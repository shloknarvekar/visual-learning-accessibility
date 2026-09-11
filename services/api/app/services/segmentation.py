"""Segmentation stage interface: split an extracted document into topic-sized segments.

Segments bound how much text each AI call sees and preserve source locations for provenance.
"""

from typing import Protocol

from app.models.content import ContentSegment, ExtractedDocument


class Segmenter(Protocol):
    def segment(self, document: ExtractedDocument) -> list[ContentSegment]: ...
