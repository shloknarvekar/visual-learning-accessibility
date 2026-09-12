"""What a video can and cannot prove about a draft's citations."""

import pytest

from app.ai.drafts import NO_TIMESTAMP, DraftSourceReference
from app.ai.grounding import MAX_VIDEO_SECONDS, PageGrounding, VideoGrounding
from app.models.content import ExtractedDocument, ExtractedPage
from app.schemas.lesson import SourceReference

QUOTE = "chlorophyll absorbs red and blue light"

DOCUMENT = ExtractedDocument(
    pages=[ExtractedPage(page_number=1, text=f"Leaves are green because {QUOTE}.")],
    total_pages=1,
)


def ref(
    *,
    page: int = 0,
    start: float = NO_TIMESTAMP,
    end: float = NO_TIMESTAMP,
    excerpt: str = "",
) -> DraftSourceReference:
    return DraftSourceReference(
        page_number=page, start_time_seconds=start, end_time_seconds=end, excerpt=excerpt
    )


# ---- Timestamps --------------------------------------------------------------------------------


def test_a_time_range_survives_as_a_time_range() -> None:
    grounding = VideoGrounding()

    assert grounding.reference(ref(start=12.5, end=30.0, excerpt=QUOTE)) == SourceReference(
        start_time_seconds=12.5, end_time_seconds=30.0, excerpt=QUOTE
    )


def test_a_moment_without_an_end_is_kept() -> None:
    assert VideoGrounding().reference(ref(start=12.5)) == SourceReference(start_time_seconds=12.5)


def test_the_very_start_of_a_video_is_a_valid_locator() -> None:
    """Zero is a real timestamp, and must not be mistaken for "no timestamp"."""
    assert VideoGrounding().reference(ref(start=0.0)) == SourceReference(start_time_seconds=0.0)


@pytest.mark.parametrize(
    "end",
    [5.0, NO_TIMESTAMP, MAX_VIDEO_SECONDS + 1],
    ids=["end-before-start", "no-end-given", "end-past-any-real-video"],
)
def test_an_unusable_end_is_dropped_but_the_start_is_kept(end: float) -> None:
    """Half a usable citation beats none, and beats a guess at the other half."""
    reference = VideoGrounding().reference(ref(start=10.0, end=end))

    assert reference == SourceReference(start_time_seconds=10.0)


@pytest.mark.parametrize(
    "start",
    [NO_TIMESTAMP, -0.5, MAX_VIDEO_SECONDS + 1, 1e12],
    ids=["not-given", "negative", "just-past-the-bound", "absurd"],
)
def test_a_reference_with_no_usable_start_is_removed_entirely(start: float) -> None:
    grounding = VideoGrounding()

    assert grounding.reference(ref(start=start, excerpt=QUOTE)) is None
    assert any("impossible timestamp" in note for note in grounding.notes())


def test_page_numbers_from_a_video_draft_are_ignored_not_trusted() -> None:
    """A video has no pages, so a page number here is the model filling a field, not evidence."""
    reference = VideoGrounding().reference(ref(page=7, start=10.0))

    assert reference is not None
    assert reference.page_number is None


# ---- Quotes ------------------------------------------------------------------------------------


def test_a_quote_is_kept_but_the_lesson_says_it_was_not_verified() -> None:
    grounding = VideoGrounding()

    reference = grounding.reference(ref(start=10.0, excerpt=QUOTE))

    assert reference is not None
    assert reference.excerpt == QUOTE
    assert any("not checked word for word" in note for note in grounding.notes())


def test_a_quote_too_short_to_mean_anything_is_dropped() -> None:
    reference = VideoGrounding().reference(ref(start=10.0, excerpt="yes"))

    assert reference is not None
    assert reference.excerpt is None


def test_a_very_long_quote_is_shortened() -> None:
    reference = VideoGrounding().reference(ref(start=10.0, excerpt="word " * 200))

    assert reference is not None
    assert reference.excerpt is not None
    assert len(reference.excerpt) <= 300


def test_nothing_is_reported_when_nothing_needed_changing() -> None:
    grounding = VideoGrounding()

    grounding.reference(ref(start=1.0))

    assert grounding.notes() == []


# ---- Charts ------------------------------------------------------------------------------------


def test_a_chart_must_say_when_in_the_video_its_numbers_appear() -> None:
    rejection = VideoGrounding().chart_rejection([12.0, 30.0], [])

    assert rejection is not None
    assert "cite the time" in rejection


def test_a_chart_that_cites_a_time_is_kept_with_a_warning_that_it_was_not_checked() -> None:
    """Without a transcript the numbers cannot be verified, so the lesson says so rather than

    dropping a chart the video may well support, or pretending it was checked.
    """
    grounding = VideoGrounding()
    cited = [SourceReference(start_time_seconds=42.0)]

    assert grounding.chart_rejection([12.0, 30.0], cited) is None
    assert any("read from the video" in note for note in grounding.notes())


# ---- Documents are unaffected ------------------------------------------------------------------


def test_page_grounding_still_moves_a_quote_to_the_page_it_is_really_on() -> None:
    grounding = PageGrounding(DOCUMENT)

    reference = grounding.reference(DraftSourceReference(page_number=9, excerpt=QUOTE))

    assert reference == SourceReference(page_number=1, excerpt=QUOTE)
    assert any("moved to the right page" in note for note in grounding.notes())


def test_page_grounding_ignores_timestamps_a_document_cannot_have() -> None:
    reference = PageGrounding(DOCUMENT).reference(ref(page=1, start=10.0, end=20.0))

    assert reference == SourceReference(page_number=1)


def test_page_grounding_still_requires_chart_numbers_to_appear_on_the_cited_page() -> None:
    grounding = PageGrounding(DOCUMENT)

    rejection = grounding.chart_rejection([999.0], [SourceReference(page_number=1)])

    assert rejection is not None
    assert "do not appear" in rejection
