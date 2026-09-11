from pathlib import Path

import pytest

from app.schemas.lesson import Lesson
from app.services.lesson_store import FileLessonStore


def test_saved_lesson_can_be_read_back(tmp_path: Path, example_lesson: Lesson) -> None:
    store = FileLessonStore(tmp_path)

    store.save(example_lesson)

    assert store.get(example_lesson.id) == example_lesson


def test_missing_lesson_returns_none(tmp_path: Path) -> None:
    assert FileLessonStore(tmp_path).get("not-saved") is None


@pytest.mark.parametrize(
    "unsafe_id", ["../escape", "a/b", "a\\b", "", "has space", "x" * 65, "ok\n"]
)
def test_unsafe_ids_are_rejected(tmp_path: Path, unsafe_id: str) -> None:
    with pytest.raises(ValueError, match="invalid id"):
        FileLessonStore(tmp_path).get(unsafe_id)
