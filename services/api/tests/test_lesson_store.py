from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.schemas.lesson import Lesson
from app.schemas.lessons_api import LessonMetadata, LessonRecord, ProcessingTimings
from app.services.lesson_store import FileLessonStore


def _record(lesson: Lesson) -> LessonRecord:
    metadata = LessonMetadata(
        provider="demo",
        generation_status="demo",
        is_mock=True,
        notice="Demo data.",
        source_filename="notes.pdf",
        page_count=2,
        chunk_count=1,
        character_count=120,
        ai_request_count=0,
        timings=ProcessingTimings(
            extraction_ms=12, chunking_ms=1, generation_ms=2, validation_ms=1, total_ms=20
        ),
        created_at=datetime(2026, 9, 12, 10, 0, tzinfo=UTC),
    )
    return LessonRecord(lesson_id=lesson.id, metadata=metadata, lesson=lesson)


def test_saved_record_can_be_read_back(tmp_path: Path, example_lesson: Lesson) -> None:
    store = FileLessonStore(tmp_path)
    record = _record(example_lesson)

    store.save(record)

    assert store.get(record.lesson_id) == record


def test_missing_lesson_returns_none(tmp_path: Path) -> None:
    assert FileLessonStore(tmp_path).get("not-saved") is None


@pytest.mark.parametrize(
    "unsafe_id", ["../escape", "a/b", "a\\b", "", "has space", "x" * 65, "ok\n"]
)
def test_unsafe_ids_are_rejected(tmp_path: Path, unsafe_id: str) -> None:
    with pytest.raises(ValueError, match="invalid id"):
        FileLessonStore(tmp_path).get(unsafe_id)
