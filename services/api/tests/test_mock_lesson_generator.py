import asyncio

from app.ai.lesson_generator import LessonGenerator
from app.ai.mock_lesson_generator import MockLessonGenerator
from app.schemas.lesson import Lesson, Source

SOURCE = Source.model_validate(
    {
        "source_type": "youtube",
        "title": "Introduction to Biology",
        "url": "https://www.youtube.com/watch?v=abc123",
    }
)


def test_mock_generator_returns_a_valid_lesson_for_the_given_source() -> None:
    generator: LessonGenerator = MockLessonGenerator()

    lesson = asyncio.run(generator.generate(SOURCE, segments=[]))

    assert lesson.source == SOURCE
    Lesson.model_validate(lesson.model_dump(mode="json", exclude_none=True))


def test_mock_generator_is_deterministic() -> None:
    generator = MockLessonGenerator()

    first = asyncio.run(generator.generate(SOURCE, segments=[]))
    second = asyncio.run(generator.generate(SOURCE, segments=[]))

    assert first == second
