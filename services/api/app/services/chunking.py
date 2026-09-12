"""Deterministic chunking: splits a document into pieces small enough for one model request.

Chunks follow document order and prefer natural boundaries: whole paragraphs, then whole sentences,
and only as a last resort a break between words. Pieces are slices of the extracted text, so wording
and spacing are unchanged. The same document and limit always produce the same chunks and ids.
"""

import re

from app.models.content import ContentChunk, ExtractedDocument, PagePassage

PARAGRAPH_SEPARATOR = "\n\n"

_PARAGRAPH_BREAK = re.compile(r"\n\s*\n")
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+")
_WORD_BREAK = re.compile(r"\s+")


def chunk_document(document: ExtractedDocument, *, max_chars: int) -> list[ContentChunk]:
    """Split `document` into chunks whose `text` is at most `max_chars` characters long."""
    pieces = [
        (page.page_number, piece)
        for page in document.pages
        for piece in _split_page(page.text, max_chars)
    ]

    groups: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    size = 0
    for page_number, piece in pieces:
        added = len(piece) + (len(PARAGRAPH_SEPARATOR) if current else 0)
        if current and size + added > max_chars:
            groups.append(current)
            current, size, added = [], 0, len(piece)
        current.append((page_number, piece))
        size += added
    if current:
        groups.append(current)

    return [
        ContentChunk(chunk_id=f"chunk-{index:03d}", passages=_passages(group))
        for index, group in enumerate(groups, start=1)
    ]


def _split_page(text: str, max_chars: int) -> list[str]:
    pieces: list[str] = []
    for paragraph in _PARAGRAPH_BREAK.split(text):
        paragraph = paragraph.strip()
        if len(paragraph) <= max_chars:
            pieces.extend([paragraph] if paragraph else [])
        else:
            pieces.extend(_pack(paragraph, _fitting_spans(paragraph, max_chars), max_chars))
    return pieces


def _spans(text: str, separator: re.Pattern[str], start: int, end: int) -> list[tuple[int, int]]:
    """Character ranges of the non-separator parts of text[start:end]."""
    spans: list[tuple[int, int]] = []
    for match in separator.finditer(text, start, end):
        spans.append((start, match.start()))
        start = match.end()
    spans.append((start, end))
    return [(span_start, span_end) for span_start, span_end in spans if span_end > span_start]


def _fitting_spans(text: str, max_chars: int) -> list[tuple[int, int]]:
    """Sentence ranges; sentences longer than the limit become word ranges (or fixed slices)."""
    spans: list[tuple[int, int]] = []
    for start, end in _spans(text, _SENTENCE_BREAK, 0, len(text)):
        if end - start <= max_chars:
            spans.append((start, end))
            continue
        for word_start, word_end in _spans(text, _WORD_BREAK, start, end):
            spans.extend(
                (slice_start, min(slice_start + max_chars, word_end))
                for slice_start in range(word_start, word_end, max_chars)
            )
    return spans


def _pack(text: str, spans: list[tuple[int, int]], max_chars: int) -> list[str]:
    """Greedily join neighbouring ranges while the combined slice stays within the limit."""
    parts: list[str] = []
    part_start: int | None = None
    part_end = 0
    for start, end in spans:
        if part_start is not None and end - part_start > max_chars:
            parts.append(text[part_start:part_end])
            part_start = None
        if part_start is None:
            part_start = start
        part_end = end
    if part_start is not None:
        parts.append(text[part_start:part_end])
    return parts


def _passages(group: list[tuple[int, str]]) -> list[PagePassage]:
    passages: list[PagePassage] = []
    for page_number, piece in group:
        if passages and passages[-1].page_number == page_number:
            passages[-1].text += PARAGRAPH_SEPARATOR + piece
        else:
            passages.append(PagePassage(page_number=page_number, text=piece))
    return passages
