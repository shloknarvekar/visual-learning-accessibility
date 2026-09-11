import pytest
from pydantic import ValidationError

from app.core.config import DEFAULT_GEMINI_MODEL, Settings


def test_cors_origins_parse_from_comma_separated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://a.test, http://b.test")

    assert Settings(_env_file=None).cors_allowed_origins == ["http://a.test", "http://b.test"]


def test_wildcard_cors_is_rejected_in_production() -> None:
    with pytest.raises(ValidationError, match="explicit origins"):
        Settings(_env_file=None, app_env="production", cors_allowed_origins="*")


def test_empty_gemini_key_is_treated_as_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "")

    assert Settings(_env_file=None).gemini_api_key is None


def test_empty_gemini_model_uses_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_MODEL", "")

    assert Settings(_env_file=None).gemini_model == DEFAULT_GEMINI_MODEL
