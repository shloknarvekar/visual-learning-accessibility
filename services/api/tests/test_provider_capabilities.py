"""Which providers can read which inputs, and what happens when none of them can.

No provider is ever called here. Building one only constructs a client, so these tests stay
entirely offline while still proving the real wiring decisions.
"""

import asyncio
from pathlib import Path

import pytest

from app.ai.factory import (
    _PROVIDERS,
    available_providers,
    create_video_lesson_generator,
    create_video_uploader,
    video_capable_provider_names,
)
from app.ai.lesson_cache import NullLessonCache
from app.ai.lesson_generator import VideoLessonGenerationRequest
from app.ai.mock_lesson_generator import MockLessonGenerator
from app.ai.provider import AIInputNotSupportedError, AIProviderError
from app.ai.routing import RoutingLessonGenerator
from app.ai.video_upload import GeminiFilesUploader, NullVideoUploader
from app.core.config import Settings
from app.models.media import VideoSource
from app.schemas.lesson import Source

YOUTUBE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def settings_with(tmp_path: Path, **keys: str) -> Settings:
    provider = keys.pop("ai_provider", "gemini")
    return Settings(
        _env_file=None,
        app_env="test",
        data_dir=tmp_path / "data",
        ai_provider=provider,  # type: ignore[arg-type]
        ai_fallback_providers=["openrouter", "groq"],
        **keys,  # type: ignore[arg-type]
    )


def video_request() -> VideoLessonGenerationRequest:
    return VideoLessonGenerationRequest(
        lesson_id="video-1",
        source=Source(source_type="youtube", title="YouTube video", url=YOUTUBE_URL),
        video=VideoSource(kind="youtube", uri=YOUTUBE_URL, processing="static"),
        identity=YOUTUBE_URL,
    )


# ---- The capability table ----------------------------------------------------------------------


def test_only_gemini_is_declared_able_to_watch_a_video() -> None:
    assert video_capable_provider_names() == ["gemini"]


@pytest.mark.parametrize("name", sorted(_PROVIDERS))
def test_the_table_matches_what_each_provider_actually_reports(name: str, tmp_path: Path) -> None:
    """The table is what routing is built from, so it must not drift from the implementations."""
    entry = _PROVIDERS[name]
    built = entry.build(
        settings_with(
            tmp_path,
            gemini_api_key="test-key",
            openrouter_api_key="test-key",
            groq_api_key="test-key",
        )
    )

    assert built.modalities == entry.modalities


def test_every_provider_can_at_least_read_text() -> None:
    assert all("text" in entry.modalities for entry in _PROVIDERS.values())


# ---- Which providers are chosen ----------------------------------------------------------------


def test_text_generation_uses_every_configured_provider(tmp_path: Path) -> None:
    settings = settings_with(tmp_path, gemini_api_key="k", openrouter_api_key="k", groq_api_key="k")

    assert available_providers(settings) == ["gemini", "openrouter", "groq"]


def test_video_generation_uses_only_the_providers_that_can_watch(tmp_path: Path) -> None:
    settings = settings_with(tmp_path, gemini_api_key="k", openrouter_api_key="k", groq_api_key="k")

    assert available_providers(settings, modality="video") == ["gemini"]


def test_a_text_only_setup_offers_nothing_for_video(tmp_path: Path) -> None:
    settings = settings_with(
        tmp_path, ai_provider="openrouter", openrouter_api_key="k", groq_api_key="k"
    )

    assert available_providers(settings) == ["openrouter", "groq"]
    assert available_providers(settings, modality="video") == []


# ---- What gets built ---------------------------------------------------------------------------


def test_a_video_capable_setup_gets_a_real_router(tmp_path: Path) -> None:
    generator = create_video_lesson_generator(settings_with(tmp_path, gemini_api_key="k"))

    assert isinstance(generator, RoutingLessonGenerator)


def test_a_text_only_setup_gets_no_video_generator_at_all(tmp_path: Path) -> None:
    """None is the signal for a capability gap. The service turns it into a clear error rather

    than quietly answering with a lesson about something else.
    """
    settings = settings_with(
        tmp_path, ai_provider="openrouter", openrouter_api_key="k", groq_api_key="k"
    )

    assert create_video_lesson_generator(settings) is None
    assert create_video_uploader(settings) is None


def test_with_nothing_configured_video_behaves_like_every_other_input(tmp_path: Path) -> None:
    """Mock mode has to keep working for video too, or the product stops being free to demo."""
    settings = settings_with(tmp_path)

    assert isinstance(create_video_lesson_generator(settings), MockLessonGenerator)
    assert isinstance(create_video_uploader(settings), NullVideoUploader)


def test_the_uploader_is_the_same_service_that_will_watch_the_video(tmp_path: Path) -> None:
    uploader = create_video_uploader(settings_with(tmp_path, gemini_api_key="k"))

    assert isinstance(uploader, GeminiFilesUploader)


# ---- What the router does with a capability mismatch -------------------------------------------


class _RefusingGenerator:
    """Stands in for a generator whose provider cannot read the request's input."""

    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, request: object) -> object:
        self.calls += 1
        raise AIInputNotSupportedError("groq cannot take video input (it accepts: text).")


class _BrokenGenerator:
    async def generate(self, request: object) -> object:
        raise AIProviderError("HTTP 503")


def test_a_capability_mismatch_stops_the_chain_instead_of_becoming_demo_content() -> None:
    """Falling through to demo here would hide a misconfiguration behind a plausible lesson."""
    router = RoutingLessonGenerator(
        live=[("groq", _RefusingGenerator())],  # type: ignore[list-item]
        cache=NullLessonCache(),
        demo=MockLessonGenerator(),
    )

    with pytest.raises(AIInputNotSupportedError):
        asyncio.run(router.generate(video_request()))


def test_a_real_outage_still_falls_back_to_demo_content() -> None:
    """The contrast that makes the test above meaningful: outages are recoverable, gaps are not."""
    router = RoutingLessonGenerator(
        live=[("gemini", _BrokenGenerator())],  # type: ignore[list-item]
        cache=NullLessonCache(),
        demo=MockLessonGenerator(),
    )

    generated = asyncio.run(router.generate(video_request()))

    assert generated.generation_status == "demo"
    assert any("does not describe this video" in warning for warning in generated.warnings)


def test_a_later_provider_is_not_tried_after_a_capability_mismatch() -> None:
    first, second = _RefusingGenerator(), _RefusingGenerator()
    router = RoutingLessonGenerator(
        live=[("groq", first), ("openrouter", second)],  # type: ignore[list-item]
        cache=NullLessonCache(),
        demo=MockLessonGenerator(),
    )

    with pytest.raises(AIInputNotSupportedError):
        asyncio.run(router.generate(video_request()))

    assert (first.calls, second.calls) == (1, 0)
