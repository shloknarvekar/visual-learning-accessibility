"""Lesson generation stage interface.

A `LessonGenerator` turns segmented source content into a validated `Lesson`. The planned
implementation composes small steps that can each be tested alone, not one large prompt:

    segments -> content analysis -> visual planning -> lesson assembly -> quiz generation

AI steps call `AIProvider.generate_structured` with their own prompt (in `app/ai/prompts/`) and
their own intermediate output model. Lesson assembly (ids, provenance, schema_version) is plain
Python, and the result is always validated as `Lesson` before it leaves the pipeline.

When no AI provider is configured, `MockLessonGenerator` implements this interface instead.
"""

from typing import Protocol

from app.models.content import ContentSegment
from app.schemas.lesson import Lesson, Source


class LessonGenerator(Protocol):
    async def generate(self, source: Source, segments: list[ContentSegment]) -> Lesson: ...
