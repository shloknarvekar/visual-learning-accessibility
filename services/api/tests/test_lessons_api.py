"""End-to-end lessons API tests: upload, extract, chunk, generate, validate and store."""

from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker

from app.ai.ai_lesson_generator import AILessonGenerator
from app.ai.drafts import (
    DraftChartPoint,
    DraftChartSeries,
    DraftEdge,
    DraftNode,
    DraftQuizQuestion,
    DraftSection,
    DraftSourceReference,
    DraftStep,
    DraftTimelineEvent,
    LessonDraft,
)
from app.ai.lesson_cache import FileLessonCache, NullLessonCache
from app.ai.mock_lesson_generator import MockLessonGenerator
from app.ai.provider import AIInvalidResponseError, AIProviderError, AIRateLimitError
from app.ai.routing import RoutingLessonGenerator
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

# A third page adds dated events and numeric data, so every section type (including timeline and
# chart, which need material RICH_PAGES's two pages don't) can cite real, checkable source text.
RICH_PAGES = [
    *PAGES,
    "The Calvin cycle turns carbon dioxide into glucose in a series of steps. In 1930 Cornelis "
    "van Niel proposed the modern equation for photosynthesis. By 1950 scientists had confirmed "
    "the light and dark reactions. In an experiment, 12 bubbles formed per minute at 10 cm and "
    "30 bubbles formed per minute at 5 cm from the lamp.",
]

ALL_SECTION_TYPES = frozenset(
    {
        "concept",
        "explanation",
        "process",
        "comparison",
        "timeline",
        "example",
        "concept_map",
        "diagram",
        "chart",
    }
)


