from starlette.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health_skips_rate_limit():
    resp = client.get("/health")
    assert resp.status_code == 200


def test_rate_limit_exceeded():
    from api.middleware.rate_limit import _rates
    _rates.clear()
    from api.config import settings
    for _ in range(settings.default_rate_limit):
        client.get("/v1/servers", headers={"Authorization": "Bearer test-token"})
    resp = client.get("/v1/servers", headers={"Authorization": "Bearer test-token"})
    assert resp.status_code == 429
    body = resp.json()
    assert body["error"] == "rate_limit_exceeded"
