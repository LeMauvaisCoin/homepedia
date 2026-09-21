from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from homepedia_api.db import get_connection
from homepedia_api.main import create_app


@pytest.fixture
def offline_client() -> TestClient:
    """Client without a database: the lifespan is not started, the connection is overridden."""
    app = create_app()
    app.dependency_overrides[get_connection] = lambda: None
    return TestClient(app)


@pytest.fixture
def database_client() -> Iterator[TestClient]:
    with TestClient(create_app()) as client:
        yield client
