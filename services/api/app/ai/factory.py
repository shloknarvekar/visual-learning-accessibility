"""Builds the AI stack from settings. The only module that knows which providers exist.

The primary provider is tried first, then each configured fallback, then the cache, then demo
content. Adding a provider means one `AIProvider` implementation and one entry in `_PROVIDERS`.
"""

import logging
from collections.abc import Callable

from app.ai.ai_lesson_generator import AILessonGenerator
from app.ai.gemini_provider import GeminiProvider
from app.ai.groq_provider import GroqProvider
from app.ai.lesson_cache import FileLessonCache, NullLessonCache
from app.ai.lesson_generator import LessonGenerator, LessonProviderName
from app.ai.mock_lesson_generator import MockLessonGenerator
from app.ai.openrouter_provider import OpenRouterProvider
from app.ai.provider import AIProvider
from app.ai.routing import RoutingLessonGenerator
from app.core.config import AIProviderName, Settings

logger = logging.getLogger(__name__)

# A provider is available only when its key is set, so an unconfigured one is skipped silently.
_PROVIDERS: dict[str, tuple[Callable[[Settings], AIProvider], Callable[[Settings], bool]]] = {
    "gemini": (GeminiProvider.from_settings, lambda s: s.gemini_api_key is not None),
    "openrouter": (OpenRouterProvider.from_settings, lambda s: s.openrouter_api_key is not None),
    "groq": (GroqProvider.from_settings, lambda s: s.groq_api_key is not None),
}


def available_providers(settings: Settings) -> list[LessonProviderName]:
    """Configured providers in the order they will be tried: primary first, then fallbacks."""
    if settings.ai_provider == "mock":
        return []
    order = [settings.ai_provider, *settings.ai_fallback_providers]
    chosen: list[LessonProviderName] = []
    for name in order:
        if name in _PROVIDERS and name not in chosen and _PROVIDERS[name][1](settings):
            chosen.append(name)  # type: ignore[arg-type]
    return chosen


def resolve_ai_mode(settings: Settings) -> AIProviderName:
    """The provider that will be tried first, or `mock` when none is configured."""
    providers = available_providers(settings)
    return providers[0] if providers else "mock"  # type: ignore[return-value]


def create_ai_provider(settings: Settings) -> AIProvider | None:
    """The primary provider, or None when no provider is configured."""
    providers = available_providers(settings)
    if not providers:
        return None
    return _PROVIDERS[providers[0]][0](settings)


def create_lesson_generator(settings: Settings) -> LessonGenerator:
    """A router over the configured providers, or deterministic demo lessons when there are none."""
    providers = available_providers(settings)
    if not providers:
        return MockLessonGenerator()

    live: list[tuple[LessonProviderName, LessonGenerator]] = []
    for name in providers:
        provider = _PROVIDERS[name][0](settings)
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

    cache = (
        FileLessonCache(settings.data_dir / "cache")
        if settings.ai_cache_enabled
        else NullLessonCache()
    )
    return RoutingLessonGenerator(
        live=live,
        cache=cache,
        demo=MockLessonGenerator() if settings.ai_fallback_to_demo else None,
    )
