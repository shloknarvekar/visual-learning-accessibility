"""Optional connectivity check against the real Gemini API.

Excluded from the default test run. Opt in with `pytest -m live`; skipped when GEMINI_API_KEY is
not set. Uses one request of free-tier quota.
"""

import asyncio

import pytest
from pydantic import BaseModel

from app.ai.gemini_provider import GeminiProvider
from app.core.config import Settings

pytestmark = pytest.mark.live


class ConnectivityReply(BaseModel):
    reply: str


def test_gemini_returns_structured_output() -> None:
    settings = Settings()
    if settings.gemini_api_key is None:
        pytest.skip("GEMINI_API_KEY is not set")

    provider = GeminiProvider.from_settings(settings)
    result = asyncio.run(
        provider.generate_structured(
            instructions="Return a JSON object whose `reply` field is the word: ready",
            input_text="Connectivity check.",
            output_model=ConnectivityReply,
        )
    )

    assert result.reply
