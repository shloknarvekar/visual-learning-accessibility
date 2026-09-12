"""Tests for the OpenRouter/Groq HTTP provider. No real network: httpx.MockTransport is used."""

import asyncio
import json
import logging
import time
from typing import Any

import httpx
import pytest
from pydantic import BaseModel, SecretStr

from app.ai import groq_provider, openrouter_provider
from app.ai.drafts import LessonDraft
from app.ai.groq_provider import GroqProvider
from app.ai.openai_compatible import OpenAICompatibleProvider
from app.ai.openrouter_provider import OpenRouterProvider
from app.ai.provider import (
    AIConfigurationError,
    AIInvalidResponseError,
    AIProviderError,
    AIRateLimitError,
)
from app.core.config import Settings

# Not a real credential: a marker value these tests assert never reaches logs or error messages.
SECRET_KEY = "test-key-never-logged-123456"  # noqa: S105


class Answer(BaseModel):
    reply: str


def _completion(content: str) -> dict[str, Any]:
    return {"choices": [{"message": {"content": content}}]}


def _provider(handler: Any, *, name: str = "openrouter") -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        name=name,
        model="test-model",
        api_key=SecretStr(SECRET_KEY),
        base_url="https://example.test/api/v1",
        transport=httpx.MockTransport(handler),
    )


def _generate(provider: OpenAICompatibleProvider) -> Answer:
    return asyncio.run(
        provider.generate_structured(
            instructions="Be brief.", input_text="Hello", output_model=Answer
        )
    )


