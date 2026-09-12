import asyncio

from app.ai.lesson_generator import LessonGenerationRequest, LessonGenerator
from app.ai.mock_lesson_generator import MockLessonGenerator
from app.models.content import ExtractedDocument, ExtractedPage
from app.schemas.lesson import Lesson, Source

UPLOADED_SOURCE = Source(source_type="pdf", title="Chemistry notes", filename="chemistry.pdf")


def _request(lesson_id: str = "lesson-abc") -> LessonGenerationRequest:
    document = ExtractedDocument(
        pages=[ExtractedPage(page_number=1, text="Atoms form bonds.")], total_pages=1
    )
    return LessonGenerationRequest(
        lesson_id=lesson_id, source=UPLOADED_SOURCE, document=document, chunks=[]
    )


def test_mock_generator_returns_the_example_lesson_under_the_requested_id() -> None:
    generator: LessonGenerator = MockLessonGenerator()

    result = asyncio.run(generator.generate(_request()))

    assert result.lesson.id == "lesson-abc"
    assert result.lesson.title.startswith("Photosynthesis")
    assert (result.model, result.ai_request_count, result.warnings) == (None, 0, [])
    assert (result.provider, result.generation_status) == ("demo", "demo")
    Lesson.model_validate(result.lesson.model_dump(mode="json", exclude_none=True))


def test_mock_lesson_does_not_claim_to_come_from_the_uploaded_pdf() -> None:
    result = asyncio.run(MockLessonGenerator().generate(_request()))

    assert result.lesson.source != UPLOADED_SOURCE


def test_mock_generator_is_deterministic() -> None:
    generator = MockLessonGenerator()

    assert asyncio.run(generator.generate(_request())) == asyncio.run(
        generator.generate(_request())
    )
