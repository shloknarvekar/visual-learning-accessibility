"""Generates a lesson from extracted document text with any `AIProvider`.

- Short documents take one request: source text -> lesson draft.
- Longer documents take one request per chunk (stage A: study notes) and one synthesis request
  (stage B: notes -> lesson draft). Requests run one after another to stay within free-tier limits.

The draft is then checked and assembled into a strict `Lesson` by `lesson_assembly`.
"""

import logging
import time

from app.ai.drafts import ChunkNotes, LessonDraft
from app.ai.lesson_assembly import assemble_lesson
from app.ai.lesson_generator import GeneratedLesson, LessonGenerationRequest
from app.ai.prompts.lesson_generation import (
    CHUNK_NOTES_INSTRUCTIONS,
    LESSON_FROM_NOTES_INSTRUCTIONS,
    LESSON_FROM_SOURCE_INSTRUCTIONS,
    render_chunk,
    render_notes,
    render_source,
)
from app.ai.provider import AIProvider
from app.core.errors import AppError, ErrorCode
from app.models.content import ContentChunk

logger = logging.getLogger(__name__)


class AILessonGenerator:
    def __init__(
        self, provider: AIProvider, *, single_pass_max_chars: int, max_chunks: int
    ) -> None:
        self._provider = provider
        self._single_pass_max_chars = single_pass_max_chars
        self._max_chunks = max_chunks

    async def generate(self, request: LessonGenerationRequest) -> GeneratedLesson:
        started = time.perf_counter()
        if request.document.character_count <= self._single_pass_max_chars:
            strategy = "single_pass"
            draft = await self._draft_from_source(request.chunks)
            request_count = 1
        else:
            strategy = "chunk_notes_then_synthesis"
            draft = await self._draft_from_notes(request.chunks)
            request_count = len(request.chunks) + 1
        logger.info(
            "lesson draft generated",
            extra={
                "document_id": request.lesson_id,
                "strategy": strategy,
                "ai_requests": request_count,
                "duration_ms": round((time.perf_counter() - started) * 1000),
            },
        )

        assembled = assemble_lesson(
            draft, lesson_id=request.lesson_id, source=request.source, document=request.document
        )
        return GeneratedLesson(
            lesson=assembled.lesson,
            warnings=assembled.warnings,
            model=self._provider.model_name,
            ai_request_count=request_count,
            provider=self._provider.name,  # type: ignore[arg-type]
            generation_status="live",
        )

    async def _draft_from_source(self, chunks: list[ContentChunk]) -> LessonDraft:
        return await self._provider.generate_structured(
            instructions=LESSON_FROM_SOURCE_INSTRUCTIONS,
            input_text=render_source(passage for chunk in chunks for passage in chunk.passages),
            output_model=LessonDraft,
        )

    async def _draft_from_notes(self, chunks: list[ContentChunk]) -> LessonDraft:
        if len(chunks) > self._max_chunks:
            raise AppError(
                ErrorCode.DOCUMENT_TOO_LONG,
                f"This PDF is too long to turn into one lesson ({len(chunks)} parts; the limit is "
                f"{self._max_chunks}). Try a shorter PDF, such as a single chapter.",
            )
        notes: list[tuple[ContentChunk, ChunkNotes]] = []
        for position, chunk in enumerate(chunks, start=1):
            chunk_notes = await self._provider.generate_structured(
                instructions=CHUNK_NOTES_INSTRUCTIONS,
                input_text=render_chunk(chunk, position, len(chunks)),
                output_model=ChunkNotes,
            )
            notes.append((chunk, chunk_notes))
        return await self._provider.generate_structured(
            instructions=LESSON_FROM_NOTES_INSTRUCTIONS,
            input_text=render_notes(notes),
            output_model=LessonDraft,
        )
