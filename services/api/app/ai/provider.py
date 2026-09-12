"""Vendor-neutral interface for schema-constrained model calls.

Pipeline stages depend on `AIProvider`, not on a vendor SDK, so each stage can be unit-tested with a
fake provider and the model vendor can change without touching stage code.

Providers differ in what they can *read*, not only in how well they answer. Every provider declares
that as `modalities`, so a video request is never sent to a text-only service and then explained
away as a model failure: the mismatch is visible before the call and is enforced by `require`.
"""

from typing import Literal, Protocol, TypeVar

from pydantic import BaseModel

from app.models.media import VideoSource

ModelT = TypeVar("ModelT", bound=BaseModel)

# What a provider can take as input.
#   text   prompt text, the only thing an OpenAI-compatible chat endpoint accepts here
#   video  a video the provider fetches itself from a URI, by watching it rather than reading text
Modality = Literal["text", "video"]

TEXT_ONLY: frozenset[Modality] = frozenset({"text"})
TEXT_AND_VIDEO: frozenset[Modality] = frozenset({"text", "video"})


class AIProviderError(Exception):
    """A model call failed, for example because the service could not be reached."""


class AIConfigurationError(AIProviderError):
    """AI features were used without the required configuration."""


class AIRateLimitError(AIProviderError):
    """The provider refused the request because a rate limit or quota was reached."""


class AIInvalidResponseError(AIProviderError):
    """The model answered, but its output did not match the requested schema."""


class AIInputNotSupportedError(AIProviderError):
    """This input type cannot be sent to this provider at all.

    Deliberately not something another attempt can fix in the way the errors above are: a text-only
    provider will not start accepting video on a second try. The router treats it as a hard stop so
    the caller gets a capability error instead of a misleading outage.
    """


class AIProvider(Protocol):
    name: str  # which service this is: "gemini", "openrouter", "groq"
    model_name: str
    modalities: frozenset[Modality]

    async def generate_structured(
        self, *, instructions: str, input_text: str, output_model: type[ModelT]
    ) -> ModelT:
        """Make one model call whose output is constrained to, and validated as, `output_model`."""
        ...


class VideoCapableProvider(AIProvider, Protocol):
    """An `AIProvider` that can also watch a video it fetches from a URI."""

    async def generate_structured_from_video(
        self, *, instructions: str, video: VideoSource, output_model: type[ModelT]
    ) -> ModelT:
        """One model call over `video`, constrained to and validated as `output_model`."""
        ...


def supports(provider: AIProvider, modality: Modality) -> bool:
    return modality in provider.modalities


def require(provider: AIProvider, modality: Modality) -> None:
    """Raise before a call is built when `provider` cannot read `modality` at all."""
    if not supports(provider, modality):
        raise AIInputNotSupportedError(
            f"{provider.name} cannot take {modality} input "
            f"(it accepts: {', '.join(sorted(provider.modalities))})."
        )
