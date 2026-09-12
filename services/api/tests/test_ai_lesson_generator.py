import asyncio

import pytest

from app.ai.ai_lesson_generator import AILessonGenerator
from app.ai.drafts import (
    ChunkNotes,
    DraftQuizQuestion,
    DraftSection,
    DraftSourceReference,
    LessonDraft,
    NoteItem,
)
from app.ai.lesson_generator import LessonGenerationRequest
from app.core.errors import AppError, ErrorCode
from app.models.content import ExtractedDocument, ExtractedPage
from app.schemas.lesson import Source
from app.services.chunking import chunk_document
from tests.fakes import FakeProvider

PAGES = [
    "Photosynthesis is the process plants use to make glucose from light, water and carbon "
    "dioxide.",
    "Chlorophyll absorbs red and blue light and reflects green light, so leaves look green.",
]
QUOTE = "plants use to make glucose"


def _request(*, chunk_max_chars: int = 10_000) -> LessonGenerationRequest:
    pages = [ExtractedPage(page_number=n, text=text) for n, text in enumerate(PAGES, start=1)]
    document = ExtractedDocument(pages=pages, total_pages=len(pages))
    return LessonGenerationRequest(
        lesson_id="lesson-1",
        source=Source(source_type="pdf", title="notes", filename="notes.pdf"),
        document=document,
        chunks=chunk_document(document, max_chars=chunk_max_chars),
    )


def _draft() -> LessonDraft:
    return LessonDraft(
        title="Photosynthesis",
        overview="How plants make glucose.",
        sections=[
            DraftSection(
                type="concept",
                title="Photosynthesis",
                term="Photosynthesis",
                definition="How plants make glucose from light.",
                source_references=[DraftSourceReference(page_number=1, excerpt=QUOTE)],
            )
        ],
        quiz=[
            DraftQuizQuestion(
                prompt=f"Question {number}?",
                options=["Glucose", "Salt", "Iron"],
                correct_option_index=0,
                explanation="Page 1 says plants make glucose.",
                section_numbers=[1],
            )
            for number in (1, 2, 3)
        ],
    )


def _notes() -> ChunkNotes:
    return ChunkNotes(
        topics=["Photosynthesis"],
        notes=[
            NoteItem(
                kind="definition",
                title="Photosynthesis",
                content="Plants make glucose from light.",
                source_references=[DraftSourceReference(page_number=1, excerpt=QUOTE)],
            )
        ],
    )


def test_short_document_uses_one_grounded_request() -> None:
    provider = FakeProvider([_draft()])
    generator = AILessonGenerator(provider, single_pass_max_chars=10_000, max_chunks=8)

    result = asyncio.run(generator.generate(_request()))

    assert len(provider.calls) == 1
    call = provider.calls[0]
    assert call["output_model"] is LessonDraft
    assert '<page number="1">' in call["input_text"]
    assert '<page number="2">' in call["input_text"]
    assert "Use only information supported by the source" in call["instructions"]
    assert result.lesson.id == "lesson-1"
    assert (result.model, result.ai_request_count) == ("fake-model", 1)


def test_long_document_takes_notes_per_chunk_then_writes_the_lesson() -> None:
    request = _request(chunk_max_chars=100)  # each page becomes its own chunk
    provider = FakeProvider([_notes(), _notes(), _draft()])
    generator = AILessonGenerator(provider, single_pass_max_chars=50, max_chunks=8)

    result = asyncio.run(generator.generate(request))

    assert len(request.chunks) == 2
    assert [call["output_model"] for call in provider.calls] == [
        ChunkNotes,
        ChunkNotes,
        LessonDraft,
    ]
    assert "part 2 of 2" in provider.calls[1]["input_text"]
    assert QUOTE in provider.calls[2]["input_text"]
    assert result.ai_request_count == 3


def test_document_with_too_many_chunks_is_rejected_before_any_request() -> None:
    provider = FakeProvider([])
    generator = AILessonGenerator(provider, single_pass_max_chars=50, max_chunks=1)

    with pytest.raises(AppError) as caught:
        asyncio.run(generator.generate(_request(chunk_max_chars=100)))

    assert caught.value.code == ErrorCode.DOCUMENT_TOO_LONG
    assert provider.calls == []
