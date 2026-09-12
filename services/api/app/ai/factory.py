"""Builds the AI stack from settings. The only module that knows which providers exist.

The primary provider is tried first, then each configured fallback, then the cache, then demo
content. Adding a provider means one `AIProvider` implementation and one entry in `_PROVIDERS`.

Each entry also declares what that provider can read. Routing is built per input type from that
declaration, so a video request is never handed to a text-only service: the chain for video simply
does not contain one. When nothing configured can read video at all, the video generator is `None`
and the caller reports a capability error rather than quietly serving something else.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass

from app.ai.ai_lesson_generator import AILessonGenerator
from app.ai.gemini_provider import GeminiProvider
from app.ai.groq_provider import GroqProvider
from app.ai.lesson_cache import FileLessonCache, LessonCache, NullLessonCache
from app.ai.lesson_generator import LessonGenerator, LessonProviderName
from app.ai.mock_lesson_generator import MockLessonGenerator
from app.ai.openrouter_provider import OpenRouterProvider
from app.ai.provider import TEXT_AND_VIDEO, TEXT_ONLY, AIProvider, Modality
from app.ai.routing import RoutingLessonGenerator
from app.ai.video_lesson_generator import VideoLessonGenerator
from app.ai.video_upload import GeminiFilesUploader, NullVideoUploader, VideoUploader
from app.core.config import AIProviderName, Settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _ProviderEntry:
    """How to build a provider, when it is usable, and what it can read.

    Capability sits beside the constructor so it can be consulted without building a client, and so
    adding a provider means stating it once. `test_provider_capabilities` checks this table against
    what the built instances report, so the two cannot drift apart.
    """

    build: Callable[[Settings], AIProvider]
    is_configured: Callable[[Settings], bool]
    modalities: frozenset[Modality]


# A provider is available only when its key is set, so an unconfigured one is skipped silently.
_PROVIDERS: dict[str, _ProviderEntry] = {
    "gemini": _ProviderEntry(
        GeminiProvider.from_settings,
        lambda s: s.gemini_api_key is not None,
        TEXT_AND_VIDEO,
    ),
    "openrouter": _ProviderEntry(
        OpenRouterProvider.from_settings,
        lambda s: s.openrouter_api_key is not None,
        TEXT_ONLY,
    ),
    "groq": _ProviderEntry(
        GroqProvider.from_settings,
        lambda s: s.groq_api_key is not None,
        TEXT_ONLY,
    ),
}


def available_providers(
    settings: Settings, *, modality: Modality = "text"
) -> list[LessonProviderName]:
    """Configured providers that can read `modality`, primary first, then fallbacks."""
    if settings.ai_provider == "mock":
        return []
    order = [settings.ai_provider, *settings.ai_fallback_providers]
    chosen: list[LessonProviderName] = []
    for name in order:
        entry = _PROVIDERS.get(name)
        if entry is None or name in chosen:
            continue
        if entry.is_configured(settings) and modality in entry.modalities:
            chosen.append(name)  # type: ignore[arg-type]
    return chosen


def video_capable_provider_names() -> list[str]:
    """Which providers this build can use to watch a video, configured or not."""
    return sorted(name for name, entry in _PROVIDERS.items() if "video" in entry.modalities)


def resolve_ai_mode(settings: Settings) -> AIProviderName:
    """The provider that will be tried first, or `mock` when none is configured."""
    providers = available_providers(settings)
    return providers[0] if providers else "mock"  # type: ignore[return-value]


def create_ai_provider(settings: Settings) -> AIProvider | None:
    """The primary provider, or None when no provider is configured."""
    providers = available_providers(settings)
    if not providers:
        return None
    return _PROVIDERS[providers[0]].build(settings)


def create_lesson_generator(settings: Settings) -> LessonGenerator:
    """A router over the configured providers, or deterministic demo lessons when there are none."""
    providers = available_providers(settings)
    if not providers:
        return MockLessonGenerator()

    live: list[tuple[LessonProviderName, LessonGenerator]] = []
    for name in providers:
        provider = _PROVIDERS[name].build(settings)
        live.append(
            (
                name,
                AILessonGenerator(
                    provider,
                    single_pass_max_chars=settings.ai_single_pass_max_chars,
                    max_chunks=settings.ai_max_chunks,
                ),
            )
        )
    logger.info("ai providers configured", extra={"providers": [name for name, _ in live]})
    return _router(settings, live)


def create_video_lesson_generator(settings: Settings) -> LessonGenerator | None:
    """A router over the video-capable providers.

    Returns demo content when nothing at all is configured, so video behaves like every other input
    in mock mode and the product stays usable at zero cost. Returns None when providers *are*
    configured but none of them can watch a video - a real capability gap, which the caller turns
    into a clear error instead of a lesson about the wrong thing.
    """
    configured = available_providers(settings)
    if not configured:
        return MockLessonGenerator()

    providers = available_providers(settings, modality="video")
    if not providers:
        logger.warning("no configured AI provider can read video", extra={"providers": configured})
        return None

    live: list[tuple[LessonProviderName, LessonGenerator]] = []
    for name in providers:
        provider = _PROVIDERS[name].build(settings)
        live.append((name, VideoLessonGenerator(provider)))  # type: ignore[arg-type]
    logger.info("video providers configured", extra={"providers": [name for name, _ in live]})
    return _router(settings, live)


def create_video_uploader(settings: Settings) -> VideoUploader | None:
    """Somewhere to put an uploaded video so a provider can watch it, when one can.

    Tied to the same provider that will read the URI: a Files API address only means anything to
    the service that issued it, so this is not a free choice among configured providers.

    With nothing configured at all the upload is inert rather than absent, so mock mode answers a
    video upload the same way it answers a PDF. `None` is returned only for the genuine gap: real
    providers, none of which can watch a video.
    """
    if not available_providers(settings):
        return NullVideoUploader()
    if "gemini" not in available_providers(settings, modality="video"):
        return None
    return GeminiFilesUploader.from_settings(settings)


def _router(
    settings: Settings, live: list[tuple[LessonProviderName, LessonGenerator]]
) -> RoutingLessonGenerator:
    cache: LessonCache = (
        FileLessonCache(settings.data_dir / "cache")
        if settings.ai_cache_enabled
        else NullLessonCache()
    )
    return RoutingLessonGenerator(
        live=live,
        cache=cache,
        demo=MockLessonGenerator() if settings.ai_fallback_to_demo else None,
    )
