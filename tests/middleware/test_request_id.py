from uuid import uuid4

import pytest
from starlette.testclient import TestClient

from api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestRequestIDMiddleware:
    def test_response_has_request_id(self, client: TestClient) -> None:
        response = client.get("/health")
        assert "Fabric-Request-Id" in response.headers
        rid = response.headers["Fabric-Request-Id"]
        assert len(rid) == 36
        assert rid.count("-") == 4

    def test_request_id_set_on_state(self, client: TestClient) -> None:
        response = client.get("/health")
        rid = response.headers["Fabric-Request-Id"]
        assert rid is not None

    def test_passthrough_existing_request_id(self, client: TestClient) -> None:
        existing = str(uuid4())
        response = client.get("/health", headers={"Fabric-Request-Id": existing})
        assert response.headers["Fabric-Request-Id"] == existing
