from starlette.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_default_version_is_one():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("Fabric-API-Version") == "1"


def test_accept_header_version():
    resp = client.get("/health", headers={"Accept": "application/json; version=1"})
    assert resp.status_code == 200
    assert resp.headers.get("Fabric-API-Version") == "1"


def test_unsupported_version_returns_406():
    resp = client.get("/health", headers={"Accept": "application/json; version=2"})
    assert resp.status_code == 406
    body = resp.json()
    assert body["error"] == "unsupported_api_version"
    assert "version '2'" in body["message"]
    assert "1" in body["supported_versions"]


def test_accept_version_header():
    resp = client.get("/health", headers={"Accept-Version": "1"})
    assert resp.status_code == 200
    assert resp.headers.get("Fabric-API-Version") == "1"


def test_query_param_api_version():
    resp = client.get("/health?api_version=1")
    assert resp.status_code == 200
    assert resp.headers.get("Fabric-API-Version") == "1"
