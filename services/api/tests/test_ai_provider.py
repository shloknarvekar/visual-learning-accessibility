import asyncio
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel, SecretStr

from app.ai.factory import create_ai_provider, resolve_ai_mode
from app.ai.gemini_provider import GeminiProvider
from app.ai.provider import AIConfigurationError, AIProviderError
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


# ---- Provider selection ------------------------------------------------------------------------


def test_mock_mode_without_api_key(settings: Settings) -> None:
    assert resolve_ai_mode(settings) == "mock"
    assert create_ai_provider(settings) is None


def test_mock_mode_when_requested_even_with_api_key(settings: Settings) -> None:
    settings = settings.model_copy(
        update={"ai_provider": "mock", "gemini_api_key": SecretStr("test-key")}
    )

    assert resolve_ai_mode(settings) == "mock"
    assert create_ai_provider(settings) is None


def test_gemini_mode_with_api_key(settings: Settings) -> None:
    settings = settings.model_copy(update={"gemini_api_key": SecretStr("test-key")})

    assert resolve_ai_mode(settings) == "gemini"
    assert isinstance(create_ai_provider(settings), GeminiProvider)


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
    assert request["response_format"]["schema"] == Answer.model_json_schema()
    assert request["store"] is False


@pytest.mark.parametrize("output_text", ["", "not json", '{"unexpected": 1}'])
def test_unusable_output_raises_provider_error(output_text: str) -> None:
    with pytest.raises(AIProviderError):
        _generate(_provider(FakeInteractions(output_text=output_text)))


def test_rate_limit_is_reported_clearly() -> None:
    with pytest.raises(AIProviderError, match="rate limit"):
        _generate(_provider(FakeInteractions(error=FakeStatusError(429))))


def test_network_failure_is_wrapped_with_cause() -> None:
    with pytest.raises(AIProviderError, match="ConnectionError") as caught:
        _generate(_provider(FakeInteractions(error=ConnectionError("offline"))))

    assert isinstance(caught.value.__cause__, ConnectionError)
