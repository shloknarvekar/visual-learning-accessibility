"""Conservative clean-up of text extracted from PDFs.

Removes layout artefacts only. Wording is never changed, so every sentence stays traceable to its
page:
- normalises spaces, invisible characters and line endings
- joins lines that the PDF layout wrapped mid-sentence
- collapses runs of blank lines
- removes headers, footers and page numbers at the top or bottom of pages
"""

import math
import re
from collections import defaultdict

_EDGE_LINE_COUNT = 2  # lines at the top and at the bottom of a page that may be headers/footers
_MIN_PAGES_FOR_REPEAT_DETECTION = 3
_REPEAT_RATIO = 0.6
_MAX_EDGE_LINE_LENGTH = 100

_HORIZONTAL_SPACE = re.compile(r"[^\S\n]+")
_INVISIBLE = re.compile(
    r"[\N{SOFT HYPHEN}\N{ZERO WIDTH SPACE}\N{ZERO WIDTH NON-JOINER}"
    r"\N{ZERO WIDTH JOINER}\N{WORD JOINER}\N{ZERO WIDTH NO-BREAK SPACE}]"
)
_DIGITS = re.compile(r"\d+")
_DASH = r"[-\N{EN DASH}\N{EM DASH}]"
_PAGE_NUMBER = re.compile(
    rf"^(?:page\s*)?{_DASH}?\s*(\d{{1,4}})\s*{_DASH}?(?:\s*(?:of|/)\s*\d{{1,4}})?$",
    re.IGNORECASE,
)
_SENTENCE_END = (".", "!", "?", ":", ";")


def clean_pages(page_texts: list[str]) -> list[str]:
    """Return the cleaned text of each page, in order.

    Header and footer detection compares pages with each other, so pass the whole document.
    """
    pages = [_split_lines(text) for text in page_texts]
    furniture = _repeated_edge_keys(pages)
    return [
        _join_lines(_strip_page_furniture(lines, page_number, furniture))
        for page_number, lines in enumerate(pages, start=1)
    ]


def _split_lines(text: str) -> list[str]:
    text = _INVISIBLE.sub("", text.replace("\r\n", "\n").replace("\r", "\n"))
    return [_HORIZONTAL_SPACE.sub(" ", line).strip() for line in text.split("\n")]


def _edge_key(line: str) -> str:
    return _DIGITS.sub("#", line.casefold())


def _edge_lines(lines: list[str]) -> set[str]:
    content = [line for line in lines if line and len(line) <= _MAX_EDGE_LINE_LENGTH]
    return set(content[:_EDGE_LINE_COUNT] + content[-_EDGE_LINE_COUNT:])


def _repeated_edge_keys(pages: list[list[str]]) -> set[str]:
    if len(pages) < _MIN_PAGES_FOR_REPEAT_DETECTION:
        return set()
    appearances: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for page_number, lines in enumerate(pages, start=1):
        for line in _edge_lines(lines):
            appearances[_edge_key(line)].append((page_number, line))
    threshold = max(_MIN_PAGES_FOR_REPEAT_DETECTION, math.ceil(len(pages) * _REPEAT_RATIO))
    return {
        key
        for key, seen in appearances.items()
        if len(seen) >= threshold and _looks_like_page_furniture(seen)
    }


def _looks_like_page_furniture(seen: list[tuple[int, str]]) -> bool:
    """True for identical running text, or for numbers that move with the page ("Page 3 of 9").

    Lines such as "Section 2" that only share a shape but whose numbers do not follow the page
    numbers are content and are kept.
    """
    if len({line.casefold() for _, line in seen}) == 1:
        return True
    shared_offsets: set[int] | None = None
    for page_number, line in seen:
        offsets = {int(number) - page_number for number in _DIGITS.findall(line)}
        shared_offsets = offsets if shared_offsets is None else shared_offsets & offsets
    return bool(shared_offsets)


def _is_page_furniture(line: str, page_number: int, furniture: set[str]) -> bool:
    if _edge_key(line) in furniture:
        return True
    match = _PAGE_NUMBER.match(line)
    return match is not None and int(match.group(1)) == page_number


def _content_index(lines: list[str], *, from_top: bool) -> int | None:
    indices = range(len(lines)) if from_top else range(len(lines) - 1, -1, -1)
    return next((index for index in indices if lines[index]), None)


def _strip_page_furniture(lines: list[str], page_number: int, furniture: set[str]) -> list[str]:
    content = list(lines)
    for from_top in (True, False):
        for _ in range(_EDGE_LINE_COUNT):
            index = _content_index(content, from_top=from_top)
            if index is None or not _is_page_furniture(content[index], page_number, furniture):
                break
            del content[index]
    return content


def _join_lines(lines: list[str]) -> str:
    paragraphs: list[str] = []
    current = ""
    for line in lines:
        if not line:
            if current:
                paragraphs.append(current)
                current = ""
        elif not current:
            current = line
        elif current.endswith("-") and line[0].islower():
            current += line  # "light-" + "dependent" -> "light-dependent"; the hyphen is kept
        elif line[0].islower() and not current.endswith(_SENTENCE_END):
            current += " " + line  # the layout wrapped this sentence onto a new line
        else:
            current += "\n" + line
    if current:
        paragraphs.append(current)
    return "\n\n".join(paragraphs)
