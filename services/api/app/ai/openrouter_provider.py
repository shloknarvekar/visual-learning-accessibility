"""OpenRouter provider: first fallback when the primary provider is unavailable.

OpenRouter's free models (ids ending in `:free`) need no payment method. Only some of them support
structured outputs, so the default model is one that does; see docs/architecture/overview.md.
Free-tier limits at the time of writing: 20 requests per minute and 50 per day without credits.
"""

from typing import Any

import httpx

from app.ai.openai_compatible import OpenAICompatibleProvider
from app.ai.provider import AIConfigurationError
from app.core.config import Settings

PROVIDER_NAME = "openrouter"

# The first fallback: one live provider (Groq) still follows it, so it gets more patience than
# Gemini but less than Groq. See the failover-latency note in docs/architecture/overview.md.
REQUEST_TIMEOUT_SECONDS = 35.0

# ---- OpenRouter-specific request fields --------------------------------------------------------
#
# These exist because one real request spent 320 seconds and came back HTTP 200 with an empty
# `content` field: the documented signature of a reasoning model whose output budget went on
# deliberation, leaving nothing for the answer. They are sent only by this provider; Groq shares
# the HTTP implementation but not these fields.

# Completion budget for one structured lesson. Measured against the strict `LessonDraft` schema: a
# rich ten-section lesson with five quiz questions serialises to about 2,800 tokens compact, or
# about 4,300 with the whitespace models tend to emit. This leaves comfortable headroom for a
# legitimate answer while still bounding a runaway generation.
MAX_COMPLETION_TOKENS = 8000

# Reasoning off: this is a latency-bounded fallback, and OpenRouter bills reasoning as output
# tokens, so unbounded deliberation is exactly what consumed the budget last time.
#
# Caveat worth knowing before the next live test: OpenRouter documents that a model whose reasoning
# is `mandatory` *rejects* `effort: "none"`, and the model page does not say whether this one is.
# A rejection surfaces as a normal HTTP error, so it fails over to Groq rather than hanging. The
# documented setting that works either way is `{"max_tokens": 1024, "exclude": True}`, which bounds
# deliberation to the documented minimum instead of removing it.
REASONING = {"effort": "none"}

# Route only to an upstream provider that honours every parameter above - `response_format` most of
# all. Without this, OpenRouter may pick a provider that ignores one, which is how a structured
# request quietly comes back unstructured.
PROVIDER_ROUTING = {"require_parameters": True}


class OpenRouterProvider(OpenAICompatibleProvider):
    def _extra_body_fields(self) -> dict[str, Any]:
        # Copied so a caller mutating the request can never edit the module-level defaults.
        return {
            "max_tokens": MAX_COMPLETION_TOKENS,
            "reasoning": dict(REASONING),
            "provider": dict(PROVIDER_ROUTING),
        }

    @classmethod
    def from_settings(
        cls, settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None
    ) -> "OpenRouterProvider":
        if settings.openrouter_api_key is None:
            raise AIConfigurationError("Set OPENROUTER_API_KEY to use the OpenRouter provider.")
        # Optional attribution headers OpenRouter uses to label traffic from this app.
        extra_headers = {}
        if settings.openrouter_app_url:
            extra_headers["HTTP-Referer"] = settings.openrouter_app_url
        if settings.openrouter_app_title:
            extra_headers["X-Title"] = settings.openrouter_app_title
        return cls(
            name=PROVIDER_NAME,
            model=settings.openrouter_model,
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            extra_headers=extra_headers,
            timeout_seconds=REQUEST_TIMEOUT_SECONDS,
            transport=transport,
        )
