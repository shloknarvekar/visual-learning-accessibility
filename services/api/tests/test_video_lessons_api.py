"""End-to-end video lessons API tests: validate, ingest, generate, validate, store.

Every provider and every upload target is a fake, so nothing here reaches a network.
"""

import logging
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker

from app.ai.drafts import LessonDraft
from app.ai.lesson_cache import FileLessonCache, NullLessonCache
from app.ai.mock_lesson_generator import MockLessonGenerator
from app.ai.provider import AIInvalidResponseError, AIProviderError, AIRateLimitError
from app.ai.routing import RoutingLessonGenerator
from app.ai.video_lesson_generator import VideoLessonGenerator
from app.api.routes.lessons import get_video_lesson_service
from app.core.config import Settings
from app.main import create_app
from app.schemas.lesson import Lesson
from app.services.video_lessons import VideoLessonService
from tests.video_helpers import MP4, NOT_A_VIDEO, WEBM, FakeUploader, FakeVideoProvider, video_draft

YOUTUBE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
SHARE_URL = "https://youtu.be/dQw4w9WgXcQ?si=tracking"

_UNSET = object()


def _service_client(
    settings: Settings,
    *,
    generator: Any = _UNSET,
    uploader: Any = _UNSET,
) -> TestClient:
    """An app whose video service is wired to fakes, leaving every other route untouched."""
    app = create_app(settings)
    service = VideoLessonService.from_settings(
        settings,
        generator=(
            # Two responses queued: a couple of tests call this client's default generator
            # twice (once per endpoint) to compare the two lessons directly.
            VideoLessonGenerator(FakeVideoProvider([video_draft(), video_draft()]))
            if generator is _UNSET
            else generator
        ),
        uploader=FakeUploader() if uploader is _UNSET else uploader,
        store=app.state.lesson_store,
    )
    app.dependency_overrides[get_video_lesson_service] = lambda: service
    return TestClient(app, raise_server_exceptions=False)


def _post_youtube(client: TestClient, url: str = YOUTUBE_URL) -> httpx.Response:
    return client.post("/api/v1/lessons/youtube", json={"url": url})


def _post_video(
    client: TestClient,
    data: bytes = MP4,
    *,
    filename: str = "lecture.mp4",
    content_type: str = "video/mp4",
) -> httpx.Response:
    return client.post("/api/v1/lessons/video", files={"file": (filename, data, content_type)})


def _error_code(response: httpx.Response) -> str:
    code: str = response.json()["error"]["code"]
    return code


# ---- YouTube -----------------------------------------------------------------------------------


def test_a_youtube_link_becomes_a_stored_lesson(settings: Settings) -> None:
    with _service_client(settings) as client:
        response = _post_youtube(client)

    assert response.status_code == 201
    body = response.json()
    assert body["lesson"]["source"] == {
        "source_type": "youtube",
        "title": "YouTube video",
        "url": YOUTUBE_URL,
    }
    assert body["lesson"]["id"] == body["lesson_id"]
    Lesson.model_validate(body["lesson"])


def test_the_link_handed_to_the_provider_is_the_canonical_one(settings: Settings) -> None:
    """A share link with tracking on it must not reach the provider as the caller wrote it."""
    provider = FakeVideoProvider([video_draft()])
    with _service_client(settings, generator=VideoLessonGenerator(provider)) as client:
        response = _post_youtube(client, SHARE_URL)

    assert response.status_code == 201
    assert provider.calls[0]["video"].uri == YOUTUBE_URL
    assert response.json()["lesson"]["source"]["url"] == YOUTUBE_URL


def test_a_youtube_lesson_cites_times_instead_of_pages(settings: Settings) -> None:
    with _service_client(settings) as client:
        body = _post_youtube(client).json()

    references = [
        reference
        for section in body["lesson"]["sections"]
        for reference in section["source_references"]
    ]
    assert references
    assert all("page_number" not in reference for reference in references)
    assert all("start_time_seconds" in reference for reference in references)


def test_a_youtube_lesson_has_no_page_count_rather_than_a_made_up_one(settings: Settings) -> None:
    with _service_client(settings) as client:
        metadata = _post_youtube(client).json()["metadata"]

    assert "page_count" not in metadata
    assert "source_filename" not in metadata
    assert (metadata["chunk_count"], metadata["character_count"]) == (0, 0)


