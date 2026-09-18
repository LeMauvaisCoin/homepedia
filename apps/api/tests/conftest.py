from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from homepedia_api.db import get_pool
from homepedia_api.main import create_app


@pytest.fixture
def offline_client() -> TestClient:
    """Client sans base : le cycle de vie n'est pas démarré, le pool est remplacé."""
    app = create_app()
    app.dependency_overrides[get_pool] = lambda: None
    return TestClient(app)


@pytest.fixture
def database_client() -> Iterator[TestClient]:
    with TestClient(create_app()) as client:
        yield client
