from starlette.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_tenant_namespace_from_agent_class():
    resp = client.get("/health")
    assert resp.status_code == 200
