"""Ingestion stage interface.

Planned implementations live next to this file: `youtube.py` (transcript fetch or transcription) and
`pdf.py` (text extraction with an OCR fallback for scanned pages).

Rules for implementations:
- Never build shell commands from user input. Call libraries, or pass fixed argument lists.
- Uploaded filenames are display text only. Store files under server-generated names.
- Raise `app.core.errors.AppError` for problems the user can fix (bad URL, unreadable PDF).
"""

from typing import Protocol

from app.models.content import ExtractedDocument, SourceInput


class ContentExtractor(Protocol):
    async def extract(self, source: SourceInput) -> ExtractedDocument:
        """Extract text blocks, each with its page number or time range."""
        ...
