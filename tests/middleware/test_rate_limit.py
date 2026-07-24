from fastapi import FastAPI
from starlette.testclient import TestClient

from api.middleware.rate_limit import RateLimitMiddleware

app = FastAPI()
app.add_middleware(RateLimitMiddleware, max_requests=2, window=60.0)


@app.get("/v1/servers")
async def servers():
    return {"ok": True}


@app.get("/health")
async def health():
    return {"ok": True}


client = TestClient(app)


def test_health_skips_rate_limit():
    resp = client.get("/health")
    assert resp.status_code == 200


def test_rate_limit_exceeded():
    assert client.get("/v1/servers").status_code == 200
    assert client.get("/v1/servers").status_code == 200
    resp = client.get("/v1/servers")
    assert resp.status_code == 429
    body = resp.json()
    assert body["error"] == "rate_limit_exceeded"
