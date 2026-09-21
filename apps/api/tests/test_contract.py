import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError

from homepedia_api.db import get_connection
from homepedia_api.main import create_app
from homepedia_api.settings import Settings


def test_health_answers_without_database(offline_client: TestClient) -> None:
    response = offline_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_invalid_parameter_returns_a_structured_problem(offline_client: TestClient) -> None:
    response = offline_client.get("/v1/territories", params={"limit": 500})

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["errors"] == [
        {"location": "query.limit", "message": "Input should be less than or equal to 100"}
    ]


def test_unknown_route_returns_a_structured_problem(offline_client: TestClient) -> None:
    response = offline_client.get("/v1/unknown")

    assert response.status_code == 404
    assert response.json()["title"] == "Not Found"


def _app_failing_with(error: Exception) -> FastAPI:
    def fail() -> None:
        raise error

    app = create_app()
    app.dependency_overrides[get_connection] = fail
    return app


def test_unexpected_error_returns_a_structured_problem() -> None:
    app = _app_failing_with(RuntimeError("s3cret"))
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"])

    response = TestClient(app).get("/health/ready", headers={"Origin": "http://localhost:5173"})

    assert response.status_code == 500
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["title"] == "Internal error"
    assert "s3cret" not in response.text
    # Without this header, the browser hides the response from the frontend.
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_unreachable_database_returns_503() -> None:
    app = _app_failing_with(OperationalError("SELECT 1", {}, Exception("connection refused")))

    response = TestClient(app).get("/health/ready")

    assert response.status_code == 503
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["title"] == "Service unavailable"
    assert "connection refused" not in response.text


def test_contract_exports_offline_with_stable_operation_ids() -> None:
    schema = create_app().openapi()

    operation_ids = {
        operation["operationId"] for path in schema["paths"].values() for operation in path.values()
    }
    assert operation_ids == {"getHealth", "getReadiness", "listTerritories"}


def test_contract_declares_the_server_problems() -> None:
    paths = create_app().openapi()["paths"]

    for path in ("/health/ready", "/v1/territories"):
        responses = paths[path]["get"]["responses"]
        assert "application/problem+json" in responses["500"]["content"]
        assert "application/problem+json" in responses["503"]["content"]


def test_missing_database_url_fails_at_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError, match="database_url"):
        Settings(_env_file=None)


def test_invalid_database_url_does_not_leak_its_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "mysql://user:s3cret@host/db")

    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None)

    assert "database_url" in str(error.value)
    assert "s3cret" not in str(error.value)


def test_settings_never_display_the_database_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:s3cret@host/db")

    settings = Settings(_env_file=None)

    assert "s3cret" not in repr(settings)
    assert "s3cret" not in str(settings.database_url)
    assert "s3cret" not in settings.model_dump_json()
    assert "s3cret" in str(settings.database_url.get_secret_value())
