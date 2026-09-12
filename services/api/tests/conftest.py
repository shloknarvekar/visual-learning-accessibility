import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import CONTRACTS_DIR, Settings
from app.main import create_app
from app.schemas.lesson import Lesson


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    # _env_file=None keeps a developer's local .env from changing test behaviour.
    return Settings(
        _env_file=None,
        app_env="test",
        cors_allowed_origins=["http://localhost:3000"],
        ai_provider="gemini",
        gemini_api_key=None,
        data_dir=tmp_path / "data",
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings), raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def lesson_schema() -> dict[str, Any]:
    return json.loads((CONTRACTS_DIR / "lesson.schema.json").read_text(encoding="utf-8"))


@pytest.fixture
def example_lesson_data() -> dict[str, Any]:
    path = CONTRACTS_DIR / "examples" / "photosynthesis.lesson.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def example_lesson(example_lesson_data: dict[str, Any]) -> Lesson:
    return Lesson.model_validate(example_lesson_data)
