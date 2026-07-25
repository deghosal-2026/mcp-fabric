"""Integration tests for API router endpoints.

These tests exercise the full request lifecycle through FastAPI's
TestClient against a running Fabric instance. They require:
- PostgreSQL or SQLite database at DATABASE_URL
- Redis at REDIS_URL

These are marked 'integration' and 'slow' — run in CI only.
For local testing, start the stack: docker-compose up
"""

import os

import httpx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow]

BASE_URL = os.getenv("FABRIC_TEST_URL", "http://localhost:8000")


def _server_running() -> bool:
    """Check if the Fabric server is reachable before running integration tests."""
    try:
        resp = httpx.get(f"{BASE_URL}/health", timeout=3)
        return resp.status_code < 500
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


@pytest.fixture(scope="module")
def server_available():
    """Skip all tests in the module if the server is unreachable."""
    if not _server_running():
        pytest.skip("Fabric server not running — skipping integration tests")


@pytest.fixture
def client():
    return httpx.Client(base_url=BASE_URL)


@pytest.fixture
def auth_client(client):
    """Obtain an admin token for authenticated requests."""
    resp = client.post(
        "/v1/auth/connect",
        json={"username": "test-agent", "password": "ignored"},
    )
    assert resp.status_code == 200
    token = resp.json()["token"]
    return httpx.Client(base_url=BASE_URL, headers={"Authorization": f"Bearer {token}"})


def test_health_check(server_available, client):
    """Health endpoint should be accessible without auth."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data


def test_health_ready(server_available, client):
    """Readiness probe should respond without auth."""
    resp = client.get("/health/ready")
    assert resp.status_code == 200


def test_health_live(server_available, client):
    """Liveness probe should respond without auth."""
    resp = client.get("/health/live")
    assert resp.status_code == 200


def test_register_and_list_servers(server_available, auth_client):
    """T10-16: Register a server and verify it appears in the list."""
    resp = auth_client.post(
        "/v1/servers",
        json={
            "name": "e2e-test-server",
            "endpoint": "http://e2e-test:3001",
            "owner_team": "platform",
            "labels": ["e2e"],
        },
    )
    data = resp.json()
    if resp.status_code == 400:
        raise AssertionError(f"400 error: {data}")
    assert resp.status_code in (201, 200)
    assert data["name"] == "e2e-test-server"

    resp = auth_client.get("/v1/servers")
    assert resp.status_code == 200
    names = [s["name"] for s in resp.json()["items"]]
    assert "e2e-test-server" in names


def test_capability_lifecycle(server_available, auth_client):
    """T10-17: Create capability, list, verify it exists."""
    resp = auth_client.post(
        "/v1/capabilities",
        json={
            "name": "test:etoe-api",
            "domain": "e2e",
            "description": "E2E test capability",
        },
    )
    data = resp.json()
    if resp.status_code == 422:
        raise AssertionError(f"422 error: {data}")
    assert resp.status_code in (201, 200)

    resp = auth_client.get("/v1/capabilities")
    assert resp.status_code == 200
    names = [c["name"] for c in resp.json()["items"]]
    assert "test:etoe-api" in names


def test_auth_connect_no_token(server_available, client):
    """T10-21: Connecting without a token should mint an agent token."""
    resp = client.post(
        "/v1/auth/connect",
        json={"username": "test-agent", "password": "ignored"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["token"]


def test_audit_endpoint(server_available, auth_client):
    """Audit endpoint should be queryable with auth."""
    resp = auth_client.get("/v1/audit")
    assert resp.status_code in (200, 404)


def test_not_found_returns_404(server_available, auth_client):
    """Unknown routes should return 404 (after auth check passes)."""
    resp = auth_client.get("/v1/nonexistent/route")
    assert resp.status_code == 404


def test_migration_status(server_available, auth_client):
    """T10-23: Migration status stub endpoint."""
    resp = auth_client.get("/v1/admin/migration/status")
    assert resp.status_code in (200, 404)
