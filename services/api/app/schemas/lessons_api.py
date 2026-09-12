"""Request and response models for the lessons API.

The `lesson` field follows the shared Lesson contract; everything around it describes how that
lesson was produced and is specific to this API.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.ai.lesson_generator import GenerationStatus, LessonProviderName
from app.schemas.lesson import Id, Lesson


class YouTubeLessonRequest(BaseModel):
    """The body of `POST /lessons/youtube`.

    Typed as a plain string rather than a URL so that a link which is well-formed but not a
    YouTube video fails as `INVALID_VIDEO_URL`, with an explanation, instead of as a generic
    request-validation error. The real checking happens in `app.ingestion.video`.
    """

    url: str = Field(
        min_length=1,
        max_length=2048,
        description="A link to a single public YouTube video.",
        examples=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
    )


class ProcessingTimings(BaseModel):
    """How long each step took, in milliseconds, when the lesson was created."""

    extraction_ms: int
    chunking_ms: int
    generation_ms: int
    validation_ms: int
    total_ms: int


class LessonMetadata(BaseModel):
    provider: LessonProviderName = Field(
        description="Who produced this lesson: an AI provider, the cache, or fixed demo content."
    )
    generation_status: GenerationStatus = Field(
        description="`live` from the primary provider, `fallback` from a backup provider, "
        "`cached` from an earlier generation of the same document, `demo` for example content."
    )
    is_mock: bool = Field(
        description="True when the lesson is example data that does not describe the uploaded file."
    )
    notice: str | None = Field(
        default=None, description="A note to show the user, for example that this is demo data."
    )
    model: str | None = Field(default=None, description="The AI model that generated the lesson.")
    # Both are omitted rather than faked when they do not apply: a YouTube lesson has no uploaded
    # file, and no video has pages. What the lesson was made from is always in `lesson.source`
    # (`source_type`, plus `url` or `filename`), which is the field to branch on - not these.
    source_filename: str | None = Field(
        default=None, description="Name of the uploaded file. Absent for a YouTube lesson."
    )
    page_count: int | None = Field(
        default=None, description="Pages in the source document. Absent for video lessons."
    )
    chunk_count: int
    character_count: int
    ai_request_count: int
    warnings: list[str] = Field(
        default_factory=list,
        description="Content that was left out or corrected when the lesson was checked.",
    )
    timings: ProcessingTimings
    created_at: datetime


class LessonRecord(BaseModel):
    """A stored lesson and how it was made. Returned by both lessons endpoints."""

    lesson_id: Id
    metadata: LessonMetadata
    lesson: Lesson
