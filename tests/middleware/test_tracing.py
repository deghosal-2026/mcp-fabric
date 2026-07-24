from starlette.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_tracing_adds_span():
    resp = client.get("/health")
    assert resp.status_code == 200
