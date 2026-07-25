"""Integration tests for API router endpoints.

These tests exercise the full request lifecycle through FastAPI's
TestClient against a running Fabric instance. They require:
- PostgreSQL or SQLite database at DATABASE_URL
- Redis at REDIS_URL

These are marked 'integration' and 'slow' — run in CI only.
For local testing, start the stack: docker-compose up
"""

import os

import pytest
import httpx

pytestmark = [pytest.mark.integration, pytest.mark.slow]

BASE_URL = os.getenv("FABRIC_TEST_URL", "http://localhost:8000")


@pytest.fixture
def client():
    return httpx.Client(base_url=BASE_URL)


def test_health_check(client):
    """Health endpoint should be accessible."""
    resp = client.get("/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data


def test_health_ready(client):
    """Readiness probe should respond."""
    resp = client.get("/v1/health/ready")
    assert resp.status_code == 200


def test_health_live(client):
    """Liveness probe should respond."""
    resp = client.get("/v1/health/live")
    assert resp.status_code == 200


def test_register_and_list_servers(client):
    """T10-16: Register a server and verify it appears in the list."""
    resp = client.post("/v1/servers", json={
        "name": "e2e-test-server",
        "endpoint": "http://e2e-test:3001",
        "owner_team": "platform",
        "labels": ["e2e"],
    })
    assert resp.status_code in (201, 200)
    data = resp.json()
    assert data["name"] == "e2e-test-server"

    resp = client.get("/v1/servers")
    assert resp.status_code == 200
    names = [s["name"] for s in resp.json()["items"]]
    assert "e2e-test-server" in names


def test_capability_lifecycle(client):
    """T10-17: Create capability, list, verify it exists."""
    resp = client.post("/v1/capabilities", json={
        "name": "e2e:test-capability",
        "domain": "e2e",
        "description": "E2E test capability",
    })
    assert resp.status_code in (201, 200)

    resp = client.get("/v1/capabilities")
    assert resp.status_code == 200
    names = [c["name"] for c in resp.json()["items"]]
    assert "e2e:test-capability" in names


def test_auth_connect_no_token(client):
    """T10-21: Connecting without a token should return 401."""
    resp = client.post("/v1/auth/connect")
    assert resp.status_code == 401


def test_audit_endpoint(client):
    """Audit endpoint should be queryable."""
    resp = client.get("/v1/audit")
    assert resp.status_code in (200, 404)


def test_not_found_returns_404(client):
    """Unknown routes should return 404."""
    resp = client.get("/v1/nonexistent/route")
    assert resp.status_code == 404


def test_migration_status(client):
    """T10-23: Migration status stub endpoint."""
    resp = client.get("/v1/admin/migration/status")
    assert resp.status_code in (200, 404)
