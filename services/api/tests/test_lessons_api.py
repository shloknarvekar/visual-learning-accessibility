"""End-to-end lessons API tests: upload, extract, chunk, generate, validate and store."""

from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker

from app.ai.ai_lesson_generator import AILessonGenerator
from app.ai.drafts import DraftQuizQuestion, DraftSection, DraftSourceReference, LessonDraft
from app.ai.provider import AIInvalidResponseError, AIProviderError, AIRateLimitError
from app.api.routes.lessons import get_pdf_lesson_service
from app.core.config import Settings
from app.main import create_app
from app.schemas.lesson import Lesson
from app.services.pdf_lessons import PdfLessonService
from tests.fakes import FakeProvider
from tests.pdf_helpers import make_image_only_pdf, make_pdf

PAGES = [
    "Photosynthesis is the process plants use to make glucose from light, water and carbon "
    "dioxide.",
    "Chlorophyll absorbs red and blue light and reflects green light, so leaves look green.",
]
DAMAGED_PDF = b"%PDF-1.7\nthis is not a real pdf"


def _upload(
    client: TestClient,
    data: bytes,
    *,
    filename: str = "notes.pdf",
    content_type: str = "application/pdf",
) -> httpx.Response:
    return client.post("/api/v1/lessons/pdf", files={"file": (filename, data, content_type)})


def _error_code(response: httpx.Response) -> str:
    code: str = response.json()["error"]["code"]
    return code


