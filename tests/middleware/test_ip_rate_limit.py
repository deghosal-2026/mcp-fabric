from fastapi import FastAPI
from starlette.testclient import TestClient

from api.config import settings
from api.middleware.ip_rate_limit import IPRateLimitMiddleware

app = FastAPI()
app.add_middleware(IPRateLimitMiddleware, max_requests=2, window=60.0)


@app.get("/v1/servers")
async def servers():
    return {"ok": True}


@app.get("/health")
async def health():
    return {"ok": True}


client = TestClient(app)


def test_health_skips_ip_rate_limit():
    resp = client.get("/health")
    assert resp.status_code == 200


def test_ip_rate_limit_exceeded():
    assert client.get("/v1/servers").status_code == 200
    assert client.get("/v1/servers").status_code == 200
    resp = client.get("/v1/servers")
    assert resp.status_code == 429
    body = resp.json()
    assert body["error"] == "rate_limit_exceeded"


def test_different_ips_separate_buckets():
    assert client.get("/v1/servers", headers={"X-Forwarded-For": "1.2.3.4"}).status_code == 200
    assert client.get("/v1/servers", headers={"X-Forwarded-For": "5.6.7.8"}).status_code == 200
    assert client.get("/v1/servers", headers={"X-Forwarded-For": "1.2.3.4"}).status_code == 200
    resp = client.get("/v1/servers", headers={"X-Forwarded-For": "1.2.3.4"})
    assert resp.status_code == 429
    resp2 = client.get("/v1/servers", headers={"X-Forwarded-For": "5.6.7.8"})
    assert resp2.status_code == 200


def test_testing_environment_skips_ip_rate_limit(monkeypatch):
    test_app = FastAPI()
    test_app.add_middleware(IPRateLimitMiddleware, max_requests=1, window=60.0)

    @test_app.get("/v1/approvals")
    async def approvals():
        return {"ok": True}

    monkeypatch.setattr(settings, "environment", "testing")
    test_client = TestClient(test_app)

    assert test_client.get("/v1/approvals").status_code == 200
    assert test_client.get("/v1/approvals").status_code == 200
