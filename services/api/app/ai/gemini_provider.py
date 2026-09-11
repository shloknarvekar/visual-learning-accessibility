"""Google Gemini implementation of `AIProvider`.

The only module that imports the Gemini SDK. Uses the Interactions API with a JSON-schema response
format, as documented at https://ai.google.dev/gemini-api/docs/structured-output (checked against
google-genai 2.23 in September 2026).
"""

from typing import Any, Self

from google import genai
from pydantic import ValidationError

from app.ai.provider import AIConfigurationError, AIProviderError, ModelT
from app.core.config import Settings

REQUEST_TIMEOUT_SECONDS = 120.0
_HTTP_TOO_MANY_REQUESTS = 429


class GeminiProvider:
    def __init__(self, *, client: genai.Client, model: str) -> None:
        self._client = client
        self._model = model

    @classmethod
    def from_settings(cls, settings: Settings) -> Self:
        if settings.gemini_api_key is None:
            raise AIConfigurationError("Set GEMINI_API_KEY to use the Gemini provider.")
        client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())
        return cls(client=client, model=settings.gemini_model)

    async def generate_structured(
        self, *, instructions: str, input_text: str, output_model: type[ModelT]
    ) -> ModelT:
        try:
            interaction = await self._client.aio.interactions.create(
                model=self._model,
                system_instruction=instructions,
                input=input_text,
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": output_model.model_json_schema(),
                },
                store=False,  # don't keep course material stored for later retrieval
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            # The SDK's error classes live in private modules that move between releases, so this
            # boundary converts every failure. The original exception stays attached as __cause__.
            raise AIProviderError(_describe_failure(exc)) from exc

        text = interaction.output_text
        if not text:
            raise AIProviderError("Gemini returned no output.")
        try:
            return output_model.model_validate_json(text)
        except ValidationError as exc:
            raise AIProviderError("Gemini output did not match the requested schema.") from exc


def _describe_failure(exc: Exception) -> str:
    status_code: Any = getattr(exc, "status_code", None)
    if status_code == _HTTP_TOO_MANY_REQUESTS:
        return "Gemini rate limit reached (free-tier quota). Retry later or set AI_PROVIDER=mock."
    if status_code is not None:
        return f"Gemini request failed with HTTP {status_code}."
    return f"Gemini request failed: {type(exc).__name__}."
