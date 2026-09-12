"""`AIProvider` for services that speak the OpenAI chat-completions API (OpenRouter, Groq).

Both providers take the same request shape, so they share this implementation and differ only in
base URL, model and headers. Requests are plain HTTP through httpx: no vendor SDK, no built-in
retries, so one logical call is exactly one HTTP request and free-tier quota stays predictable.

The API key is read from settings at call time and only ever placed in the Authorization header.
It is never logged, never stored on the instance in plain text and never included in an error.
"""

import asyncio
import json
import logging
from typing import Any

import httpx
from pydantic import SecretStr, ValidationError

from app.ai.provider import (
    TEXT_ONLY,
    AIInvalidResponseError,
    AIProviderError,
    AIRateLimitError,
    ModelT,
)
from app.ai.schema_tools import openai_strict_schema

logger = logging.getLogger(__name__)

# Fallback default only: `OpenRouterProvider` and `GroqProvider` each pass their own value below,
# chosen by how many live providers are still behind them in `RoutingLessonGenerator` (fewer
# remaining chances to still succeed means more patience is worth it). A future direct caller of
# this class should pick its timeout the same way rather than relying on this default.
REQUEST_TIMEOUT_SECONDS = 45.0
_HTTP_TOO_MANY_REQUESTS = 429


def _empty_output_reason(choice: Any, body: Any) -> str:
    """Why an empty answer was empty, using only fields that cannot carry document text.

    A reasoning model that spends its whole output budget on reasoning tokens returns exactly the
    shape this explains: HTTP 200, `content` empty, `finish_reason` "length". Without these fields
    that is indistinguishable from a model that simply answered nothing, which is what made one
    real 320-second OpenRouter failure impossible to diagnose from the error alone.

    The reasoning *text* is deliberately never included: it can restate the source document.
    """
    parts: list[str] = []
    if isinstance(choice, dict):
        for field in ("finish_reason", "native_finish_reason"):
            value = choice.get(field)
            if isinstance(value, str) and value:
                parts.append(f"{field}={value}")
        message = choice.get("message")
        if isinstance(message, dict) and message.get("reasoning"):
            parts.append("reasoning_returned=yes")  # presence only, never the text
    usage = body.get("usage") if isinstance(body, dict) else None
    if isinstance(usage, dict):
        for field in ("completion_tokens", "total_tokens"):
            value = usage.get(field)
            if isinstance(value, int):
                parts.append(f"{field}={value}")
    return ", ".join(parts) or "no finish_reason or usage reported"


class OpenAICompatibleProvider:
    """Chat-completions provider using `response_format: {"type": "json_schema", ...}`."""

    def __init__(
        self,
        *,
        name: str,
        model: str,
        api_key: SecretStr,
        base_url: str,
        extra_headers: dict[str, str] | None = None,
        timeout_seconds: float = REQUEST_TIMEOUT_SECONDS,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.name = name
        self.model_name = model
        # Chat completions carry text. These services have no way to accept a video the way the
        # Gemini video path does, and declaring that here is what stops the router from trying.
        self.modalities = TEXT_ONLY
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._extra_headers = extra_headers or {}
        self._timeout_seconds = timeout_seconds
        self._transport = transport  # tests inject a MockTransport; production leaves this None

    def _extra_body_fields(self) -> dict[str, Any]:
        """Vendor-specific request-body fields for this provider, if it has any.

        The base implementation adds nothing, so a plain OpenAI-compatible service - Groq included -
        sends the standard chat-completions body and never receives another vendor's fields. Only
        `OpenRouterProvider` overrides this today. Keeping the hook here rather than forking the
        class means one request-building path, one error boundary and one deadline for everyone.
        """
        return {}

    async def generate_structured(
        self, *, instructions: str, input_text: str, output_model: type[ModelT]
    ) -> ModelT:
        core = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": input_text},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": output_model.__name__,
                    "strict": True,
                    "schema": openai_strict_schema(output_model),
                },
            },
        }
        # Core fields are merged last, so a subclass can add to the request but can never quietly
        # replace the model, the messages or the structured-output format.
        payload = {**self._extra_body_fields(), **core}
        headers = {
            "Authorization": f"Bearer {self._api_key.get_secret_value()}",
            "Content-Type": "application/json",
            **self._extra_headers,
        }

        try:
            # Hard wall-clock deadline over the whole request/response. The httpx timeout below is
            # a *per-operation* budget (connect, read, write, pool): its read clock restarts every
            # time another byte arrives, so a service that trickles bytes can hold a request open
            # far past it. A real OpenRouter call was observed running 320s against a 35s httpx
            # timeout for exactly that reason, returning HTTP 200 with an empty body. The httpx
            # timeout stays as the cheaper lower-level safeguard; this bounds the total.
            async with asyncio.timeout(self._timeout_seconds):
                async with httpx.AsyncClient(
                    base_url=self._base_url,
                    timeout=self._timeout_seconds,
                    transport=self._transport,
                ) as client:
                    response = await client.post("/chat/completions", json=payload, headers=headers)
        except TimeoutError as exc:
            # `asyncio.timeout` cancels the awaiting task and converts that cancellation into
            # `TimeoutError` on the way out. Unwinding runs `AsyncClient.__aexit__`, so the
            # connection pool is closed and no socket or task is orphaned. A cancellation from
            # *outside* stays a `CancelledError` (a `BaseException`) and is deliberately not caught
            # here, so shutdown is never mistaken for a provider failure.
            raise AIProviderError(
                f"{self.name} request exceeded its {self._timeout_seconds:g}s deadline."
            ) from exc
        except httpx.HTTPError as exc:
            # Only the exception type is reported: messages can contain the request URL.
            # `httpx.TimeoutException` is not a builtin `TimeoutError`, so httpx's own timeouts
            # still land here rather than in the clause above.
            raise AIProviderError(f"{self.name} request failed: {type(exc).__name__}.") from exc

        if response.status_code == _HTTP_TOO_MANY_REQUESTS:
            raise AIRateLimitError(f"{self.name} rate limit reached (free-tier quota).")
        if response.status_code >= 400:
            # The body is not included: it can echo back the prompt, which holds document text.
            raise AIProviderError(f"{self.name} request failed with HTTP {response.status_code}.")

        return self._parse(response, output_model)

    def _parse(self, response: httpx.Response, output_model: type[ModelT]) -> ModelT:
        try:
            body: Any = response.json()
            choice: Any = body["choices"][0]
            content = choice["message"]["content"]
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise AIInvalidResponseError(
                f"{self.name} returned a response in an unexpected shape."
            ) from exc

        if not isinstance(content, str) or not content.strip():
            raise AIInvalidResponseError(
                f"{self.name} returned no output ({_empty_output_reason(choice, body)})."
            )

        try:
            return output_model.model_validate_json(content)
        except ValidationError as exc:
            raise AIInvalidResponseError(
                f"{self.name} output did not match the requested schema."
            ) from exc
