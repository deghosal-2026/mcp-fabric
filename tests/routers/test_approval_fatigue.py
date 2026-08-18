"""Router-level tests for approval envelope + bulk-approve endpoints (#442).

Exercises the FastAPI approval router against an in-memory SQLite DB by
overriding the db-session dependency. This covers the HTTP contract (status
codes, JSON shapes) that the service-level tests do not.
"""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db_session
from api.routers import approval as approval_router
from api.services.approval_fatigue_service import ApprovalFatigueService


def _expires_in(hours: int = 24) -> str:
    return (datetime.now(UTC) + timedelta(hours=hours)).isoformat()


def _make_app(db: AsyncSession) -> FastAPI:
    """Build an app that routes /v1/approvals through the real router."""

    async def _override() -> AsyncGenerator[AsyncSession, None]:
        yield db

    app = FastAPI()
    app.dependency_overrides[get_db_session] = _override
    app.include_router(approval_router.router)
    return app


@pytest.fixture
def service(db_session: AsyncSession) -> ApprovalFatigueService:
    return ApprovalFatigueService(db=db_session)


@pytest.mark.anyio
async def test_grant_envelope_creates_envelope(
    db_session: AsyncSession,
) -> None:
    """POST /v1/approvals/envelopes returns a populated envelope."""
    app = _make_app(db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/approvals/envelopes",
            json={
                "scope": "staging",
                "budget": 5,
                "expires_at": "2030-01-01T00:00:00Z",
            },
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["scope"] == "staging"
    assert body["budget"] == 5
    assert body["remaining"] == 5
    assert "expires_at" in body


@pytest.mark.anyio
async def test_grant_envelope_validates_budget(db_session: AsyncSession) -> None:
    """Zero/negative budgets are rejected with 422."""
    app = _make_app(db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/approvals/envelopes",
            json={
                "scope": "staging",
                "budget": 0,
                "expires_at": "2030-01-01T00:00:00Z",
            },
        )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_bulk_approve_marks_anomalies(
    service: ApprovalFatigueService, db_session: AsyncSession
) -> None:
    """POST /v1/approvals/bulk-approve burns budget and returns anomalies."""
    envelope = await service.grant_envelope(
        scope="staging",
        budget=3,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    app = _make_app(db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/approvals/bulk-approve",
            json={
                "envelope_id": str(envelope.id),
                "action_ids": [
                    "11111111-1111-1111-1111-111111111111",
                    "22222222-2222-2222-2222-222222222222",
                    "33333333-3333-3333-3333-333333333333",
                ],
                "anomaly_ids": ["33333333-3333-3333-3333-333333333333"],
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["approved"] == 2
    assert body["anomalies"] == ["33333333-3333-3333-3333-333333333333"]
    assert body["envelope_remaining"] == 2


@pytest.mark.anyio
async def test_bulk_approve_exhausted_envelope_returns_409(
    service: ApprovalFatigueService, db_session: AsyncSession
) -> None:
    """An exhausted envelope escalates to 409 instead of silently approving."""
    envelope = await service.grant_envelope(
        scope="staging",
        budget=1,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    app = _make_app(db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First bulk-approve burns the single unit of budget.
        resp1 = await client.post(
            "/v1/approvals/bulk-approve",
            json={
                "envelope_id": str(envelope.id),
                "action_ids": ["11111111-1111-1111-1111-111111111111"],
            },
        )
        assert resp1.status_code == 200
        assert resp1.json()["envelope_remaining"] == 0

        # Second bulk-approve on the now-exhausted envelope must escalate to 409.
        resp2 = await client.post(
            "/v1/approvals/bulk-approve",
            json={
                "envelope_id": str(envelope.id),
                "action_ids": ["22222222-2222-2222-2222-222222222222"],
            },
        )
    assert resp2.status_code == 409
