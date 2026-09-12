"""Optional checks against the real Gemini API. Excluded from normal test runs and CI.

Opt in with `pytest -m live`; skipped when GEMINI_API_KEY is not set. Uses free-tier quota: the
connectivity check makes one request and the lesson check makes one or a few.
"""

import asyncio
from pathlib import Path

import pytest
from pydantic import BaseModel

from app.ai.ai_lesson_generator import AILessonGenerator
from app.ai.gemini_provider import GeminiProvider
from app.ai.lesson_generator import LessonGenerationRequest
from app.core.config import Settings
from app.ingestion.pdf import extract_pdf
from app.schemas.lesson import Source
from app.services.chunking import chunk_document
from tests.pdf_helpers import make_pdf

pytestmark = pytest.mark.live

SAMPLE_PAGES = [
    "Photosynthesis\n\n"
    "Photosynthesis is the process plants use to make glucose from light energy, water and carbon "
    "dioxide. It happens in chloroplasts, which contain the green pigment chlorophyll. Oxygen is "
    "released as a by-product.\n\n"
    "Word equation: carbon dioxide + water -> glucose + oxygen.",
    "Two stages\n\n"
    "1. The light-dependent reactions take place in the thylakoid membranes. Light energy splits "
    "water and produces ATP and NADPH.\n"
    "2. The Calvin cycle takes place in the stroma. It uses ATP and NADPH to turn carbon dioxide "
    "into glucose.\n\n"
    "In an experiment with pondweed, 12 bubbles formed per minute with the lamp 10 cm away and 30 "
    "bubbles formed per minute with the lamp 5 cm away.",
]


class ConnectivityReply(BaseModel):
    reply: str


def _live_settings() -> Settings:
    settings = Settings()
    if settings.gemini_api_key is None:
        pytest.skip("GEMINI_API_KEY is not set")
    return settings


def test_gemini_returns_structured_output() -> None:
    provider = GeminiProvider.from_settings(_live_settings())

    result = asyncio.run(
        provider.generate_structured(
            instructions="Return a JSON object whose `reply` field is the word: ready",
            input_text="Connectivity check.",
            output_model=ConnectivityReply,
        )
    )

    assert result.reply


def test_gemini_generates_a_grounded_lesson_from_a_pdf(tmp_path: Path) -> None:
    settings = _live_settings()
    path = tmp_path / "photosynthesis.pdf"
    path.write_bytes(make_pdf(SAMPLE_PAGES))
    document = extract_pdf(path, max_pages=settings.pdf_max_pages)
    generator = AILessonGenerator(
        GeminiProvider.from_settings(settings),
        single_pass_max_chars=settings.ai_single_pass_max_chars,
        max_chunks=settings.ai_max_chunks,
    )
    request = LessonGenerationRequest(
        lesson_id="live-check",
        source=Source(source_type="pdf", title="photosynthesis", filename="photosynthesis.pdf"),
        document=document,
        chunks=chunk_document(document, max_chars=settings.chunk_max_chars),
    )

    result = asyncio.run(generator.generate(request))

    lesson = result.lesson
    assert lesson.sections
    assert 1 <= len(lesson.quiz) <= 5
    for section in lesson.sections:
        for reference in section.source_references:
            assert 1 <= (reference.page_number or 0) <= document.total_pages
