"""Response models for the lessons API. The `lesson` field follows the shared Lesson contract."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.ai.lesson_generator import GenerationStatus, LessonProviderName
from app.schemas.lesson import Id, Lesson


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
    source_filename: str
    page_count: int
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
