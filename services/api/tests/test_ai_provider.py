import asyncio
import json
import time
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from pydantic import BaseModel, SecretStr

from app.ai import gemini_provider
from app.ai.drafts import LessonDraft
from app.ai.factory import create_ai_provider, create_lesson_generator, resolve_ai_mode
from app.ai.gemini_provider import (
    RETRYABLE_STATUS_CODES,
    GeminiProvider,
    gemini_response_schema,
)
from app.ai.mock_lesson_generator import MockLessonGenerator
from app.ai.provider import (
    AIConfigurationError,
    AIInvalidResponseError,
    AIProviderError,
    AIRateLimitError,
)
from app.ai.routing import RoutingLessonGenerator
from app.core.config import Settings


class Answer(BaseModel):
    reply: str


class FakeInteractions:
    """Fake `client.aio.interactions`: records requests; returns or raises a canned result."""

    def __init__(self, *, output_text: str = "", error: Exception | None = None) -> None:
        self.output_text = output_text
        self.error = error
        self.requests: list[dict[str, Any]] = []

    async def create(self, **request: Any) -> SimpleNamespace:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return SimpleNamespace(output_text=self.output_text)


class FakeStatusError(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code


def _provider(interactions: FakeInteractions) -> GeminiProvider:
    fake_client: Any = SimpleNamespace(aio=SimpleNamespace(interactions=interactions))
    return GeminiProvider(client=fake_client, model="test-model")


def _generate(provider: GeminiProvider) -> Answer:
    return asyncio.run(
        provider.generate_structured(
            instructions="Be brief.", input_text="Hello", output_model=Answer
        )
    )


def _with_key(settings: Settings, **changes: Any) -> Settings:
    return settings.model_copy(update={"gemini_api_key": SecretStr("test-key"), **changes})


# ---- Provider selection ------------------------------------------------------------------------


def test_mock_mode_without_api_key(settings: Settings) -> None:
    assert resolve_ai_mode(settings) == "mock"
    assert create_ai_provider(settings) is None
    assert isinstance(create_lesson_generator(settings), MockLessonGenerator)


def test_mock_mode_when_requested_even_with_api_key(settings: Settings) -> None:
    settings = _with_key(settings, ai_provider="mock")

    assert resolve_ai_mode(settings) == "mock"
    assert create_ai_provider(settings) is None


def test_gemini_mode_with_api_key(settings: Settings) -> None:
    settings = _with_key(settings)

    assert resolve_ai_mode(settings) == "gemini"
    assert isinstance(create_ai_provider(settings), GeminiProvider)
    assert isinstance(create_lesson_generator(settings), RoutingLessonGenerator)


def test_gemini_provider_requires_api_key(settings: Settings) -> None:
    with pytest.raises(AIConfigurationError, match="GEMINI_API_KEY"):
        GeminiProvider.from_settings(settings)


# ---- Structured generation (fake client, no network) -------------------------------------------


def test_returns_validated_output_and_requests_json_schema() -> None:
    interactions = FakeInteractions(output_text='{"reply": "ready"}')

    result = _generate(_provider(interactions))

    assert result == Answer(reply="ready")
    request = interactions.requests[0]
    assert request["model"] == "test-model"
    assert request["system_instruction"] == "Be brief."
    assert request["response_format"] == {
        "type": "text",
        "mime_type": "application/json",
        "schema": gemini_response_schema(Answer),
    }
    assert request["store"] is False


def test_gemini_request_carries_no_openai_compatible_vendor_fields() -> None:
    """Gemini must be unaffected by OpenRouter's request customization.

    The Interactions API takes its own argument set; the OpenAI-compatible vendor fields
    (`max_tokens`, `reasoning`, `provider`) belong to a different request shape entirely and must
    never appear here.
    """
    interactions = FakeInteractions(output_text='{"reply": "ready"}')

    _generate(_provider(interactions))

    request = interactions.requests[0]
    assert set(request) == {
        "model",
        "system_instruction",
        "input",
        "response_format",
        "store",
        "timeout",
    }
    for vendor_field in ("max_tokens", "reasoning", "provider"):
        assert vendor_field not in request


@pytest.mark.parametrize("output_text", ["", "not json", '{"unexpected": 1}'])
def test_unusable_output_raises_invalid_response_error(output_text: str) -> None:
    with pytest.raises(AIInvalidResponseError):
        _generate(_provider(FakeInteractions(output_text=output_text)))


def test_rate_limit_raises_rate_limit_error() -> None:
    with pytest.raises(AIRateLimitError):
        _generate(_provider(FakeInteractions(error=FakeStatusError(429))))


def test_network_failure_raises_provider_error_with_cause() -> None:
    with pytest.raises(AIProviderError) as caught:
        _generate(_provider(FakeInteractions(error=ConnectionError("offline"))))

    assert type(caught.value) is AIProviderError
    assert isinstance(caught.value.__cause__, ConnectionError)


def test_response_schema_is_self_contained_and_uses_supported_keywords() -> None:
    schema = gemini_response_schema(LessonDraft)
    text = json.dumps(schema)

    for unsupported in ('"$ref"', '"$defs"', '"default"', '"const"'):
        assert unsupported not in text
    section = schema["properties"]["sections"]["items"]
    assert "concept_map" in section["properties"]["type"]["enum"]
    assert section["properties"]["steps"]["items"]["properties"]["title"]["type"] == "string"


# ---- SDK retry policy (no network) -------------------------------------------------------------


def test_client_is_built_with_sdk_retries_disabled(settings: Settings) -> None:
    provider = GeminiProvider.from_settings(_with_key(settings))

    # Reaching into the SDK client is deliberate: this asserts the supported knob is actually
    # wired, and the test below proves the resulting behaviour.
    options = provider._client._api_client._http_options
    assert options.retry_options is not None
    assert options.retry_options.http_status_codes == RETRYABLE_STATUS_CODES
    assert 429 not in (options.retry_options.http_status_codes or [])


@pytest.mark.parametrize(
    ("status", "status_text", "expected"),
    [
        (429, "RESOURCE_EXHAUSTED", AIRateLimitError),
        (503, "UNAVAILABLE", AIProviderError),
    ],
)
def test_retryable_status_is_not_retried_inside_the_sdk(
    settings: Settings, status: int, status_text: str, expected: type[AIProviderError]
) -> None:
    """Every status the SDK would retry must reach us after one request.

    Left alone the SDK spends four attempts on 429 and on 5xx before raising. A 5xx is covered
    next to the 429 because `RETRYABLE_STATUS_CODES` is the single knob holding both back: if it
    ever stopped applying, the quota case would keep failing fast while outages quietly went back
    to waiting out four attempts before the router could fail over.
    """
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            status, json={"error": {"code": status, "status": status_text, "message": "nope"}}
        )

    provider = GeminiProvider.from_settings(
        _with_key(settings), transport=httpx.MockTransport(handler)
    )

    with pytest.raises(expected) as caught:
        _generate(provider)

    # Exact type: `AIRateLimitError` is an `AIProviderError`, so the 5xx case would pass either way.
    assert type(caught.value) is expected
    assert len(requests) == 1, f"the SDK retried a {status} instead of handing it straight back"


