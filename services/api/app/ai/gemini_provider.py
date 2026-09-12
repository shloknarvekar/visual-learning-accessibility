"""Google Gemini implementation of `AIProvider`.

The only module that imports the Gemini SDK. Uses the Interactions API with a JSON-schema response
format, as documented at https://ai.google.dev/gemini-api/docs/structured-output (checked against
google-genai 2.23 in September 2026).
"""

import asyncio
from typing import Any, Self

import httpx
from google import genai
from google.genai.types import HttpOptions, HttpRetryOptions
from pydantic import BaseModel, ValidationError

from app.ai.provider import (
    AIConfigurationError,
    AIInvalidResponseError,
    AIProviderError,
    AIRateLimitError,
    ModelT,
)
from app.core.config import Settings

# Bounds a single HTTP attempt, not the whole document: a chunked document makes one call per
# chunk, and a hang on any one of them raises `AIProviderError` (see the except clause below) and
# fails over immediately - the timeout only needs to cover one request's normal latency, not a
# whole document.
#
# Gemini is tried first, so this is the shortest of the three provider timeouts: two more live
# providers are still ahead of it in `RoutingLessonGenerator`, so cutting it off early is cheap.
# A provider later in the chain gets more patience because failing it early costs more - there is
# less chain left to still produce a real, if slow, answer. See docs/architecture/overview.md.
REQUEST_TIMEOUT_SECONDS = 25.0
_HTTP_TOO_MANY_REQUESTS = 429

# JSON Schema keywords Gemini documents as supported for structured output. Anything else (for
# example "default", "pattern" or "$defs") is left out of the request; Pydantic still validates the
# full model when the response comes back.
_SUPPORTED_SCHEMA_KEYWORDS = frozenset(
    {
        "type",
        "properties",
        "required",
        "items",
        "prefixItems",
        "minItems",
        "maxItems",
        "enum",
        "format",
        "minimum",
        "maximum",
        "anyOf",
        "title",
        "description",
        "additionalProperties",
    }
)


PROVIDER_NAME = "gemini"

# The SDK retries 408/409/429/5xx itself before raising. With a router in front, waiting inside one
# provider is the wrong place to spend time: a 429 carrying Retry-After is honoured as-is, so a
# single retry can block for as long as the service asks before failover even starts.
#
# `attempts` cannot express "no retries" here. It is normalised from 0 to 1 while the client is
# built, and the Interactions API reads it as a retry *count*, so any value still allows one retry.
# `http_status_codes` can: it replaces the retryable set, and its documented meaning is "codes that
# should trigger a retry". Narrowing it to a code the API never returns leaves nothing to retry.
# An empty list does not work - the SDK treats it as falsy and restores its defaults.
# See docs/architecture/overview.md.
RETRYABLE_STATUS_CODES = [418]  # "I'm a teapot": never returned by the Gemini API
MIN_SDK_ATTEMPTS = 1  # the floor the SDK allows; irrelevant while nothing is retryable


class GeminiProvider:
    def __init__(self, *, client: genai.Client, model: str) -> None:
        self._client = client
        self.name = PROVIDER_NAME
        self.model_name = model

    @classmethod
    def from_settings(
        cls, settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None
    ) -> Self:
        if settings.gemini_api_key is None:
            raise AIConfigurationError("Set GEMINI_API_KEY to use the Gemini provider.")
        # Built fresh for every client: the SDK rewrites `attempts` in place while the client is
        # constructed, so a shared instance would be mutated.
        http_options = HttpOptions(
            retry_options=HttpRetryOptions(
                attempts=MIN_SDK_ATTEMPTS, http_status_codes=RETRYABLE_STATUS_CODES
            )
        )
        if transport is not None:
            http_options.async_client_args = {"transport": transport}
        client = genai.Client(
            api_key=settings.gemini_api_key.get_secret_value(), http_options=http_options
        )
        return cls(client=client, model=settings.gemini_model)

    async def generate_structured(
        self, *, instructions: str, input_text: str, output_model: type[ModelT]
    ) -> ModelT:
        try:
            # Hard wall-clock deadline over the whole call. The SDK's own `timeout` below is
            # handed to httpx as a per-operation budget, whose read clock restarts on every byte
            # received - a service that trickles bytes can outlive it (observed on the
            # OpenAI-compatible providers: a 320s call against a 35s httpx timeout). This bounds
            # the total instead. The SDK is not modified; it is simply run under a deadline.
            async with asyncio.timeout(REQUEST_TIMEOUT_SECONDS):
                interaction = await self._client.aio.interactions.create(
                    model=self.model_name,
                    system_instruction=instructions,
                    input=input_text,
                    response_format={
                        "type": "text",
                        "mime_type": "application/json",
                        "schema": gemini_response_schema(output_model),
                    },
                    store=False,  # don't keep course material stored for later retrieval
                    timeout=REQUEST_TIMEOUT_SECONDS,
                )
        except TimeoutError as exc:
            # Must precede the catch-all below, which would otherwise report this as a generic
            # failure. `asyncio.timeout` turns its own cancellation into `TimeoutError`; an
            # external cancellation stays a `CancelledError` (a `BaseException`) and so is caught
            # by neither clause, keeping shutdown distinct from a provider failure.
            raise AIProviderError(
                f"Gemini request exceeded its {REQUEST_TIMEOUT_SECONDS:g}s deadline."
            ) from exc
        except Exception as exc:
            # The SDK's error classes live in private modules that move between releases, so this
            # boundary converts every failure. The original exception stays attached as __cause__.
            status_code: Any = getattr(exc, "status_code", None)
            if status_code == _HTTP_TOO_MANY_REQUESTS:
                raise AIRateLimitError("Gemini rate limit reached (free-tier quota).") from exc
            reason = f"HTTP {status_code}" if status_code is not None else type(exc).__name__
            raise AIProviderError(f"Gemini request failed: {reason}.") from exc

        text = interaction.output_text
        if not text:
            raise AIInvalidResponseError("Gemini returned no output.")
        try:
            return output_model.model_validate_json(text)
        except ValidationError as exc:
            raise AIInvalidResponseError(
                "Gemini output did not match the requested schema."
            ) from exc


def gemini_response_schema(model: type[BaseModel]) -> dict[str, Any]:
    """`model`'s JSON schema, self-contained and limited to keywords Gemini supports."""
    schema = model.model_json_schema()
    simplified: dict[str, Any] = _simplify(schema, schema.get("$defs", {}))
    return simplified


def _simplify(node: Any, definitions: dict[str, Any]) -> Any:
    if isinstance(node, list):
        return [_simplify(item, definitions) for item in node]
    if not isinstance(node, dict):
        return node
    if "$ref" in node:
        referenced = definitions[node["$ref"].rsplit("/", 1)[-1]]
        siblings = {key: value for key, value in node.items() if key != "$ref"}
        return _simplify({**referenced, **siblings}, definitions)

    simplified: dict[str, Any] = {}
    for key, value in node.items():
        if key == "const":
            simplified["enum"] = [value]
        elif key == "oneOf":
            simplified["anyOf"] = _simplify(value, definitions)
        elif key == "properties":
            simplified[key] = {name: _simplify(sub, definitions) for name, sub in value.items()}
        elif key in _SUPPORTED_SCHEMA_KEYWORDS:
            simplified[key] = _simplify(value, definitions)
    return simplified
