"""Tests for ApprovalService: request lifecycle, approve/deny, status polling, expiration."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.models.audit import ApprovalRequest
from api.schemas.approval import ApprovalAction, ApprovalRequestCreate
from api.schemas.routing import RouteResult
from api.services.approval_service import (
    ApprovalAlreadyResolvedError,
    ApprovalNotFoundError,
    ApprovalService,
)


@pytest.fixture
def approval_svc(db_session: AsyncSession) -> ApprovalService:
    return ApprovalService(db=db_session)


class TestApprovalCreate:
    async def test_create_request(self, db_session: AsyncSession, approval_svc, server, capability):
        req = await _create_request(approval_svc, server, capability)
        assert req.status == "pending"
        assert req.capability_id == capability.id
        assert req.server_id == server.id
        assert req.id is not None

    async def test_create_request_sets_expiry(
        self, db_session: AsyncSession, approval_svc, server, capability
    ):

        req = await _create_request(approval_svc, server, capability)
        expected = datetime.now(UTC).replace(tzinfo=None) + timedelta(
            hours=settings.approval_expiry_hours
        )
        assert abs((req.expires_at - expected).total_seconds()) < 5

    async def test_create_request_stores_params(
        self, db_session: AsyncSession, approval_svc, server, capability
    ):
        identity = await _fake_agent_identity(db_session)
        params = ApprovalRequestCreate(
            agent_identity_id=identity.id,
            capability_id=capability.id,
            server_id=server.id,
            request_params={"query": "test", "max_results": 10},
        )
        req = await approval_svc.create_request(params)
        assert req.request_params == {"query": "test", "max_results": 10}


class TestApprovalApprove:
    async def test_approve_updates_status(
        self, db_session: AsyncSession, approval_svc, server, capability
    ):
        created = await _create_request(approval_svc, server, capability)
        approved = await approval_svc.approve(
            created.id, ApprovalAction(approver_id=uuid4(), note="Looks good")
        )
        assert approved.status == "approved"
        assert approved.resolved_at is not None

    async def test_approve_not_found(self, approval_svc):
        with pytest.raises(ApprovalNotFoundError):
            await approval_svc.approve(uuid4(), ApprovalAction(approver_id=uuid4()))

    async def test_approve_already_resolved(
        self, db_session: AsyncSession, approval_svc, server, capability
    ):
        created = await _create_request(approval_svc, server, capability)
        await approval_svc.approve(created.id, ApprovalAction(approver_id=uuid4()))
        with pytest.raises(ApprovalAlreadyResolvedError):
            await approval_svc.approve(created.id, ApprovalAction(approver_id=uuid4()))


class TestApprovalDeny:
    async def test_deny_updates_status(
        self, db_session: AsyncSession, approval_svc, server, capability
    ):
        created = await _create_request(approval_svc, server, capability)
        denied = await approval_svc.deny(
            created.id, ApprovalAction(approver_id=uuid4(), note="Not authorized")
        )
        assert denied.status == "denied"
        assert denied.approver_note == "Not authorized"

    async def test_deny_not_found(self, approval_svc):
        with pytest.raises(ApprovalNotFoundError):
            await approval_svc.deny(uuid4(), ApprovalAction(approver_id=uuid4()))

    async def test_deny_already_resolved(
        self, db_session: AsyncSession, approval_svc, server, capability
    ):
        created = await _create_request(approval_svc, server, capability)
        await approval_svc.approve(created.id, ApprovalAction(approver_id=uuid4()))
        with pytest.raises(ApprovalAlreadyResolvedError):
            await approval_svc.deny(created.id, ApprovalAction(approver_id=uuid4()))


class TestApprovalStatus:
    async def test_get_status_pending(
        self, db_session: AsyncSession, approval_svc, server, capability
    ):
        created = await _create_request(approval_svc, server, capability)
        status = await approval_svc.get_status(created.id)
        assert status.status == "pending"

    async def test_get_status_approved(
        self, db_session: AsyncSession, approval_svc, server, capability
    ):
        created = await _create_request(approval_svc, server, capability)
        await approval_svc.approve(created.id, ApprovalAction(approver_id=uuid4()))
        status = await approval_svc.get_status(created.id)
        assert status.status == "approved"

    async def test_get_status_denied(
        self, db_session: AsyncSession, approval_svc, server, capability
    ):
        created = await _create_request(approval_svc, server, capability)
        await approval_svc.deny(created.id, ApprovalAction(approver_id=uuid4()))
        status = await approval_svc.get_status(created.id)
        assert status.status == "denied"

    async def test_get_status_not_found(self, approval_svc):
        with pytest.raises(ApprovalNotFoundError):
            await approval_svc.get_status(uuid4())


class TestApprovalExpire:
    async def test_expire_pending_requests(
        self, db_session: AsyncSession, approval_svc, server, capability
    ):
        created = await _create_request(approval_svc, server, capability)
        result = await db_session.execute(
            sqlalchemy.select(ApprovalRequest).where(ApprovalRequest.id == created.id)
        )
        req_row = result.scalar_one()
        req_row.expires_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=1)
        await db_session.commit()
        expired = await approval_svc.expire_pending()
        assert expired >= 1
        status = await approval_svc.get_status(created.id)
        assert status.status == "expired"

    async def test_expire_pending_no_requests(self, approval_svc):
        count = await approval_svc.expire_pending()
        assert count == 0

    async def test_expire_does_not_touch_active(
        self, db_session: AsyncSession, approval_svc, server, capability
    ):
        created = await _create_request(approval_svc, server, capability)
        await approval_svc.approve(created.id, ApprovalAction(approver_id=uuid4()))
        expired = await approval_svc.expire_pending()
        assert expired == 0


class TestApprovalList:
    async def test_list_requests(self, db_session: AsyncSession, approval_svc, server, capability):
        await _create_request(approval_svc, server, capability)
        await _create_request(approval_svc, server, capability)
        all_reqs = await approval_svc.list_requests()
        assert len(all_reqs) == 2

    async def test_list_requests_empty(self, approval_svc):
        result = await approval_svc.list_requests()
        assert result == []

    async def test_list_requests_filter_status(
        self, db_session: AsyncSession, approval_svc, server, capability
    ):
        created = await _create_request(approval_svc, server, capability)
        await approval_svc.approve(created.id, ApprovalAction(approver_id=uuid4()))
        pending = await approval_svc.list_requests(status_filter="pending")
        approved = await approval_svc.list_requests(status_filter="approved")
        assert len(pending) == 0
        assert len(approved) == 1


class TestApprovalWithRouting:
    async def test_approve_with_routing_executes(
        self, db_session: AsyncSession, server, capability
    ):
        routing = AsyncMock()
        routing.execute = AsyncMock(
            return_value=RouteResult(
                result={"output": "done"},
                server="test-server",
                server_id=uuid4(),
                latency_ms=10,
            )
        )
        svc = ApprovalService(db=db_session, routing=routing)
        created = await _create_request(svc, server, capability)
        approved = await svc.approve(created.id, ApprovalAction(approver_id=uuid4()))
        assert approved.status == "approved"
        assert approved.result is not None
        assert approved.result["result"]["output"] == "done"
        routing.execute.assert_awaited_once()

    async def test_approve_routing_stores_result_for_polling(
        self, db_session: AsyncSession, server, capability
    ):
        routing = AsyncMock()
        routing.execute = AsyncMock(
            return_value=RouteResult(
                result={"output": "stored"},
                server="test-server",
                server_id=uuid4(),
                latency_ms=5,
            )
        )
        svc = ApprovalService(db=db_session, routing=routing)
        created = await _create_request(svc, server, capability)
        await svc.approve(created.id, ApprovalAction(approver_id=uuid4()))
        status = await svc.get_status(created.id)
        assert status.result is not None
        assert status.result["result"]["output"] == "stored"

    async def test_approve_routing_failure_does_not_block(
        self, db_session: AsyncSession, server, capability
    ):
        routing = AsyncMock()
        routing.execute = AsyncMock(side_effect=Exception("MCP connection refused"))
        svc = ApprovalService(db=db_session, routing=routing)
        created = await _create_request(svc, server, capability)
        approved = await svc.approve(created.id, ApprovalAction(approver_id=uuid4()))
        assert approved.status == "approved"
        assert approved.result is None


class TestApprovalAuditLogging:
    async def test_create_logs_audit_event(
        self, db_session: AsyncSession, server, capability, approval_svc
    ):
        from api.services.audit_service import AuditService

        created = await _create_request(approval_svc, server, capability)
        audit = AuditService(db=db_session)
        events = await audit.query(event_type="approval_requested")
        assert len(events) == 1
        assert events[0].target_id == str(created.id)
        assert events[0].actor_type == "agent"

    async def test_approve_logs_audit_event(
        self, db_session: AsyncSession, server, capability, approval_svc
    ):
        from api.services.audit_service import AuditService

        created = await _create_request(approval_svc, server, capability)
        admin_id = uuid4()
        await approval_svc.approve(created.id, ApprovalAction(approver_id=admin_id, note="ok"))
        audit = AuditService(db=db_session)
        events = await audit.query(event_type="approval_approved")
        assert len(events) == 1
        assert events[0].actor_id == str(admin_id)
        assert events[0].details["note"] == "ok"

    async def test_deny_logs_audit_event(
        self, db_session: AsyncSession, server, capability, approval_svc
    ):
        from api.services.audit_service import AuditService

        created = await _create_request(approval_svc, server, capability)
        admin_id = uuid4()
        await approval_svc.deny(created.id, ApprovalAction(approver_id=admin_id))
        audit = AuditService(db=db_session)
        events = await audit.query(event_type="approval_denied")
        assert len(events) == 1
        assert events[0].actor_id == str(admin_id)


class TestApprovalResultPersistence:
    async def test_approve_persists_result_in_db(
        self, db_session: AsyncSession, server, capability
    ):
        routing = AsyncMock()
        routing.execute = AsyncMock(
            return_value=RouteResult(
                result={"output": "persisted"},
                server="test-server",
                server_id=uuid4(),
                latency_ms=5,
            )
        )
        svc = ApprovalService(db=db_session, routing=routing)
        created = await _create_request(svc, server, capability)
        await svc.approve(created.id, ApprovalAction(approver_id=uuid4()))
        await db_session.commit()
        row = await db_session.get(ApprovalRequest, created.id)
        assert row is not None
        assert row.result is not None
        assert row.result["result"]["output"] == "persisted"

    async def test_get_status_returns_persisted_result(
        self, db_session: AsyncSession, server, capability
    ):
        routing = AsyncMock()
        routing.execute = AsyncMock(
            return_value=RouteResult(
                result={"output": "status-check"},
                server="test-server",
                server_id=uuid4(),
                latency_ms=5,
            )
        )
        svc = ApprovalService(db=db_session, routing=routing)
        created = await _create_request(svc, server, capability)
        await svc.approve(created.id, ApprovalAction(approver_id=uuid4()))
        status = await svc.get_status(created.id)
        assert status.result is not None
        assert status.result["result"]["output"] == "status-check"


async def _create_request(svc, server, capability, db_session=None):
    identity = await _fake_agent_identity(db_session or svc.db)
    return await svc.create_request(
        ApprovalRequestCreate(
            agent_identity_id=identity.id,
            capability_id=capability.id,
            server_id=server.id,
        )
    )


async def _fake_agent_identity(db_session: AsyncSession):
    import uuid

    from api.models.agent import AgentClass, AgentIdentity

    suffix = uuid.uuid4().hex[:8]
    ac = AgentClass(name=f"agent:test-approver-{suffix}", description="Test")
    db_session.add(ac)
    await db_session.commit()
    await db_session.refresh(ac)
    ident = AgentIdentity(
        name=f"approval-test-{suffix}",
        agent_class_id=ac.id,
        token_hash="fake_hash",
        token_prefix="fcp_",
    )
    db_session.add(ident)
    await db_session.commit()
    await db_session.refresh(ident)
    return ident
