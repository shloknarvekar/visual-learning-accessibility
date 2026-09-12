"""Deciding which of a draft's citations the source can actually prove.

Everything a model writes about provenance is untrusted, but what "proving" means depends on the
input:

- A document holds its own text, so a page number can be checked, a quote can be located and moved
  to the page it really appears on, and a chart's numbers can be required to appear on the pages it
  cites.
- A video proves none of that without a transcript, which this project deliberately does not build
  (scraping one back just to imitate the document path would be a worse lie than admitting the
  limit). What a video can prove is that a timestamp is a real position in it, so that is what
  survives, and the lesson carries a warning saying its quotes were not checked word for word.

`lesson_assembly` asks a `Grounding` these questions and never learns which input produced the
draft, so there is one assembly path for every input type.
"""

import re
from typing import Protocol

from app.ai.drafts import DraftSourceReference
from app.models.content import ExtractedDocument
from app.schemas.lesson import SourceReference

MIN_EXCERPT_CHARS = 12  # shorter quotes match too many places to prove anything
MAX_EXCERPT_CHARS = 300

# A timestamp beyond this is not a position in a lecture, it is a mistake.
MAX_VIDEO_SECONDS = 24 * 60 * 60

_WHITESPACE = re.compile(r"\s+")


def normalise(text: str) -> str:
    return _WHITESPACE.sub(" ", text).strip().casefold()


def shorten(excerpt: str) -> str:
    if len(excerpt) <= MAX_EXCERPT_CHARS:
        return excerpt
    cut = excerpt.rfind(" ", 0, MAX_EXCERPT_CHARS)
    return excerpt[: cut if cut > 0 else MAX_EXCERPT_CHARS]


def _clean_excerpt(excerpt: str) -> str:
    return _WHITESPACE.sub(" ", excerpt).strip()


def number_in_text(value: float, text: str) -> bool:
    forms = {f"{value:g}", f"{value:.1f}", f"{value:.2f}"}
    if value.is_integer():
        forms |= {str(int(value)), f"{int(value):,}"}
    return any(re.search(rf"(?<![\d.]){re.escape(form)}(?!\d)", text) for form in forms)


class Grounding(Protocol):
    """What a particular source can prove about a draft's claims."""

    def reference(self, draft: DraftSourceReference) -> SourceReference | None:
        """The citation this source supports, or None when it supports none of it."""
        ...

    def chart_rejection(self, values: list[float], references: list[SourceReference]) -> str | None:
        """Why a chart's numbers cannot be trusted, in plain words, or None when they can."""
        ...

    def notes(self) -> list[str]:
        """Warnings about what was changed or dropped, for the lesson's metadata."""
        ...


class PageGrounding:
    """Citations checked against the extracted text of a paged document."""

    def __init__(self, document: ExtractedDocument) -> None:
        self._page_count = document.total_pages
        self._page_text = {page.page_number: normalise(page.text) for page in document.pages}
        self._moved_quotes = 0
        self._removed_quotes = 0
        self._removed_pages = 0

    def reference(self, draft: DraftSourceReference) -> SourceReference | None:
        excerpt = _clean_excerpt(draft.excerpt)
        if len(excerpt) >= MIN_EXCERPT_CHARS:
            page = self._page_with_quote(excerpt, preferred=draft.page_number)
            if page is not None:
                if page != draft.page_number:
                    self._moved_quotes += 1
                return SourceReference(page_number=page, excerpt=shorten(excerpt))
        if excerpt:
            self._removed_quotes += 1
        if 1 <= draft.page_number <= self._page_count:
            return SourceReference(page_number=draft.page_number)
        self._removed_pages += 1
        return None

    def chart_rejection(self, values: list[float], references: list[SourceReference]) -> str | None:
        cited = " ".join(
            self._page_text.get(reference.page_number, "")
            for reference in references
            if reference.page_number is not None
        )
        if not cited:
            return "a chart must cite the page its numbers come from"
        if not all(number_in_text(value, cited) for value in values):
            return "some of its numbers do not appear on the pages it cites"
        return None

    def notes(self) -> list[str]:
        counts = [
            (self._moved_quotes, "quote(s) cited the wrong page and were moved to the right page"),
            (self._removed_quotes, "quote(s) could not be found in the PDF and were removed"),
            (self._removed_pages, "reference(s) to pages that do not exist were removed"),
        ]
        return [f"{count} {message}." for count, message in counts if count]

    def _page_with_quote(self, excerpt: str, *, preferred: int) -> int | None:
        needle = normalise(excerpt)
        if needle in self._page_text.get(preferred, ""):
            return preferred
        return next((number for number, text in self._page_text.items() if needle in text), None)


class VideoGrounding:
    """Citations checked against a video, where a timestamp is the only provable locator.

    Page numbers in the draft are ignored outright rather than trusted: a video has no pages, so a
    page number here is the model filling in a required field, not evidence.
    """

    def __init__(self) -> None:
        self._removed_timestamps = 0
        self._kept_quotes = 0
        self._unverified_charts = 0

    def reference(self, draft: DraftSourceReference) -> SourceReference | None:
        start = draft.start_time_seconds
        if not 0 <= start <= MAX_VIDEO_SECONDS:
            self._removed_timestamps += 1
            return None
        end = draft.end_time_seconds
        # An end before the start, or past the sanity bound, is dropped rather than guessed at. The
        # start on its own is still a usable locator.
        usable_end = end if start <= end <= MAX_VIDEO_SECONDS else None

        excerpt = _clean_excerpt(draft.excerpt)
        if len(excerpt) >= MIN_EXCERPT_CHARS:
            self._kept_quotes += 1
        else:
            excerpt = ""

        return SourceReference(
            start_time_seconds=start,
            end_time_seconds=usable_end,
            excerpt=shorten(excerpt) or None,
        )

    def chart_rejection(self, values: list[float], references: list[SourceReference]) -> str | None:
        if not any(reference.start_time_seconds is not None for reference in references):
            return "a chart from a video must cite the time its numbers come from"
        self._unverified_charts += 1
        return None

    def notes(self) -> list[str]:
        notes = []
        if self._removed_timestamps:
            notes.append(
                f"{self._removed_timestamps} reference(s) had a missing or impossible timestamp "
                "and were removed."
            )
        if self._kept_quotes:
            notes.append(
                f"{self._kept_quotes} quote(s) come from what is said in the video. They are "
                "placed at the time they were heard but were not checked word for word."
            )
        if self._unverified_charts:
            notes.append(
                f"{self._unverified_charts} chart(s) use numbers read from the video. Check them "
                "against the video before relying on them."
            )
        return notes
