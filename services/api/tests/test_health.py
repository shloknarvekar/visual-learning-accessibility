import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize("path", ["/health", "/api/v1/health"])
def test_health_reports_ok(client: TestClient, path: str) -> None:
    response = client.get(path)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "api"
    assert response.headers["X-Request-ID"]


def test_health_reports_mock_mode_without_api_key(client: TestClient) -> None:
    assert client.get("/api/v1/health").json()["ai_mode"] == "mock"


def test_cors_allows_configured_origin(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"Origin": "http://localhost:3000"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_ignores_unknown_origin(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"Origin": "https://attacker.example"})

    assert "access-control-allow-origin" not in response.headers
