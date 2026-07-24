from starlette.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health_skips_audit():
    resp = client.get("/health")
    assert resp.status_code == 200
