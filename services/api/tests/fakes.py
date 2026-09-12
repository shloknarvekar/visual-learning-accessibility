"""Test doubles shared by several test modules."""

from typing import Any

from pydantic import BaseModel


class FakeProvider:
    """An `AIProvider` that returns, or raises, prepared responses in order and records requests."""

    name = "gemini"  # tests override this when they need a specific provider identity
    model_name = "fake-model"

    def __init__(self, responses: list[BaseModel | Exception]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    async def generate_structured(
        self, *, instructions: str, input_text: str, output_model: type[BaseModel]
    ) -> Any:
        self.calls.append(
            {"instructions": instructions, "input_text": input_text, "output_model": output_model}
        )
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        assert isinstance(response, output_model)
        return response
