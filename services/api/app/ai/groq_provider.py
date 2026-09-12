"""Groq provider: second fallback.

Groq's OpenAI-compatible API supports `strict: true` JSON-schema output on a documented subset of
models, so the default is one of those. Free-tier limits at the time of writing: 30 requests per
minute, 1,000 per day, and 8,000 tokens per minute, which is the tightest constraint of the three
providers and can reject long documents.
"""

import httpx

from app.ai.openai_compatible import OpenAICompatibleProvider
from app.ai.provider import AIConfigurationError
from app.core.config import Settings

PROVIDER_NAME = "groq"

# The last live provider: nothing follows it but cache/demo, so a premature timeout here directly
# downgrades a real answer to demo content. It gets the most patience of the three.
# See the failover-latency note in docs/architecture/overview.md.
REQUEST_TIMEOUT_SECONDS = 45.0

# Models Groq documents as supporting strict structured output.
STRICT_SCHEMA_MODELS = frozenset({"openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.8-27b"})


class GroqProvider(OpenAICompatibleProvider):
    @classmethod
    def from_settings(
        cls, settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None
    ) -> "GroqProvider":
        if settings.groq_api_key is None:
            raise AIConfigurationError("Set GROQ_API_KEY to use the Groq provider.")
        return cls(
            name=PROVIDER_NAME,
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            base_url=settings.groq_base_url,
            timeout_seconds=REQUEST_TIMEOUT_SECONDS,
            transport=transport,
        )
