"""Application settings, read from environment variables and the repository-root `.env` file.

Environment variables take precedence over `.env`. See `.env.example` for every supported variable.
Every setting has a safe default, so the API starts with no configuration at all.
"""

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

API_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = API_ROOT.parents[1]
CONTRACTS_DIR = REPO_ROOT / "packages" / "contracts"

AIProviderName = Literal["gemini", "openrouter", "groq", "mock"]

# Stable model with free-tier access, checked against ai.google.dev/gemini-api/docs/models and
# /pricing in September 2026. Override with GEMINI_MODEL when Google retires or renames it.
DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"

# Free OpenRouter model that supports structured outputs, from openrouter.ai/api/v1/models
# (September 2026). Free ids end in ":free" and need no payment method.
DEFAULT_OPENROUTER_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"

# Groq model documented as supporting strict JSON-schema output (console.groq.com/docs/
# structured-outputs, September 2026).
DEFAULT_GROQ_MODEL = "openai/gpt-oss-20b"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    cors_allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )
    ai_provider: AIProviderName = "gemini"
    gemini_api_key: SecretStr | None = None
    gemini_model: str = DEFAULT_GEMINI_MODEL
    data_dir: Path = API_ROOT / ".data"

    # Providers tried, in order, when the primary one is rate-limited or unavailable.
    ai_fallback_providers: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["openrouter", "groq"]
    )
    ai_cache_enabled: bool = True
    ai_fallback_to_demo: bool = True

    openrouter_api_key: SecretStr | None = None
    openrouter_model: str = DEFAULT_OPENROUTER_MODEL
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_app_url: str | None = None
    openrouter_app_title: str | None = None

    groq_api_key: SecretStr | None = None
    groq_model: str = DEFAULT_GROQ_MODEL
    groq_base_url: str = "https://api.groq.com/openai/v1"

    # PDF processing limits. They bound memory, processing time and free-tier AI requests.
    max_upload_mb: int = Field(default=15, ge=1, le=100)
    pdf_max_pages: int = Field(default=40, ge=1, le=500)
    chunk_max_chars: int = Field(default=12_000, ge=1_000)
    ai_single_pass_max_chars: int = Field(default=30_000, ge=0)
    ai_max_chunks: int = Field(default=8, ge=1)

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalise_log_level(cls, value: object) -> object:
        return value.upper() if isinstance(value, str) else value

    @field_validator("ai_fallback_providers", "cors_allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def _require_explicit_cors_in_production(self) -> Self:
        if self.is_production and "*" in self.cors_allowed_origins:
            raise ValueError("CORS_ALLOWED_ORIGINS must list explicit origins in production")
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