def _full_draft() -> LessonDraft:
    """One `LessonDraft` exercising all nine section types, each grounded in `RICH_PAGES`."""

    def ref(page: int, excerpt: str) -> DraftSourceReference:
        return DraftSourceReference(page_number=page, excerpt=excerpt)

    return LessonDraft(
        title="Photosynthesis",
        overview="How plants convert light into chemical energy, and how we learned this.",
        sections=[
            DraftSection(
                type="concept",
                title="Photosynthesis",
                term="Photosynthesis",
                definition="How plants make glucose from light, water and carbon dioxide.",
                source_references=[ref(1, "plants use to make glucose")],
            ),
            DraftSection(
                type="explanation",
                title="Why leaves look green",
                body="Chlorophyll reflects green light.",
                source_references=[ref(2, "reflects green light, so leaves look green")],
            ),
            DraftSection(
                type="process",
                title="The Calvin cycle",
                steps=[
                    DraftStep(title="Fix carbon", description="Carbon dioxide is fixed."),
                    DraftStep(title="Reduce", description="The fixed carbon is reduced."),
                ],
                source_references=[ref(3, "The Calvin cycle turns carbon dioxide into glucose")],
            ),
            DraftSection(
                type="comparison",
                title="Light vs dark reactions",
                items=["Light reactions", "Dark reactions"],
                rows=[{"criterion": "Needs light", "values": ["Yes", "No"]}],
                source_references=[ref(3, "confirmed the light and dark reactions")],
            ),
            DraftSection(
                type="timeline",
                title="Discovery timeline",
                events=[
                    DraftTimelineEvent(
                        time_label="1930",
                        title="Modern equation",
                        description="Proposed by van Niel.",
                    ),
                    DraftTimelineEvent(
                        time_label="1950",
                        title="Reactions confirmed",
                        description="Both stages shown.",
                    ),
                ],
                source_references=[
                    ref(3, "In 1930 Cornelis van Niel proposed the modern equation")
                ],
            ),
            DraftSection(
                type="example",
                title="A worked example",
                scenario="A plant in sunlight absorbs carbon dioxide.",
                explanation="This is photosynthesis in action.",
                source_references=[ref(1, "plants use to make glucose")],
            ),
            DraftSection(
                type="concept_map",
                title="How the stages relate",
                summary="Light reactions feed the Calvin cycle.",
                nodes=[
                    DraftNode(id="n1", label="Light reactions"),
                    DraftNode(id="n2", label="Calvin cycle"),
                ],
                edges=[DraftEdge(from_id="n1", to_id="n2", label="feeds")],
                source_references=[ref(3, "The Calvin cycle turns carbon dioxide into glucose")],
            ),
            DraftSection(
                type="diagram",
                title="The cycle",
                diagram_type="cycle",
                summary="Carbon dioxide becomes glucose in a loop.",
                nodes=[DraftNode(id="d1", label="CO2"), DraftNode(id="d2", label="Glucose")],
                edges=[DraftEdge(from_id="d1", to_id="d2", label="becomes")],
                source_references=[ref(3, "The Calvin cycle turns carbon dioxide into glucose")],
            ),
            DraftSection(
                type="chart",
                title="Bubbles per minute",
                chart_type="bar",
                summary="More bubbles form when the lamp is closer.",
                y_axis_label="Bubbles per minute",
                series=[
                    DraftChartSeries(
                        name="Bubbles",
                        points=[
                            DraftChartPoint(label="10 cm", value=12),
                            DraftChartPoint(label="5 cm", value=30),
                        ],
                    )
                ],
                source_references=[ref(3, "12 bubbles formed per minute at 10 cm")],
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


# Distinguishes "caller said nothing" from an explicit `demo=None`, which turns demo content off.
_DEMO_UNSET = object()


def _routed_client(
    settings: Settings,
    live: list[tuple[str, object]],
    *,
    cache: object | None = None,
    demo: object | None = _DEMO_UNSET,
) -> TestClient:
    """An app wired to the real `RoutingLessonGenerator`, the same object `create_lesson_generator`

    builds in production. `_ai_client` above bypasses routing entirely (one generator, no
    fallback); this proves the multi-provider chain, cache and demo behave correctly once wired
    into the actual HTTP surface Person 2/3 consume, not just in routing's own unit tests.
    """
    app = create_app(settings)
    generator = RoutingLessonGenerator(
        live=live,  # type: ignore[arg-type]
        cache=cache or NullLessonCache(),  # type: ignore[arg-type]
        demo=MockLessonGenerator() if demo is _DEMO_UNSET else demo,  # type: ignore[arg-type]
    )
    service = PdfLessonService.from_settings(
        settings, generator=generator, store=app.state.lesson_store
    )
    app.dependency_overrides[get_pdf_lesson_service] = lambda: service
    return TestClient(app, raise_server_exceptions=False)


def _fake_generator(*responses: object, name: str) -> AILessonGenerator:
    provider = FakeProvider(list(responses))
    provider.name = name
    return AILessonGenerator(provider, single_pass_max_chars=10_000, max_chunks=8)


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


# ---- Every section type, end to end -------------------------------------------------------------


def test_all_section_types_round_trip_through_the_api_and_match_the_shared_schema(
    settings: Settings, lesson_schema: dict[str, Any]
) -> None:
    """One PDF, one AI response, all nine section types: proves the full contract surface, not

    just the two section types the other API tests happen to exercise.
    """
    with _ai_client(settings, FakeProvider([_full_draft()])) as client:
        response = _upload(client, make_pdf(RICH_PAGES))

    assert response.status_code == 201
    lesson = response.json()["lesson"]
    sections = lesson["sections"]
    section_types = [section["type"] for section in sections]

    assert set(section_types) == ALL_SECTION_TYPES
    assert len(section_types) == len(ALL_SECTION_TYPES), "no section was silently dropped"

    validator = Draft202012Validator(lesson_schema, format_checker=FormatChecker())
    assert [error.message for error in validator.iter_errors(lesson)] == []

    by_type = {section["type"]: section for section in sections}
    # Spot-check that each section's `content` carries the shape a renderer needs, keyed only by
    # `type` - never by which provider produced it.
    assert set(by_type["concept"]["content"]) == {"term", "definition", "key_points"}
    assert set(by_type["process"]["content"]["steps"][0]) == {"id", "title", "description"}
    assert by_type["comparison"]["content"]["rows"][0]["values"] == ["Yes", "No"]
    assert len(by_type["timeline"]["content"]["events"]) == 2
    assert by_type["concept_map"]["content"]["edges"][0]["label"] == "feeds"
    assert by_type["diagram"]["content"]["diagram_type"] == "cycle"
    chart_points = by_type["chart"]["content"]["series"][0]["points"]
    assert [point["value"] for point in chart_points] == [12, 30]
    # Every section got a source reference; grounding accepted every citation without a warning.
    assert all(section["source_references"] for section in sections)
    assert lesson["quiz"]  # 3 questions, all referencing an existing section


# ---- Routing, cache and demo through the real API wiring -----------------------------------------


def test_fallback_provider_is_reported_through_the_real_api_wiring(settings: Settings) -> None:
    """The primary fails, the fallback answers: proves `RoutingLessonGenerator` reaches the HTTP

    response with correct `provider`/`generation_status`, not just in routing's own unit tests.
    """
    live = [
        ("gemini", _fake_generator(AIRateLimitError("quota"), name="gemini")),
        ("openrouter", _fake_generator(_full_draft(), name="openrouter")),
    ]
    with _routed_client(settings, live) as client:
        response = _upload(client, make_pdf(RICH_PAGES))

    assert response.status_code == 201
    metadata = response.json()["metadata"]
    assert (metadata["provider"], metadata["generation_status"]) == ("openrouter", "fallback")
    assert any("gemini" in warning for warning in metadata["warnings"])


def test_cache_is_served_through_the_real_api_wiring_when_every_provider_fails(
    settings: Settings, tmp_path: Any
) -> None:
    cache = FileLessonCache(tmp_path)
    with _routed_client(
        settings, [("gemini", _fake_generator(_full_draft(), name="gemini"))], cache=cache
    ) as client:
        first = _upload(client, make_pdf(RICH_PAGES)).json()

    with _routed_client(
        settings,
        [("gemini", _fake_generator(AIRateLimitError("quota"), name="gemini"))],
        cache=cache,
    ) as client:
        second = _upload(client, make_pdf(RICH_PAGES))

    assert second.status_code == 201
    body = second.json()
    assert (body["metadata"]["provider"], body["metadata"]["generation_status"]) == (
        "cache",
        "cached",
    )
    assert body["lesson"]["title"] == first["lesson"]["title"]
    assert any("earlier successful generation" in w for w in body["metadata"]["warnings"])


def test_demo_is_served_through_the_real_api_wiring_when_nothing_is_cached(
    settings: Settings,
) -> None:
    live = [("gemini", _fake_generator(AIProviderError("HTTP 503"), name="gemini"))]
    with _routed_client(settings, live) as client:
        response = _upload(client, make_pdf(RICH_PAGES))

    assert response.status_code == 201
    metadata = response.json()["metadata"]
    assert (metadata["provider"], metadata["generation_status"], metadata["is_mock"]) == (
        "demo",
        "demo",
        True,
    )
    assert "does not describe the uploaded PDF" in metadata["notice"]


def test_every_live_provider_failing_with_demo_off_is_a_clear_503(settings: Settings) -> None:
    """No provider, no cache, no demo: the API must still answer cleanly, never with a 500."""
    live = [("gemini", _fake_generator(AIProviderError("HTTP 503"), name="gemini"))]
    with _routed_client(settings, live, demo=None) as client:
        response = _upload(client, make_pdf(RICH_PAGES))

    assert response.status_code == 503
    assert _error_code(response) == "AI_PROVIDER_UNAVAILABLE"


def test_lesson_json_is_identical_regardless_of_which_provider_answered(
    settings: Settings,
) -> None:
    """The frontend must never need to branch on `metadata.provider`: the same draft from two

    differently-named providers must produce the same `lesson` payload, field for field.
    """
    draft = _full_draft()
    with _ai_client(settings, FakeProvider([draft])) as gemini_client:
        gemini_response = _upload(gemini_client, make_pdf(RICH_PAGES)).json()

    with _routed_client(
        settings, [("openrouter", _fake_generator(draft, name="openrouter"))]
    ) as openrouter_client:
        openrouter_response = _upload(openrouter_client, make_pdf(RICH_PAGES)).json()

    # `id` legitimately differs: it is the per-upload document id, not tied to provider identity.
    assert {**gemini_response["lesson"], "id": None} == {
        **openrouter_response["lesson"],
        "id": None,
    }
    assert gemini_response["metadata"]["provider"] != openrouter_response["metadata"]["provider"]


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
