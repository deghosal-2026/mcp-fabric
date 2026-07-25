"""Approval-gated capability workflow for MCP Fabric.

Handles the lifecycle of approval requests: creation, approval (with
routing), denial, status polling, and expiration of stale requests.
"""

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from api.config import settings
from api.models.audit import ApprovalRequest
from api.schemas.approval import (
    ApprovalAction,
    ApprovalRequestCreate,
    ApprovalRequestResponse,
    ApprovalStatusResponse,
)
from api.schemas.routing import CapabilityRequest
from api.services.audit_service import AuditService
from api.services.routing_service import RoutingService
from api.telemetry.logging import logger


# All datetimes are naive UTC for cross-DB compatibility
# (SQLite drops tzinfo; PostgreSQL stores it).
# We store naive UTC and compare with naive UTC everywhere.
def _utcnow() -> datetime:
    """Return the current UTC datetime with tzinfo stripped for cross-DB compatibility."""
    return datetime.now(UTC).replace(tzinfo=None)


class ApprovalNotFoundError(Exception):
    """Raised when an approval request ID is not found."""


class ApprovalAlreadyResolvedError(Exception):
    """Raised when attempting to act on an already-resolved approval request."""


class ApprovalExpiredError(Exception):
    """Raised when attempting to approve a request that has passed its expiry."""


class ApprovalService:
    """Approval-gated capability workflow — create, approve, deny, expire, and audit."""

    def __init__(self, db: AsyncSession, routing: RoutingService | None = None):
        self.db = db
        self._routing = routing

    async def create_request(self, params: ApprovalRequestCreate) -> ApprovalRequestResponse:
        """Create a new approval request with an expiry timestamp and log an audit event."""
        expires_at = _utcnow() + timedelta(hours=settings.approval_expiry_hours)
        req = ApprovalRequest(
            agent_identity_id=params.agent_identity_id,
            capability_id=params.capability_id,
            server_id=params.server_id,
            request_params=params.request_params,
            status="pending",
            expires_at=expires_at,
        )
        self.db.add(req)
        await self.db.commit()
        await self.db.refresh(req)

        audit = AuditService(db=self.db)
        await audit.log_event(
            event_type="approval_requested",
            actor_type="agent",
            actor_id=str(params.agent_identity_id),
            target_type="approval",
            target_id=str(req.id),
            details={
                "capability_id": str(params.capability_id),
                "server_id": str(params.server_id),
            },
        )
        return self._to_response(req)

    async def approve(self, request_id: UUID, action: ApprovalAction) -> ApprovalRequestResponse:
        """Approve a pending request, execute routing if available, and log the audit event."""
        result = await self.db.execute(
            select(ApprovalRequest)
            .options(joinedload(ApprovalRequest.capability))
            .where(ApprovalRequest.id == request_id)
        )
        req = result.unique().scalar_one_or_none()
        if req is None:
            raise ApprovalNotFoundError(f"Approval request {request_id} not found")
        if req.status != "pending":
            raise ApprovalAlreadyResolvedError(
                f"Approval request {request_id} is already {req.status}"
            )
        if req.expires_at < _utcnow():
            req.status = "expired"
            await self.db.commit()
            raise ApprovalExpiredError(f"Approval request {request_id} has expired")
        req.status = "approved"
        req.approver_id = action.approver_id
        req.approver_note = action.note
        req.resolved_at = _utcnow()
        await self.db.commit()
        await self.db.refresh(req)

        route_result = None
        if self._routing is not None:
            try:
                capability_name = req.capability.name if req.capability else ""
                route_result = await self._routing.execute(
                    CapabilityRequest(
                        capability=capability_name,
                        params=req.request_params or {},
                    )
                )
            except Exception:
                logger.exception("approval:route_failed", approval_id=str(req.id))

        if route_result:
            req.result = route_result.model_dump(mode="json")
            await self.db.commit()

        await self._log_audit(req, "approval_approved", action)
        return self._to_response(req)

    async def deny(self, request_id: UUID, action: ApprovalAction) -> ApprovalRequestResponse:
        """Deny a pending approval request and log the audit event."""
        result = await self.db.execute(
            select(ApprovalRequest).where(ApprovalRequest.id == request_id)
        )
        req = result.scalar_one_or_none()
        if req is None:
            raise ApprovalNotFoundError(f"Approval request {request_id} not found")
        if req.status != "pending":
            raise ApprovalAlreadyResolvedError(
                f"Approval request {request_id} is already {req.status}"
            )
        req.status = "denied"
        req.approver_id = action.approver_id
        req.approver_note = action.note
        req.resolved_at = _utcnow()
        await self.db.commit()
        await self.db.refresh(req)
        await self._log_audit(req, "approval_denied", action)
        return self._to_response(req)

    async def get_status(self, request_id: UUID) -> ApprovalStatusResponse:
        """Return the current status and result of an approval request."""
        result = await self.db.execute(
            select(ApprovalRequest).where(ApprovalRequest.id == request_id)
        )
        req = result.scalar_one_or_none()
        if req is None:
            raise ApprovalNotFoundError(f"Approval request {request_id} not found")
        return ApprovalStatusResponse(
            id=req.id,
            status=req.status or "pending",
            result=req.result,
            approver_note=req.approver_note,
            resolved_at=req.resolved_at,
        )

    async def expire_pending(self) -> int:
        """Mark all expired pending requests as expired and return the count affected."""
        now = _utcnow()
        stmt = (
            update(ApprovalRequest)
            .where(
                ApprovalRequest.status == "pending",
                ApprovalRequest.expires_at < now,
            )
            .values(status="expired", resolved_at=now)
        )
        result = cast(CursorResult, await self.db.execute(stmt))
        await self.db.commit()

        expired = result.rowcount or 0
        if expired:
            logger.info("approval:expired_batch", count=expired)
        return expired

    async def list_requests(
        self,
        status_filter: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ApprovalRequestResponse]:
        """List approval requests with optional status filter, newest first."""
        stmt = select(ApprovalRequest).order_by(ApprovalRequest.requested_at.desc())
        if status_filter:
            stmt = stmt.where(ApprovalRequest.status == status_filter)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return [self._to_response(r) for r in result.scalars().all()]

    async def _log_audit(
        self,
        req: ApprovalRequest,
        event_type: str,
        action: ApprovalAction,
    ) -> None:
        """Record an audit event for an approval action (approved/denied)."""
        from api.services.audit_service import AuditService

        audit = AuditService(db=self.db)
        await audit.log_event(
            event_type=event_type,
            actor_type="admin",
            actor_id=str(action.approver_id),
            target_type="approval",
            target_id=str(req.id),
            details={
                "agent_identity_id": str(req.agent_identity_id),
                "capability_id": str(req.capability_id),
                "server_id": str(req.server_id),
                "note": action.note,
            },
        )

    def _to_response(self, req: ApprovalRequest) -> ApprovalRequestResponse:
        """Convert an ApprovalRequest ORM object to an ApprovalRequestResponse schema."""
        return ApprovalRequestResponse(
            id=req.id,
            agent_identity_id=req.agent_identity_id,
            capability_id=req.capability_id,
            server_id=req.server_id,
            status=req.status or "pending",
            request_params=req.request_params,
            requested_at=req.requested_at,
            resolved_at=req.resolved_at,
            expires_at=req.expires_at,
            approver_id=req.approver_id,
            approver_note=req.approver_note,
            result=req.result,
        )
