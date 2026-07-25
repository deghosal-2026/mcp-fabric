"""Approval-gated capability workflow for MCP Fabric.

Handles the lifecycle of approval requests: creation, approval (with
routing), denial, status polling, and expiration of stale requests.

Architectural notes:
  - All datetimes are naive UTC for cross-DB compatibility.
    SQLite has no timezone awareness; PostgreSQL stores tz-aware.
    We store naive UTC and compare with naive UTC everywhere.
  - Import is at module level (not inline) for the _utcnow helper.
  - Approval approval triggers optional routing execution. If routing
    fails, the approval still succeeds but the result is not persisted.
    This is a deliberate "approval succeeds even if routing fails" policy.
  - Audit events are logged for every state transition (requested,
    approved, denied) as an append-only trail.
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


def _utcnow() -> datetime:
    """Return the current UTC datetime with tzinfo stripped for cross-DB compatibility.

    WHY: SQLite stores TIMESTAMP without timezone. If we store a tz-aware
    datetime, comparisons against naive datetimes from the DB will fail.
    Stripping tzinfo ensures uniform naive-UTC handling.
    """
    return datetime.now(UTC).replace(tzinfo=None)


class ApprovalNotFoundError(Exception):
    """Raised when an approval request ID is not found."""


class ApprovalAlreadyResolvedError(Exception):
    """Raised when attempting to act on an already-resolved approval request."""


class ApprovalExpiredError(Exception):
    """Raised when attempting to approve a request that has passed its expiry."""


class ApprovalService:
    """Approval-gated capability workflow — create, approve, deny, expire, and audit.

    Depends on:
      - AsyncSession for DB access
      - RoutingService (optional) for executing capabilities on approval
      - AuditService for recording state transitions

    Used by: admin approval UI, agent capability pipeline.
    """

    def __init__(self, db: AsyncSession, routing: RoutingService | None = None):
        self.db = db
        # Routing is optional: approvals can function without a routing
        # backend (e.g., for manual-approval-only workflows).
        self._routing = routing

    async def create_request(self, params: ApprovalRequestCreate) -> ApprovalRequestResponse:
        """Create a new approval request with an expiry timestamp.

        WHY: Agent user journey — an agent requests a capability that requires
        approval. The request is created as 'pending' with a configurable TTL.

        SIDE EFFECTS:
          - Persists ApprovalRequest row
          - Logs an 'approval_requested' audit event
        RETURN: The created request with server-generated id and timestamps.
        """
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

        # Audit logging is fire-and-forget from the caller's perspective:
        # the approval request has already been committed. An audit failure
        # does not roll back the request creation.
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
        """Approve a pending request, execute routing if available, and log the audit event.

        WHY: Admin user journey — an admin approves a pending capability request.

        The approval has three stages:
          1. Validate: request exists, is pending, and has not expired.
          2. Approve: set status, approver metadata, resolution timestamp.
          3. Route: if a routing service is configured, execute the capability
             and persist the result. Routing failure is non-fatal — the approval
             still stands.

        SIDE EFFECTS:
          - Sets req.status to 'approved'
          - If routing succeeds, stores the route result in req.result
          - Logs an 'approval_approved' audit event

        RAISES:
          - ApprovalNotFoundError if request_id is missing
          - ApprovalAlreadyResolvedError if already approved/denied/expired
          - ApprovalExpiredError if the pending window has passed
        """
        # joinedload(capability) avoids an N+1 query when reading req.capability.name
        # for the routing call below.
        result = await self.db.execute(
            select(ApprovalRequest)
            .options(joinedload(ApprovalRequest.capability))
            .where(ApprovalRequest.id == request_id)
        )
        # unique() is required because joinedload on to-one relationships
        # can produce duplicate rows in the SQL result set.
        req = result.unique().scalar_one_or_none()
        if req is None:
            raise ApprovalNotFoundError(f"Approval request {request_id} not found")
        if req.status != "pending":
            raise ApprovalAlreadyResolvedError(
                f"Approval request {request_id} is already {req.status}"
            )
        # Compare with _utcnow() (naive) against expires_at (also naive, stored that way).
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
                # Routing failure is non-fatal. The approval is already committed,
                # and we log the error but do NOT roll back. This matches the
                # "approve first, route best-effort" pattern.
                logger.exception("approval:route_failed", approval_id=str(req.id))

        if route_result:
            # model_dump(mode="json") ensures all types are JSON-serializable
            # (e.g., UUIDs become strings, datetimes become ISO strings).
            req.result = route_result.model_dump(mode="json")
            await self.db.commit()

        await self._log_audit(req, "approval_approved", action)
        return self._to_response(req)

    async def deny(self, request_id: UUID, action: ApprovalAction) -> ApprovalRequestResponse:
        """Deny a pending approval request and log the audit event.

        WHY: Admin user journey — an admin rejects a pending capability request.
        Simpler than approve: no routing execution, just status update + audit.

        RAISES: ApprovalNotFoundError, ApprovalAlreadyResolvedError.
        SIDE EFFECTS: Sets status to 'denied', logs 'approval_denied'.
        """
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
        """Return the current status and result of an approval request.

        WHY: Agent user journey — the requesting agent polls for resolution.
        Used in the agent capability pipeline to check if a requested
        capability has been approved/denied/expired.

        RETURN: Lightweight status response (no full request metadata).
        RAISES: ApprovalNotFoundError if missing.
        """
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
        """Mark all expired pending requests as expired and return the count affected.

        WHY: Background job — periodic cleanup of stale pending requests.
        Uses a bulk UPDATE to avoid loading individual rows into memory.
        The resolved_at is set to the current time so expired requests
        have a clear timestamp.

        SIDE EFFECTS: Bulk UPDATE on ApprovalRequest table.
        RETURN: Number of rows updated.
        """
        now = _utcnow()
        stmt = (
            update(ApprovalRequest)
            .where(
                ApprovalRequest.status == "pending",
                ApprovalRequest.expires_at < now,
            )
            .values(status="expired", resolved_at=now)
        )
        # cast is needed because SQLAlchemy CursorResult typing varies by driver.
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
        """List approval requests with optional status filter, newest first.

        WHY: Admin user journey — browse all approval requests.
        Default ordering by requested_at desc puts recent requests first.
        """
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
        """Record an audit event for an approval action (approved/denied).

        WHY: Audit trail requirement — every approval state transition
        must be recorded for compliance and retrospective analysis.

        The import is inside the method rather than at module top-level
        to avoid circular import issues with audit_service.py.
        """
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
