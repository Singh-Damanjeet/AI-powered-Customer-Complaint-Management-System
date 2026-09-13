import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database.session import get_engine
from app.main import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def configured_test_database(monkeypatch: pytest.MonkeyPatch):
    """Use an isolated SQLite connection for the health query tests."""

    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    get_settings.cache_clear()
    get_engine.cache_clear()
    yield
    get_engine.cache_clear()
    get_settings.cache_clear()


def test_health_endpoint_returns_ok() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database": "connected",
        "version": "1.0.0",
    }


def test_health_endpoint_uses_configured_release_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_VERSION", "1.0.0-rc.1")
    get_settings.cache_clear()

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["version"] == "1.0.0-rc.1"


def test_health_endpoint_allows_configured_frontend_origin() -> None:
    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_health_endpoint_reports_unavailable_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL")
    get_settings.cache_clear()
    get_engine.cache_clear()

    response = client.get("/api/health")

    assert response.status_code == 503
    assert response.json()["detail"] == "Database connection unavailable."
