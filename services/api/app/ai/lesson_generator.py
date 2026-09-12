"""Lesson generation stage interface.

A `LessonGenerator` turns one request into a validated `Lesson`. What the request carries depends on
how the material reaches us - extracted pages for a document, a watchable URI for a video - but
everything downstream of generation is identical, so both requests answer the same two questions the
shared machinery asks: which lesson id is this, and what identifies the material for caching.

`AILessonGenerator` handles documents with any `AIProvider`, `VideoLessonGenerator` handles video
with a video-capable one, and `MockLessonGenerator` returns fixed example data when no provider is
configured at all.
"""

from dataclasses import dataclass, field
from typing import Literal, Protocol

from app.ai.lesson_cache import content_cache_key, document_cache_key
from app.models.content import ContentChunk, ExtractedDocument
from app.models.media import VideoSource
from app.schemas.lesson import Lesson, Source

# Which service produced the lesson. "cache" is an earlier lesson for the same material and "demo"
# is fixed example data; neither is a live provider.
LessonProviderName = Literal["gemini", "openrouter", "groq", "cache", "demo"]

# How the lesson was produced, so callers never mistake a fallback for a primary result:
#   live      the primary provider answered
#   fallback  a secondary provider answered after the primary failed
#   cached    every provider failed; an earlier lesson for the same material was reused
#   demo      every provider failed; this is fixed example data about a different topic
GenerationStatus = Literal["live", "fallback", "cached", "demo"]


@dataclass(frozen=True)
class LessonGenerationRequest:
    """Material that was read as text: a document, already extracted and chunked."""

    lesson_id: str
    source: Source
    document: ExtractedDocument
    chunks: list[ContentChunk]

    @property
    def cache_key(self) -> str:
        return document_cache_key(self.document)


@dataclass(frozen=True)
class VideoLessonGenerationRequest:
    """Material that is watched rather than read.

    `identity` is what makes this the same video next time: the canonical watch URL for YouTube, or
    the content hash of an upload - never the Files API URI, which is new on every upload and would
    make the cache useless for the same file sent twice.
    """

    lesson_id: str
    source: Source
    video: VideoSource
    identity: str

    @property
    def cache_key(self) -> str:
        # Namespaced so a video can never collide with a document that happens to hash the same.
        return content_cache_key(f"video:{self.identity}")


AnyLessonRequest = LessonGenerationRequest | VideoLessonGenerationRequest


@dataclass(frozen=True)
class GeneratedLesson:
    lesson: Lesson
    warnings: list[str] = field(default_factory=list)
    model: str | None = None
    ai_request_count: int = 0
    provider: LessonProviderName = "demo"
    generation_status: GenerationStatus = "demo"


class LessonGenerator(Protocol):
    """Produces a lesson from a request.

    A concrete generator accepts the one request type it knows how to read; the factory is what
    guarantees each generator only ever receives that type. The shared parts - routing, caching and
    demo content - touch only `lesson_id` and `cache_key`, which both request types provide.
    """

    async def generate(self, request: AnyLessonRequest) -> GeneratedLesson: ...
