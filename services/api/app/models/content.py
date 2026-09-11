"""Data flowing through the early pipeline stages: raw inputs, extracted text, and segments.

Every piece of text keeps a `SourceReference` so generated lesson sections can cite where they came
from (page number for PDFs, time range for videos).
"""

from pathlib import Path

from pydantic import BaseModel, Field, HttpUrl

from app.schemas.lesson import Id, Source, SourceReference


class YouTubeInput(BaseModel):
    url: HttpUrl


class PdfInput(BaseModel):
    file_path: Path = Field(
        description="Server-side path of a stored upload; never client-supplied."
    )
    display_name: str = Field(description="Sanitised original filename, for display only.")


SourceInput = YouTubeInput | PdfInput


class ContentBlock(BaseModel):
    """A run of extracted text and where it sits in the source."""

    text: str
    location: SourceReference


class ExtractedDocument(BaseModel):
    source: Source
    blocks: list[ContentBlock]


class ContentSegment(BaseModel):
    """A topically coherent group of blocks: the unit the AI analysis stage reads."""

    id: Id
    blocks: list[ContentBlock] = Field(min_length=1)
