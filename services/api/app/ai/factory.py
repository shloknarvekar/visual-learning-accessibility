"""Selects the AI backend from settings. The only module that knows which providers exist.

Adding a provider (for example OpenRouter or a local model) means one new `AIProvider`
implementation and one branch here; pipeline code does not change.
"""

from app.ai.gemini_provider import GeminiProvider
from app.ai.provider import AIProvider
from app.core.config import AIProviderName, Settings


def resolve_ai_mode(settings: Settings) -> AIProviderName:
    """The backend actually in use: the configured provider if it has credentials, else `mock`."""
    if settings.ai_provider == "gemini" and settings.gemini_api_key is not None:
        return "gemini"
    return "mock"


def create_ai_provider(settings: Settings) -> AIProvider | None:
    """The configured provider, or None in mock mode (callers then use MockLessonGenerator)."""
    if resolve_ai_mode(settings) == "gemini":
        return GeminiProvider.from_settings(settings)
    return None
