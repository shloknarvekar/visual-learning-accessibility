"""Lesson persistence.

Callers depend on the `LessonStore` interface. `FileLessonStore` keeps each lesson as a JSON file on
local disk, which is enough until the workflow is proven; a database-backed store can replace it
without changing callers.
"""

from pathlib import Path
from typing import Protocol

from app.schemas.lesson import Lesson
from app.utils.ids import ensure_safe_id


class LessonStore(Protocol):
    def save(self, lesson: Lesson) -> None: ...

    def get(self, lesson_id: str) -> Lesson | None: ...


class FileLessonStore:
    def __init__(self, data_dir: Path) -> None:
        self._lessons_dir = data_dir / "lessons"

    def save(self, lesson: Lesson) -> None:
        self._lessons_dir.mkdir(parents=True, exist_ok=True)
        path = self._path_for(lesson.id)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(lesson.model_dump_json(exclude_none=True, indent=2), encoding="utf-8")
        temporary.replace(path)  # atomic, so readers never see a half-written file

    def get(self, lesson_id: str) -> Lesson | None:
        path = self._path_for(lesson_id)
        if not path.is_file():
            return None
        return Lesson.model_validate_json(path.read_text(encoding="utf-8"))

    def _path_for(self, lesson_id: str) -> Path:
        return self._lessons_dir / f"{ensure_safe_id(lesson_id)}.json"
