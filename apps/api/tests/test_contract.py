import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

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


def test_contract_exports_offline_with_stable_operation_ids() -> None:
    schema = create_app().openapi()

    operation_ids = {
        operation["operationId"] for path in schema["paths"].values() for operation in path.values()
    }
    assert operation_ids == {"getHealth", "getReadiness", "listTerritories"}


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
