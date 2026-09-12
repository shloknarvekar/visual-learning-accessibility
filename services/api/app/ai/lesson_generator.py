"""Lesson generation stage interface.

A `LessonGenerator` turns an extracted, chunked document into a validated `Lesson`.
`AILessonGenerator` does this with an `AIProvider`; `MockLessonGenerator` returns fixed example data
when no provider is configured.
"""

from dataclasses import dataclass, field
from typing import Literal, Protocol

from app.models.content import ContentChunk, ExtractedDocument
from app.schemas.lesson import Lesson, Source

# Which service produced the lesson. "cache" is an earlier lesson for the same document and "demo"
# is fixed example data; neither is a live provider.
LessonProviderName = Literal["gemini", "openrouter", "groq", "cache", "demo"]

# How the lesson was produced, so callers never mistake a fallback for a primary result:
#   live      the primary provider answered
#   fallback  a secondary provider answered after the primary failed
#   cached    every provider failed; an earlier lesson for the same document was reused
#   demo      every provider failed; this is fixed example data about a different topic
GenerationStatus = Literal["live", "fallback", "cached", "demo"]


@dataclass(frozen=True)
class LessonGenerationRequest:
    lesson_id: str
    source: Source
    document: ExtractedDocument
    chunks: list[ContentChunk]


@dataclass(frozen=True)
class GeneratedLesson:
    lesson: Lesson
    warnings: list[str] = field(default_factory=list)
    model: str | None = None
    ai_request_count: int = 0
    provider: LessonProviderName = "demo"
    generation_status: GenerationStatus = "demo"


class LessonGenerator(Protocol):
    async def generate(self, request: LessonGenerationRequest) -> GeneratedLesson: ...