def test_a_youtube_lesson_can_be_fetched_again(settings: Settings) -> None:
    with _service_client(settings) as client:
        created = _post_youtube(client).json()
        fetched = client.get(f"/api/v1/lessons/{created['lesson_id']}")

    assert fetched.status_code == 200
    assert fetched.json() == created


@pytest.mark.parametrize(
    "url",
    ["https://vimeo.com/12345", "https://www.youtube.com/@channel", "not a url", "   "],
    ids=["other-site", "channel", "not-a-url", "blank"],
)
def test_a_link_that_is_not_a_youtube_video_is_refused(settings: Settings, url: str) -> None:
    with _service_client(settings) as client:
        response = _post_youtube(client, url)

    assert response.status_code == 422
    assert _error_code(response) == "INVALID_VIDEO_URL"


def test_a_request_without_a_url_is_a_validation_error(settings: Settings) -> None:
    with _service_client(settings) as client:
        response = client.post("/api/v1/lessons/youtube", json={})

    assert response.status_code == 422
    assert _error_code(response) == "VALIDATION_ERROR"


def test_an_absurdly_long_url_is_rejected_before_it_is_parsed(settings: Settings) -> None:
    with _service_client(settings) as client:
        response = _post_youtube(client, "https://youtu.be/" + "a" * 5000)

    assert response.status_code == 422


def test_a_bad_link_never_reaches_a_provider(settings: Settings) -> None:
    provider = FakeVideoProvider([video_draft()])
    with _service_client(settings, generator=VideoLessonGenerator(provider)) as client:
        _post_youtube(client, "https://vimeo.com/12345")

    assert provider.calls == []


# ---- Uploaded video ----------------------------------------------------------------------------


def test_an_uploaded_video_becomes_a_stored_lesson(settings: Settings) -> None:
    with _service_client(settings) as client:
        response = _post_video(client)

    assert response.status_code == 201
    body = response.json()
    assert body["lesson"]["source"] == {
        "source_type": "video",
        "title": "lecture",
        "filename": "lecture.mp4",
    }
    assert body["metadata"]["source_filename"] == "lecture.mp4"
    assert "page_count" not in body["metadata"]


def test_the_upload_is_sent_with_the_type_we_resolved_and_a_generated_name(
    settings: Settings,
) -> None:
    uploader = FakeUploader()
    with _service_client(settings, uploader=uploader) as client:
        body = _post_video(client, WEBM, filename="lecture.webm", content_type="video/webm").json()

    assert len(uploader.uploads) == 1
    upload = uploader.uploads[0]
    assert upload["mime_type"] == "video/webm"
    assert upload["path_existed"] is True
    assert upload["size_bytes"] == len(WEBM)
    # The learner's filename is kept for display but is not what the provider is told.
    assert upload["display_name"] == f"lesson-{body['lesson_id']}"
    assert "lecture" not in upload["display_name"]


@pytest.mark.parametrize(
    ("data", "filename", "content_type"),
    [
        (b"just some notes", "notes.txt", "text/plain"),
        (MP4, "lecture.mkv", "video/x-matroska"),
        (NOT_A_VIDEO, "lecture.mp4", "video/mp4"),
        (WEBM, "lecture.mp4", "video/mp4"),
        (b"%PDF-1.7 hello", "lecture.mp4", "video/mp4"),
    ],
    ids=[
        "not-a-video",
        "unsupported-container",
        "zip-renamed-to-mp4",
        "webm-declared-as-mp4",
        "pdf-declared-as-mp4",
    ],
)
def test_a_file_that_is_not_the_video_it_claims_to_be_is_refused(
    settings: Settings, data: bytes, filename: str, content_type: str
) -> None:
    with _service_client(settings) as client:
        response = _post_video(client, data, filename=filename, content_type=content_type)

    assert response.status_code == 415
    assert _error_code(response) == "INVALID_FILE_TYPE"


def test_an_empty_upload_is_refused(settings: Settings) -> None:
    with _service_client(settings) as client:
        response = _post_video(client, b"")

    assert response.status_code == 415


