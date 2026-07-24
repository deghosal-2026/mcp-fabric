from starlette.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health_skips_auth():
    resp = client.get("/health")
    assert resp.status_code == 200


def test_no_token_returns_401():
    resp = client.get("/v1/servers")
    assert resp.status_code == 401
    body = resp.json()
    assert body["error"] == "invalid_token"


def test_invalid_token_returns_401():
    resp = client.get("/v1/servers", headers={"Authorization": "Bearer invalid-token"})
    assert resp.status_code == 401
    body = resp.json()
    assert body["error"] == "invalid_token"