def test_successful_call_sends_a_strict_json_schema_and_returns_the_parsed_model() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["headers"] = dict(request.headers)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=_completion('{"reply": "ready"}'))

    result = _generate(_provider(handler))

    assert result == Answer(reply="ready")
    assert seen["url"] == "https://example.test/api/v1/chat/completions"
    assert seen["headers"]["authorization"].startswith("Bearer ")
    body = seen["body"]
    assert body["model"] == "test-model"
    assert [message["role"] for message in body["messages"]] == ["system", "user"]
    response_format = body["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    assert response_format["json_schema"]["schema"]["properties"]["reply"]["type"] == "string"


def test_rate_limit_raises_rate_limit_error() -> None:
    provider = _provider(lambda request: httpx.Response(429, json={"error": "slow down"}))

    with pytest.raises(AIRateLimitError):
        _generate(provider)


@pytest.mark.parametrize("status_code", [500, 502, 503, 400, 401])
def test_error_status_raises_provider_error(status_code: int) -> None:
    provider = _provider(lambda request: httpx.Response(status_code, json={"error": "nope"}))

    with pytest.raises(AIProviderError) as caught:
        _generate(provider)

    assert not isinstance(caught.value, AIInvalidResponseError)


def test_network_failure_raises_provider_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    with pytest.raises(AIProviderError):
        _generate(_provider(handler))


def test_timeout_raises_provider_error() -> None:
    """A hung request must be classified the same way a network failure is, so the router fails

    over on it rather than propagating it as an unhandled error. `httpx.ReadTimeout` is what a
    real `timeout_seconds` deadline raises; the mocked transport raises it directly so the test
    stays instantaneous instead of waiting out a real timeout.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    with pytest.raises(AIProviderError) as caught:
        _generate(_provider(handler))

    assert not isinstance(caught.value, AIRateLimitError)
    assert not isinstance(caught.value, AIInvalidResponseError)


@pytest.mark.parametrize(
    "payload",
    [
        _completion("not json"),
        _completion('{"unexpected": 1}'),
        _completion(""),
        {"choices": []},
        {"unexpected": "shape"},
    ],
    ids=["not-json", "wrong-fields", "empty", "no-choices", "wrong-shape"],
)
def test_unusable_response_raises_invalid_response_error(payload: dict[str, Any]) -> None:
    provider = _provider(lambda request: httpx.Response(200, json=payload))

    with pytest.raises(AIInvalidResponseError):
        _generate(provider)


def test_empty_output_error_reports_why_without_leaking_the_reasoning_text() -> None:
    """The exact shape behind one real 320s failure: HTTP 200, empty content, reasoning spent.

    Reported as an empty answer alone, that is indistinguishable from a model that said nothing.
    The finish reason and token counts are safe to surface and say which one it was; the reasoning
    text is not, because it can restate the source document.
    """
    document_text = "Chlorophyll absorbs red and blue light"
    payload = {
        "choices": [
            {
                "finish_reason": "length",
                "message": {"role": "assistant", "content": "", "reasoning": document_text},
            }
        ],
        "usage": {"completion_tokens": 4096, "total_tokens": 6296},
    }

    with pytest.raises(AIInvalidResponseError) as caught:
        _generate(_provider(lambda request: httpx.Response(200, json=payload)))

    message = str(caught.value)
    assert "finish_reason=length" in message
    assert "completion_tokens=4096" in message
    assert "reasoning_returned=yes" in message
    assert document_text not in message, "the reasoning text can restate the source document"


def test_empty_output_error_is_still_clear_when_nothing_is_reported() -> None:
    payload = {"choices": [{"message": {"role": "assistant", "content": ""}}]}

    with pytest.raises(AIInvalidResponseError) as caught:
        _generate(_provider(lambda request: httpx.Response(200, json=payload)))

    assert "no finish_reason or usage reported" in str(caught.value)


def test_api_key_is_never_logged_or_included_in_errors(
    caplog: pytest.LogCaptureFixture,
) -> None:
    provider = _provider(lambda request: httpx.Response(429, json={"error": "slow down"}))

    with caplog.at_level(logging.DEBUG), pytest.raises(AIRateLimitError) as caught:
        _generate(provider)

    assert SECRET_KEY not in caplog.text
    assert SECRET_KEY not in str(caught.value)


def test_openrouter_from_settings_uses_free_model_and_attribution_headers(
    settings: Settings,
) -> None:
    configured = settings.model_copy(
        update={
            "openrouter_api_key": SecretStr(SECRET_KEY),
            "openrouter_app_url": "https://example.test",
            "openrouter_app_title": "Visual Learning",
        }
    )

    provider = OpenRouterProvider.from_settings(configured)

    assert provider.name == "openrouter"
    assert provider.model_name.endswith(":free")
    assert provider._extra_headers == {
        "HTTP-Referer": "https://example.test",
        "X-Title": "Visual Learning",
    }


def test_groq_from_settings_uses_a_model_that_supports_strict_schemas(settings: Settings) -> None:
    from app.ai.groq_provider import STRICT_SCHEMA_MODELS

    configured = settings.model_copy(update={"groq_api_key": SecretStr(SECRET_KEY)})

    provider = GroqProvider.from_settings(configured)

    assert provider.name == "groq"
    assert provider.model_name in STRICT_SCHEMA_MODELS


@pytest.mark.parametrize("provider_class", [OpenRouterProvider, GroqProvider])
def test_providers_require_their_api_key(settings: Settings, provider_class: Any) -> None:
    with pytest.raises(AIConfigurationError):
        provider_class.from_settings(settings)


# ---- Hard wall-clock deadline ------------------------------------------------------------------
#
# The httpx timeout is a *per-operation* budget whose read clock restarts on every byte received,
# so a service that trickles bytes can outlive it. That is not hypothetical: one real OpenRouter
# call ran 320 seconds against a 35 second httpx timeout and returned HTTP 200 with an empty body.
# `MockTransport` ignores httpx timeouts altogether, which makes it a faithful stand-in here: if a
# request below is stopped at all, only the application-level deadline can have stopped it.

DEADLINE = 0.25  # short on purpose: these prove the mechanism, not the production constants


async def _hang_forever(request: httpx.Request) -> httpx.Response:
    await asyncio.sleep(3600)
    raise AssertionError("unreachable: the deadline should have fired")


async def _trickle(request: httpx.Request) -> httpx.Response:
    """Bytes keep arriving, every gap far shorter than the deadline, for ten times the deadline."""
    for _ in range(40):
        await asyncio.sleep(DEADLINE / 4)
    return httpx.Response(200, json=_completion('{"reply": "ready"}'))


def _provider_with_deadline(handler: Any, *, name: str = "openrouter") -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        name=name,
        model="test-model",
        api_key=SecretStr(SECRET_KEY),
        base_url="https://example.test/api/v1",
        timeout_seconds=DEADLINE,
        transport=httpx.MockTransport(handler),
    )


def test_request_that_never_answers_is_cut_off_at_the_hard_deadline() -> None:
    started = time.perf_counter()
    with pytest.raises(AIProviderError) as caught:
        _generate(_provider_with_deadline(_hang_forever))
    elapsed = time.perf_counter() - started

    assert "deadline" in str(caught.value)
    assert elapsed < DEADLINE * 4, "a transport that never answers was not stopped on time"


def test_trickled_response_is_still_cut_off_at_the_hard_deadline() -> None:
    """Regression test for the observed production failure.

    Reads keep arriving, so the lower-level per-read timeout never fires - exactly what let one
    real call run 320s against a 35s httpx timeout. The wall-clock deadline must still end it.
    """
    started = time.perf_counter()
    with pytest.raises(AIProviderError) as caught:
        _generate(_provider_with_deadline(_trickle))
    elapsed = time.perf_counter() - started

    assert "deadline" in str(caught.value)
    assert elapsed < DEADLINE * 4, "trickled reads outlived the wall-clock deadline"


def test_timed_out_request_leaves_no_pending_tasks() -> None:
    """Cancellation must unwind cleanly: no orphan tasks, and the client closed on the way out."""

    async def run() -> int:
        provider = _provider_with_deadline(_hang_forever)
        with pytest.raises(AIProviderError):
            await provider.generate_structured(
                instructions="Be brief.", input_text="Hello", output_model=Answer
            )
        return len(asyncio.all_tasks()) - 1  # minus the task running this coroutine

    assert asyncio.run(run()) == 0


def test_outside_cancellation_is_not_reported_as_a_provider_failure() -> None:
    """A shutdown must stay a `CancelledError`, not be mistaken for a timed-out provider."""

    async def run() -> str:
        provider = _provider_with_deadline(_hang_forever)
        task = asyncio.create_task(
            provider.generate_structured(
                instructions="Be brief.", input_text="Hello", output_model=Answer
            )
        )
        await asyncio.sleep(0)  # let the request start
        task.cancel()
        try:
            await task
        except AIProviderError:  # pragma: no cover - the failure this test guards against
            return "AIProviderError"
        except asyncio.CancelledError:
            return "CancelledError"
        return "no exception"

    assert asyncio.run(run()) == "CancelledError"


def test_api_key_is_never_logged_or_included_in_a_timeout_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG), pytest.raises(AIProviderError) as caught:
        _generate(_provider_with_deadline(_hang_forever))

    assert SECRET_KEY not in caplog.text
    assert SECRET_KEY not in str(caught.value)


@pytest.mark.parametrize(
    ("module", "provider_class", "key_field", "expected_deadline"),
    [
        (openrouter_provider, OpenRouterProvider, "openrouter_api_key", 35.0),
        (groq_provider, GroqProvider, "groq_api_key", 45.0),
    ],
    ids=["openrouter", "groq"],
)
def test_each_provider_enforces_its_own_hard_deadline(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    module: Any,
    provider_class: Any,
    key_field: str,
    expected_deadline: float,
) -> None:
    """Both the configured value and the fact that it is actually enforced."""
    configured_deadline = module.REQUEST_TIMEOUT_SECONDS
    assert configured_deadline == expected_deadline
    configured = settings.model_copy(update={key_field: SecretStr(SECRET_KEY)})
    assert provider_class.from_settings(configured)._timeout_seconds == expected_deadline

    # Re-built against a short deadline so the test stays fast; the wiring above is what matters.
    monkeypatch.setattr(module, "REQUEST_TIMEOUT_SECONDS", DEADLINE)
    provider = provider_class.from_settings(
        configured, transport=httpx.MockTransport(_hang_forever)
    )

    started = time.perf_counter()
    with pytest.raises(AIProviderError) as caught:
        _generate(provider)
    elapsed = time.perf_counter() - started

    assert "deadline" in str(caught.value)
    assert elapsed < DEADLINE * 4


# ---- Provider-specific request fields ----------------------------------------------------------


def _captured_body(provider_class: Any, settings: Settings, key_field: str) -> dict[str, Any]:
    """The exact JSON body a provider puts on the wire, captured from a mocked transport."""
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return httpx.Response(200, json=_completion('{"reply": "ready"}'))

    configured = settings.model_copy(update={key_field: SecretStr(SECRET_KEY)})
    provider = provider_class.from_settings(configured, transport=httpx.MockTransport(handler))
    assert _generate(provider) == Answer(reply="ready")
    return seen


def test_openrouter_sends_its_own_token_reasoning_and_routing_controls(settings: Settings) -> None:
    """The three fields added after a 320s call returned HTTP 200 with an empty body."""
    body = _captured_body(OpenRouterProvider, settings, "openrouter_api_key")

    assert body["max_tokens"] == openrouter_provider.MAX_COMPLETION_TOKENS == 8000
    assert body["reasoning"] == {"effort": "none"}
    assert body["provider"] == {"require_parameters": True}
    # The vendor fields must not have displaced the structured-output contract.
    assert body["response_format"]["json_schema"]["strict"] is True
    assert body["model"] and body["messages"]


def test_groq_never_receives_openrouter_specific_fields(settings: Settings) -> None:
    """Groq shares the HTTP implementation but must not inherit another vendor's parameters."""
    body = _captured_body(GroqProvider, settings, "groq_api_key")

    assert set(body) == {"model", "messages", "response_format"}
    for vendor_field in ("provider", "reasoning", "max_tokens"):
        assert vendor_field not in body, f"Groq was sent OpenRouter's {vendor_field}"
    assert body["response_format"]["json_schema"]["strict"] is True


def test_extra_body_fields_can_add_but_never_replace_the_core_request() -> None:
    """A subclass may contribute fields; it must not be able to swap out structured output."""

    class Overreaching(OpenAICompatibleProvider):
        def _extra_body_fields(self) -> dict[str, Any]:
            return {
                "model": "swapped-model",
                "messages": [],
                "response_format": {"type": "text"},
                "seed": 7,
            }

    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return httpx.Response(200, json=_completion('{"reply": "ready"}'))

    provider = Overreaching(
        name="openrouter",
        model="test-model",
        api_key=SecretStr(SECRET_KEY),
        base_url="https://example.test/api/v1",
        transport=httpx.MockTransport(handler),
    )
    _generate(provider)

    assert seen["model"] == "test-model"
    assert seen["response_format"]["type"] == "json_schema"
    assert seen["messages"], "the prompt must survive"
    assert seen["seed"] == 7, "additive fields should still reach the request"


def test_openrouter_still_parses_a_lesson_draft_with_the_vendor_fields_present(
    settings: Settings,
) -> None:
    """The added fields must not disturb the path that turns a reply into a `LessonDraft`."""
    draft_json = (
        '{"title": "The Water Cycle", "overview": "How water moves.", "sections": [], "quiz": []}'
    )
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return httpx.Response(200, json=_completion(draft_json))

    configured = settings.model_copy(update={"openrouter_api_key": SecretStr(SECRET_KEY)})
    provider = OpenRouterProvider.from_settings(configured, transport=httpx.MockTransport(handler))

    draft = asyncio.run(
        provider.generate_structured(
            instructions="Build a lesson.", input_text="source", output_model=LessonDraft
        )
    )

    assert isinstance(draft, LessonDraft)
    assert draft.title == "The Water Cycle"
    assert seen["max_tokens"] == openrouter_provider.MAX_COMPLETION_TOKENS


def test_vendor_fields_never_carry_the_api_key(settings: Settings) -> None:
    body = _captured_body(OpenRouterProvider, settings, "openrouter_api_key")

    assert SECRET_KEY not in json.dumps(body), "the key belongs in the header, never the body"