def test_a_video_over_the_limit_is_refused(settings: Settings) -> None:
    small_limit = settings.model_copy(update={"max_video_upload_mb": 1})
    oversized = MP4 + b"\x00" * (1024 * 1024 + 1024)

    with _service_client(small_limit) as client:
        response = _post_video(client, oversized)

    assert response.status_code == 413
    assert _error_code(response) == "FILE_TOO_LARGE"


def test_a_rejected_video_never_reaches_the_uploader(settings: Settings) -> None:
    uploader = FakeUploader()
    with _service_client(settings, uploader=uploader) as client:
        _post_video(client, NOT_A_VIDEO)

    assert uploader.uploads == []


def test_the_client_filename_is_only_used_as_display_text(settings: Settings) -> None:
    with _service_client(settings) as client:
        response = _post_video(client, filename="../../private\\lecture.mp4")

    assert response.status_code == 201
    assert response.json()["metadata"]["source_filename"] == "lecture.mp4"


def test_a_missing_file_is_a_validation_error(settings: Settings) -> None:
    with _service_client(settings) as client:
        response = client.post("/api/v1/lessons/video", data={"something": "else"})

    assert response.status_code == 422
    assert _error_code(response) == "VALIDATION_ERROR"


# ---- Clean-up ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("data", "content_type"),
    [(MP4, "video/mp4"), (NOT_A_VIDEO, "video/mp4"), (b"plain", "text/plain")],
    ids=["accepted", "rejected-by-signature", "rejected-by-type"],
)
def test_no_uploaded_video_is_left_on_disk(
    settings: Settings, data: bytes, content_type: str
) -> None:
    with _service_client(settings) as client:
        _post_video(client, data, content_type=content_type)

    uploads = settings.data_dir / "video-uploads"
    assert not uploads.exists() or not any(uploads.iterdir())


def test_the_upload_is_released_even_when_generation_fails(settings: Settings) -> None:
    uploader = FakeUploader()
    failing = VideoLessonGenerator(FakeVideoProvider([AIProviderError("HTTP 503")]))

    with _service_client(settings, generator=failing, uploader=uploader) as client:
        response = _post_video(client)

    assert response.status_code == 503
    assert uploader.released == 1
    uploads = settings.data_dir / "video-uploads"
    assert not uploads.exists() or not any(uploads.iterdir())


def test_a_failure_while_uploading_is_reported_cleanly(settings: Settings) -> None:
    uploader = FakeUploader(error=AIProviderError("Gemini rejected the video upload: HTTPError."))

    with _service_client(settings, uploader=uploader) as client:
        response = _post_video(client)

    assert response.status_code == 503
    assert _error_code(response) == "AI_PROVIDER_UNAVAILABLE"


# ---- How the video is watched ------------------------------------------------------------------


def test_a_short_upload_is_watched_in_one_cheap_pass(settings: Settings) -> None:
    uploader = FakeUploader()
    with _service_client(settings, uploader=uploader) as client:
        _post_video(client)

    assert uploader.uploads[0]["processing"] == "static"


def test_a_long_upload_is_watched_agentically(settings: Settings) -> None:
    """Size is the only length signal available without decoding the file."""
    uploader = FakeUploader()
    tuned = settings.model_copy(update={"video_agentic_threshold_mb": 1})
    long_video = MP4 + b"\x00" * (1024 * 1024)

    with _service_client(tuned, uploader=uploader) as client:
        _post_video(client, long_video)

    assert uploader.uploads[0]["processing"] == "agentic"


@pytest.mark.parametrize("mode", ["static", "agentic"])
def test_an_operator_can_force_one_processing_mode(settings: Settings, mode: str) -> None:
    uploader = FakeUploader()
    forced = settings.model_copy(update={"video_processing_mode": mode})

    with _service_client(forced, uploader=uploader) as client:
        _post_video(client, MP4 + b"\x00" * (1024 * 1024))

    assert uploader.uploads[0]["processing"] == mode


def test_a_youtube_link_is_watched_statically_because_its_length_is_unknown(
    settings: Settings,
) -> None:
    provider = FakeVideoProvider([video_draft()])
    with _service_client(settings, generator=VideoLessonGenerator(provider)) as client:
        _post_youtube(client)

    assert provider.calls[0]["video"].processing == "static"