def _draft() -> LessonDraft:
    return LessonDraft(
        title="Photosynthesis",
        overview="How plants make glucose, and why leaves look green.",
        sections=[
            DraftSection(
                type="concept",
                title="Photosynthesis",
                term="Photosynthesis",
                definition="How plants make glucose from light, water and carbon dioxide.",
                source_references=[
                    DraftSourceReference(page_number=1, excerpt="plants use to make glucose")
                ],
            ),
            DraftSection(
                type="explanation",
                title="Why leaves look green",
                body="Chlorophyll reflects green light.",
                source_references=[  # cites the wrong page on purpose
                    DraftSourceReference(
                        page_number=1, excerpt="reflects green light, so leaves look green"
                    )
                ],
            ),
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


def _ai_client(settings: Settings, provider: FakeProvider) -> TestClient:
    """An app wired to a fake AI provider, as if GEMINI_API_KEY were configured."""
    app = create_app(settings)
    generator = AILessonGenerator(
        provider,
        single_pass_max_chars=settings.ai_single_pass_max_chars,
        max_chunks=settings.ai_max_chunks,
    )
    provider.name = "gemini"
    service = PdfLessonService.from_settings(
        settings, generator=generator, store=app.state.lesson_store
    )
    app.dependency_overrides[get_pdf_lesson_service] = lambda: service
    return TestClient(app, raise_server_exceptions=False)


# ---- Mock mode (no API key) --------------------------------------------------------------------


def test_mock_mode_returns_a_clearly_labelled_demo_lesson(client: TestClient) -> None:
    response = _upload(client, make_pdf(PAGES))

    assert response.status_code == 201
    body = response.json()
    metadata = body["metadata"]
    assert (metadata["provider"], metadata["generation_status"], metadata["is_mock"]) == (
        "demo",
        "demo",
        True,
    )
    assert "does not describe the uploaded PDF" in metadata["notice"]
    assert (metadata["page_count"], metadata["chunk_count"], metadata["ai_request_count"]) == (
        2,
        1,
        0,
    )
    assert metadata["source_filename"] == "notes.pdf"
    assert body["lesson"]["id"] == body["lesson_id"]
    Lesson.model_validate(body["lesson"])


def test_created_lesson_can_be_fetched_by_id(client: TestClient) -> None:
    created = _upload(client, make_pdf(PAGES)).json()

    response = client.get(f"/api/v1/lessons/{created['lesson_id']}")

    assert response.status_code == 200
    assert response.json() == created


@pytest.mark.parametrize("mode", ["mock", "gemini"])
def test_lesson_record_shape_is_stable_and_lesson_matches_the_shared_schema(
    settings: Settings, lesson_schema: dict[str, Any], mode: str
) -> None:
    if mode == "mock":
        client = TestClient(create_app(settings), raise_server_exceptions=False)
    else:
        client = _ai_client(settings, FakeProvider([_draft()]))

    with client:
        created = _upload(client, make_pdf(PAGES)).json()
        record = client.get(f"/api/v1/lessons/{created['lesson_id']}").json()

    assert record == created
    assert set(record) == {"lesson_id", "metadata", "lesson"}
    mode_specific_field = {"notice"} if mode == "mock" else {"model"}
    assert (
        set(record["metadata"])
        == {
            "provider",
            "generation_status",
            "is_mock",
            "source_filename",
            "page_count",
            "chunk_count",
            "character_count",
            "ai_request_count",
            "warnings",
            "timings",
            "created_at",
        }
        | mode_specific_field
    )
    assert set(record["metadata"]["timings"]) == {
        "extraction_ms",
        "chunking_ms",
        "generation_ms",
        "validation_ms",
        "total_ms",
    }
    validator = Draft202012Validator(lesson_schema, format_checker=FormatChecker())
    assert [error.message for error in validator.iter_errors(record["lesson"])] == []


@pytest.mark.parametrize("lesson_id", ["does-not-exist", "not a valid id"])
def test_unknown_lesson_is_not_found(client: TestClient, lesson_id: str) -> None:
    response = client.get(f"/api/v1/lessons/{lesson_id}")

    assert response.status_code == 404
    assert _error_code(response) == "LESSON_NOT_FOUND"


# ---- Upload and PDF validation -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("data", "content_type"),
    [(b"plain text notes", "text/plain"), (b"plain text notes", "application/pdf")],
    ids=["declared-as-text", "disguised-as-pdf"],
)
def test_non_pdf_upload_is_rejected(client: TestClient, data: bytes, content_type: str) -> None:
    response = _upload(client, data, content_type=content_type)

    assert response.status_code == 415
    assert _error_code(response) == "INVALID_FILE_TYPE"


@pytest.mark.parametrize(
    "extra_bytes", [1024, 3 * 1024 * 1024], ids=["just-over-limit", "far-over-limit"]
)
def test_oversized_upload_is_rejected(settings: Settings, extra_bytes: int) -> None:
    app = create_app(settings.model_copy(update={"max_upload_mb": 1}))
    data = make_pdf(PAGES) + b"%" * (1024 * 1024 + extra_bytes)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = _upload(client, data)

    assert response.status_code == 413
    assert _error_code(response) == "FILE_TOO_LARGE"


def test_missing_file_is_a_validation_error(client: TestClient) -> None:
    response = client.post("/api/v1/lessons/pdf", data={"something": "else"})

    assert response.status_code == 422
    assert _error_code(response) == "VALIDATION_ERROR"


def test_pdf_without_text_is_rejected_with_ocr_message(client: TestClient) -> None:
    response = _upload(client, make_image_only_pdf())

    assert response.status_code == 422
    assert response.json()["error"] == {
        "code": "PDF_HAS_NO_EXTRACTABLE_TEXT",
        "message": "This PDF does not contain extractable text. OCR support is planned.",
    }


def test_damaged_pdf_is_rejected(client: TestClient) -> None:
    response = _upload(client, DAMAGED_PDF)

    assert response.status_code == 422
    assert _error_code(response) == "PDF_EXTRACTION_FAILED"


def test_uploaded_files_are_deleted_after_processing(
    client: TestClient, settings: Settings
) -> None:
    _upload(client, make_pdf(PAGES))
    _upload(client, DAMAGED_PDF)

    uploads = settings.data_dir / "uploads"
    assert not uploads.exists() or not any(uploads.iterdir())


def test_cleanup_failure_does_not_hide_the_real_error(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse_to_delete(*_args: object, **_kwargs: object) -> None:
        raise PermissionError("the file is in use")

    monkeypatch.setattr("pathlib.Path.unlink", refuse_to_delete)

    response = _upload(client, DAMAGED_PDF)

    assert response.status_code == 422
    assert _error_code(response) == "PDF_EXTRACTION_FAILED"


def test_client_filename_is_only_used_as_display_text(client: TestClient) -> None:
    response = _upload(client, make_pdf(PAGES), filename="../../private\\notes.pdf")

    assert response.status_code == 201
    assert response.json()["metadata"]["source_filename"] == "notes.pdf"


# ---- AI mode (fake provider, no network) -------------------------------------------------------


def test_ai_mode_generates_validates_stores_and_serves_a_grounded_lesson(
    settings: Settings,
) -> None:
    provider = FakeProvider([_draft()])

    with _ai_client(settings, provider) as client:
        created = _upload(client, make_pdf(PAGES))
        fetched = client.get(f"/api/v1/lessons/{created.json()['lesson_id']}")

    assert created.status_code == 201
    body = created.json()
    metadata = body["metadata"]
    assert (
        metadata["provider"],
        metadata["generation_status"],
        metadata["is_mock"],
        metadata["model"],
    ) == ("gemini", "live", False, "fake-model")
    assert "notice" not in metadata
    assert metadata["ai_request_count"] == 1
    sections = body["lesson"]["sections"]
    assert sections[0]["source_references"] == [
        {"page_number": 1, "excerpt": "plants use to make glucose"}
    ]
    assert sections[1]["source_references"] == [
        {"page_number": 2, "excerpt": "reflects green light, so leaves look green"}
    ]
    assert any("moved to the right page" in warning for warning in metadata["warnings"])
    assert '<page number="2">' in provider.calls[0]["input_text"]
    assert fetched.json() == body


@pytest.mark.parametrize(
    ("error", "status_code", "code"),
    [
        (AIRateLimitError("quota exhausted"), 429, "AI_RATE_LIMITED"),
        (AIInvalidResponseError("bad output"), 502, "AI_INVALID_RESPONSE"),
        (AIProviderError("connection refused"), 503, "AI_PROVIDER_UNAVAILABLE"),
        # The message shape `GeminiProvider`/`OpenAICompatibleProvider` actually raise for a
        # timeout (see their `except` clauses): a plain `AIProviderError`, with no special-casing.
        # This proves a hung request surfaces as a normal 503, never the generic 500 handler.
        (
            AIProviderError("Gemini request failed: APITimeoutError."),
            503,
            "AI_PROVIDER_UNAVAILABLE",
        ),
        # The message shape the application-level wall-clock deadline raises, for a request that
        # hangs past its deadline rather than failing at the transport.
        (
            AIProviderError("openrouter request exceeded its 35s deadline."),
            503,
            "AI_PROVIDER_UNAVAILABLE",
        ),
    ],
    ids=["rate-limited", "invalid-response", "unavailable", "timeout", "hard-deadline"],
)
def test_ai_failures_return_clear_errors(
    settings: Settings, error: Exception, status_code: int, code: str
) -> None:
    with _ai_client(settings, FakeProvider([error])) as client:
        response = _upload(client, make_pdf(PAGES))

    assert response.status_code == status_code
    assert _error_code(response) == code
    assert str(error) not in response.text


def test_ai_draft_that_cannot_become_a_lesson_is_reported(settings: Settings) -> None:
    unusable = LessonDraft(title="", overview="", sections=[], quiz=[])

    with _ai_client(settings, FakeProvider([unusable])) as client:
        response = _upload(client, make_pdf(PAGES))

    assert response.status_code == 502
    assert _error_code(response) == "LESSON_VALIDATION_FAILED"
