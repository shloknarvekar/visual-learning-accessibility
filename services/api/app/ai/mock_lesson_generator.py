"""Deterministic lesson generator used when no AI provider is available.

Keeps the product usable at zero cost: development, tests, demos and running out of free-tier quota
all work without network access. It returns the hand-written example lesson from
packages/contracts, attributed to the requested source.
"""

from pathlib import Path

from app.core.config import CONTRACTS_DIR
from app.models.content import ContentSegment
from app.schemas.lesson import Lesson, Source

MOCK_LESSON_PATH = CONTRACTS_DIR / "examples" / "photosynthesis.lesson.json"


class MockLessonGenerator:
    def __init__(self, lesson_path: Path = MOCK_LESSON_PATH) -> None:
        self._lesson = Lesson.model_validate_json(lesson_path.read_text(encoding="utf-8"))

    async def generate(self, source: Source, segments: list[ContentSegment]) -> Lesson:
        """Return the same example lesson for any input, with `source` set to the given source."""
        return self._lesson.model_copy(update={"source": source}, deep=True)