# ---- Provider capability through the real HTTP surface -----------------------------------------


@pytest.mark.parametrize("endpoint", ["youtube", "video"])
def test_no_video_capable_provider_is_a_clear_error_not_a_500(
    settings: Settings, endpoint: str
) -> None:
    """What a text-only setup must do: say so, rather than send a video to a chat endpoint."""
    with _service_client(settings, generator=None, uploader=None) as client:
        response = _post_youtube(client) if endpoint == "youtube" else _post_video(client)

    assert response.status_code == 503
    assert _error_code(response) == "AI_INPUT_NOT_SUPPORTED"


def test_a_capability_error_explains_what_would_work(settings: Settings) -> None:
    with _service_client(settings, generator=None, uploader=None) as client:
        message = _post_youtube(client).json()["error"]["message"]

    assert "PDF" in message


@pytest.mark.parametrize(
    ("error", "status_code", "code"),
    [
        (AIRateLimitError("quota exhausted"), 429, "AI_RATE_LIMITED"),
        (AIInvalidResponseError("bad output"), 502, "AI_INVALID_RESPONSE"),
        (AIProviderError("connection refused"), 503, "AI_PROVIDER_UNAVAILABLE"),
        (
            AIProviderError("Gemini request exceeded its 300s deadline."),
            503,
            "AI_PROVIDER_UNAVAILABLE",
        ),
    ],
    ids=["rate-limited", "invalid-response", "unavailable", "hard-deadline"],
)
def test_provider_failures_return_clear_errors(
    settings: Settings, error: Exception, status_code: int, code: str
) -> None:
    generator = VideoLessonGenerator(FakeVideoProvider([error]))

    with _service_client(settings, generator=generator) as client:
        response = _post_youtube(client)

    assert response.status_code == status_code
    assert _error_code(response) == code
    assert str(error) not in response.text


def test_a_draft_that_cannot_become_a_lesson_is_reported(settings: Settings) -> None:
    unusable = LessonDraft(title="", overview="", sections=[], quiz=[])
    generator = VideoLessonGenerator(FakeVideoProvider([unusable]))

    with _service_client(settings, generator=generator) as client:
        response = _post_youtube(client)

    assert response.status_code == 502
    assert _error_code(response) == "LESSON_VALIDATION_FAILED"


# ---- Fallback, cache and demo through the real wiring ------------------------------------------


def test_demo_content_for_a_video_says_it_is_about_a_video(settings: Settings) -> None:
    router = RoutingLessonGenerator(
        live=[("gemini", VideoLessonGenerator(FakeVideoProvider([AIProviderError("HTTP 503")])))],
        cache=NullLessonCache(),
        demo=MockLessonGenerator(),
    )

    with _service_client(settings, generator=router) as client:
        metadata = _post_youtube(client).json()["metadata"]

    assert (metadata["provider"], metadata["is_mock"]) == ("demo", True)
    assert "does not describe this video" in metadata["notice"]
    assert "PDF" not in metadata["notice"]


def test_the_same_video_uploaded_twice_can_be_served_from_cache(
    settings: Settings, tmp_path: Any
) -> None:
    """The cache key is the file's content, not the one-time upload URI, so a repeat hits it."""
    cache = FileLessonCache(tmp_path / "video-cache")

    working = RoutingLessonGenerator(
        live=[("gemini", VideoLessonGenerator(FakeVideoProvider([video_draft()])))],
        cache=cache,
        demo=MockLessonGenerator(),
    )
    with _service_client(settings, generator=working) as client:
        first = _post_video(client).json()

    broken = RoutingLessonGenerator(
        live=[("gemini", VideoLessonGenerator(FakeVideoProvider([AIProviderError("HTTP 503")])))],
        cache=cache,
        demo=MockLessonGenerator(),
    )
    with _service_client(settings, generator=broken) as client:
        second = _post_video(client).json()

    assert second["metadata"]["provider"] == "cache"
    assert second["lesson"]["title"] == first["lesson"]["title"]
    assert any("same video" in warning for warning in second["metadata"]["warnings"])


# ---- One contract for every input --------------------------------------------------------------


