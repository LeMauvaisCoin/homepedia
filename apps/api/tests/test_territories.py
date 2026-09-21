import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def test_lists_the_example_communes_with_their_string_codes(database_client: TestClient) -> None:
    response = database_client.get("/v1/territories", params={"limit": 100})

    page = response.json()
    assert response.status_code == 200
    assert page["total"] == 12
    assert page["items"][0]["name"] == "Annecy"
    assert "01053" in {territory["code"] for territory in page["items"]}


def test_paginates_and_keeps_the_total(database_client: TestClient) -> None:
    response = database_client.get("/v1/territories", params={"limit": 5, "offset": 10})

    page = response.json()
    assert [territory["name"] for territory in page["items"]] == ["Saint-Étienne", "Valence"]
    assert page["total"] == 12


def test_filters_by_name(database_client: TestClient) -> None:
    response = database_client.get("/v1/territories", params={"q": "lyon"})

    assert [territory["code"] for territory in response.json()["items"]] == ["69123"]


def test_treats_wildcards_in_the_name_filter_as_literals(database_client: TestClient) -> None:
    response = database_client.get("/v1/territories", params={"q": "_"})

    assert response.json()["total"] == 0


def test_readiness_reaches_the_database(database_client: TestClient) -> None:
    assert database_client.get("/health/ready").status_code == 200
