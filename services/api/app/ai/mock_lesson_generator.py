"""Deterministic lesson generator used when no AI provider is available.

Keeps the product usable at zero cost: development, tests, demos and running out of free-tier quota
all work without network access. It returns the hand-written example lesson from
packages/contracts under the requested id. The lesson keeps the example's own source, because its
content does not describe the uploaded document.
"""

from pathlib import Path

from app.ai.lesson_generator import GeneratedLesson, LessonGenerationRequest
from app.core.config import CONTRACTS_DIR
from app.schemas.lesson import Lesson

MOCK_LESSON_PATH = CONTRACTS_DIR / "examples" / "photosynthesis.lesson.json"


class MockLessonGenerator:
    def __init__(self, lesson_path: Path = MOCK_LESSON_PATH) -> None:
        self._lesson = Lesson.model_validate_json(lesson_path.read_text(encoding="utf-8"))

    async def generate(self, request: LessonGenerationRequest) -> GeneratedLesson:
        lesson = self._lesson.model_copy(update={"id": request.lesson_id}, deep=True)
        return GeneratedLesson(lesson=lesson, provider="demo", generation_status="demo")
