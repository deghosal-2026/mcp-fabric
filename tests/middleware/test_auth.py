from fastapi import FastAPI
from starlette.requests import Request
from starlette.testclient import TestClient

from api.main import app
from api.middleware.auth import AuthMiddleware
from api.services.auth_service import AuthService

client = TestClient(app)

auth_service = AuthService(secret_key="test-secret")


def _make_auth_app():
    _app = FastAPI()
    _app.add_middleware(AuthMiddleware, auth_service=auth_service)

    @_app.get("/v1/servers")
    async def _servers():
        return {"ok": True}

    @_app.get("/state")
    async def _state(request: Request):
        return {
            "agent_id": request.state.agent_id,
            "agent_type": request.state.agent_type,
            "agent_class": request.state.agent_class,
            "role": request.state.role,
        }

    return TestClient(_app)


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


def test_valid_token_passes():
    app = _make_auth_app()
    token = auth_service.create_token(subject="agent-1", agent_class="agent:developer")
    resp = app.get("/v1/servers", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_valid_token_sets_state():
    app = _make_auth_app()
    token = auth_service.create_token(
        subject="agent-1", agent_class="agent:developer", role="admin"
    )
    resp = app.get("/state", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["agent_id"] == "agent-1"
    assert body["agent_class"] == "agent:developer"
    assert body["role"] == "admin"


def test_valid_token_has_www_authenticate():
    resp = client.get("/v1/servers")
    assert "WWW-Authenticate" in resp.headers
    assert "Bearer" in resp.headers["WWW-Authenticate"]
