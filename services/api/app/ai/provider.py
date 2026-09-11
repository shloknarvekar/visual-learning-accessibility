"""Vendor-neutral interface for schema-constrained model calls.

Pipeline stages depend on `AIProvider`, not on a vendor SDK, so each stage can be unit-tested with a
fake provider and the model vendor can change without touching stage code.
"""

from typing import Protocol, TypeVar

from pydantic import BaseModel

ModelT = TypeVar("ModelT", bound=BaseModel)


class AIProviderError(Exception):
    """A model call failed or produced no usable structured output."""


class AIConfigurationError(AIProviderError):
    """AI features were used without the required configuration."""


class AIProvider(Protocol):
    async def generate_structured(
        self, *, instructions: str, input_text: str, output_model: type[ModelT]
    ) -> ModelT:
        """Make one model call whose output is constrained to, and validated as, `output_model`."""
        ...