@pytest.mark.parametrize("endpoint", ["youtube", "video"])
def test_a_video_lesson_matches_the_shared_schema(
    settings: Settings, lesson_schema: dict[str, Any], endpoint: str
) -> None:
    with _service_client(settings) as client:
        body = (_post_youtube(client) if endpoint == "youtube" else _post_video(client)).json()

    validator = Draft202012Validator(lesson_schema, format_checker=FormatChecker())
    assert [error.message for error in validator.iter_errors(body["lesson"])] == []


@pytest.mark.parametrize("endpoint", ["youtube", "video"])
def test_a_video_lesson_has_the_same_record_shape_as_a_pdf_lesson(
    settings: Settings, endpoint: str
) -> None:
    """Person 2 and Person 3 render one shape; only the always-present keys are guaranteed."""
    with _service_client(settings) as client:
        body = (_post_youtube(client) if endpoint == "youtube" else _post_video(client)).json()

    assert set(body) == {"lesson_id", "metadata", "lesson"}
    assert {
        "provider",
        "generation_status",
        "is_mock",
        "chunk_count",
        "character_count",
        "ai_request_count",
        "warnings",
        "timings",
        "created_at",
    } <= set(body["metadata"])
    assert set(body["metadata"]["timings"]) == {
        "extraction_ms",
        "chunking_ms",
        "generation_ms",
        "validation_ms",
        "total_ms",
    }


def test_the_lesson_body_never_reveals_which_endpoint_produced_it(settings: Settings) -> None:
    """Apart from `source`, a video lesson is structurally a lesson like any other."""
    with _service_client(settings) as client:
        youtube = _post_youtube(client).json()["lesson"]
        uploaded = _post_video(client).json()["lesson"]

    assert set(youtube) == set(uploaded)
    assert youtube["schema_version"] == uploaded["schema_version"] == "0.1.0"
    assert {section["type"] for section in youtube["sections"]} == {
        section["type"] for section in uploaded["sections"]
    }


# ---- Subject -------------------------------------------------------------------------------------


@pytest.mark.parametrize("endpoint", ["youtube", "video"])
def test_a_video_lesson_falls_back_to_general_when_no_subject_is_confidently_given(
    settings: Settings, endpoint: str
) -> None:
    """`video_draft()` supplies no subject by default, matching a provider that did not guess."""
    with _service_client(settings) as client:
        body = (_post_youtube(client) if endpoint == "youtube" else _post_video(client)).json()

    assert body["lesson"]["subject"] == "general"


@pytest.mark.parametrize("endpoint", ["youtube", "video"])
def test_a_confidently_given_subject_propagates_through_video_and_youtube(
    settings: Settings, endpoint: str
) -> None:
    generator = VideoLessonGenerator(FakeVideoProvider([video_draft(subject="physics")]))

    with _service_client(settings, generator=generator) as client:
        body = (_post_youtube(client) if endpoint == "youtube" else _post_video(client)).json()

    assert body["lesson"]["subject"] == "physics"


# ---- Nothing sensitive is written to the logs --------------------------------------------------


def test_the_youtube_link_is_never_written_to_the_logs(
    settings: Settings, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG), _service_client(settings) as client:
        _post_youtube(client, SHARE_URL)

    logged = "\n".join(record.getMessage() + str(record.__dict__) for record in caplog.records)
    assert "dQw4w9WgXcQ" not in logged
    assert "youtube.com" not in logged
    assert "tracking" not in logged


def test_the_uploaded_filename_is_never_written_to_the_logs(
    settings: Settings, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG), _service_client(settings) as client:
        _post_video(client, filename="my-private-lecture.mp4")

    logged = "\n".join(record.getMessage() + str(record.__dict__) for record in caplog.records)
    assert "my-private-lecture" not in logged


def test_the_provider_file_uri_is_never_written_to_the_logs(
    settings: Settings, caplog: pytest.LogCaptureFixture
) -> None:
    uploader = FakeUploader(uri="https://files.example/v/secret-handle-123")

    with caplog.at_level(logging.DEBUG), _service_client(settings, uploader=uploader) as client:
        _post_video(client)

    logged = "\n".join(record.getMessage() + str(record.__dict__) for record in caplog.records)
    assert "secret-handle-123" not in logged