def test_gemini_timeout_is_a_retryable_provider_error(settings: Settings) -> None:
    """A hung Gemini request must be classified the same way a rate limit or outage is, so the

    router fails over on it instead of propagating it unhandled. The mocked transport raises
    `httpx.ReadTimeout` directly (what a real `timeout=REQUEST_TIMEOUT_SECONDS` deadline raises)
    so the test stays instantaneous rather than waiting out a real timeout.
    """
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        raise httpx.ReadTimeout("timed out", request=request)

    provider = GeminiProvider.from_settings(
        _with_key(settings), transport=httpx.MockTransport(handler)
    )

    with pytest.raises(AIProviderError) as caught:
        _generate(provider)

    assert not isinstance(caught.value, AIRateLimitError)
    assert len(requests) == 1


# ---- Hard wall-clock deadline (no network) -----------------------------------------------------


def test_gemini_deadline_matches_the_documented_value() -> None:
    assert gemini_provider.REQUEST_TIMEOUT_SECONDS == 25.0


def test_gemini_request_that_never_answers_is_cut_off_at_the_hard_deadline(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The SDK is left untouched; it is simply run under an application-level deadline.

    `MockTransport` ignores httpx's timeouts, so nothing below the application can end this
    request - if it stops at all, the deadline stopped it. The deadline is shortened here so the
    test stays fast; `test_gemini_deadline_matches_the_documented_value` locks the real value.
    """
    monkeypatch.setattr(gemini_provider, "REQUEST_TIMEOUT_SECONDS", 0.25)

    async def hang_forever(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(3600)
        raise AssertionError("unreachable: the deadline should have fired")

    provider = GeminiProvider.from_settings(
        _with_key(settings), transport=httpx.MockTransport(hang_forever)
    )

    started = time.perf_counter()
    with pytest.raises(AIProviderError) as caught:
        _generate(provider)
    elapsed = time.perf_counter() - started

    assert not isinstance(caught.value, AIRateLimitError)
    assert "deadline" in str(caught.value)
    assert elapsed < 1.0, "the Gemini SDK outlived its application-level deadline"


def test_gemini_timeout_leaves_no_pending_tasks(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(gemini_provider, "REQUEST_TIMEOUT_SECONDS", 0.25)

    async def hang_forever(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(3600)
        raise AssertionError("unreachable")

    async def run() -> int:
        provider = GeminiProvider.from_settings(
            _with_key(settings), transport=httpx.MockTransport(hang_forever)
        )
        with pytest.raises(AIProviderError):
            await provider.generate_structured(
                instructions="-", input_text="-", output_model=Answer
            )
        return len(asyncio.all_tasks()) - 1

    assert asyncio.run(run()) == 0


# ---- Malformed model output is rejected, never accepted ----------------------------------------

VALID_DRAFT: dict[str, Any] = {
    "title": "Photosynthesis",
    "overview": "How plants make glucose.",
    "sections": [
        {
            "type": "concept",
            "title": "Photosynthesis",
            "term": "Photosynthesis",
            "definition": "How plants make glucose from light.",
        }
    ],
    "quiz": [],
}


def _draft_from(output_text: str) -> LessonDraft:
    provider = _provider(FakeInteractions(output_text=output_text))
    return asyncio.run(
        provider.generate_structured(instructions="-", input_text="-", output_model=LessonDraft)
    )


def test_valid_lesson_draft_json_is_accepted() -> None:
    draft = _draft_from(json.dumps(VALID_DRAFT))

    assert draft.sections[0].type == "concept"


@pytest.mark.parametrize(
    "output_text",
    [
        json.dumps(VALID_DRAFT)[:-25],
        json.dumps({**VALID_DRAFT, "sections": [{**VALID_DRAFT["sections"][0], "type": "poster"}]}),
        json.dumps({key: value for key, value in VALID_DRAFT.items() if key != "title"}),
        json.dumps(
            {**VALID_DRAFT, "quiz": [{"prompt": "Q?", "options": ["A", "B"], "explanation": "E"}]}
        ),
    ],
    ids=["truncated-json", "invalid-section-type", "missing-title", "quiz-without-answer"],
)
def test_malformed_lesson_draft_is_rejected(output_text: str) -> None:
    with pytest.raises(AIInvalidResponseError):
        _draft_from(output_text)
