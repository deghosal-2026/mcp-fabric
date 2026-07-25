"""Append-only audit event log backed by the AuditEvent model.

Provides log_event for recording actions with actor/target metadata,
query for retrieving events with optional filters, and cleanup for
removing events older than the configured retention period.

Architectural notes:
  - This is an APPEND-ONLY log. No UPDATE or DELETE of individual events
    is supported through the service API. Only bulk cleanup (by age) is
    allowed.
  - All audit events include actor_type/actor_id and target_type/target_id
    for structured querying — this supports the "who did what to what" pattern.
  - The details field is a JSON blob for extensible payload without schema
    migration. Schema validation happens at the caller level.
  - AuditService is a dependency of many other services. It must not import
    them to avoid circular imports.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.models.audit import AuditEvent


class AuditService:
    """Append-only audit event log backed by the AuditEvent model.

    Depends on: AsyncSession for DB access.
    Used by: alert_service, approval_service, auth_service, routing_service,
    registry_service, and any other service that needs to record actions.

    IMPORTANT: Audit failures are always non-fatal to the calling operation.
    See callers like approval_service.approve() and registry_service.register()
    that wrap audit calls in try/except. This is a deliberate architectural
    choice — the system should still function if the audit log is unavailable.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_event(
        self,
        event_type: str,
        actor_type: str,
        actor_id: str,
        target_type: str | None = None,
        target_id: str | None = None,
        details: dict | None = None,
    ) -> AuditEvent:
        """Record an audit event with actor and target metadata.

        WHY: Every meaningful state change in the system is recorded here —
        server registration, schema changes, approval decisions, access denials,
        capability requests, etc.

        The actor_type/actor_id pair identifies WHO did it (agent, admin, system).
        The target_type/target_id pair identifies WHAT was affected (server,
        approval, capability, etc.).

        SIDE EFFECTS: Commits a new AuditEvent row to the database.
        RETURN: The created AuditEvent ORM object with server-generated id/created_at.
        """
        event = AuditEvent(
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
            target_type=target_type,
            target_id=target_id,
            details=details or {},
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        from api.telemetry.logging import logger

        # Structured logging for downstream log aggregation systems.
        logger.info(
            "audit:event_created",
            audit_event_id=str(event.id),
            event_type=event_type,
            actor_id=actor_id,
        )
        return event

    async def query(
        self,
        event_type: str | None = None,
        actor_type: str | None = None,
        actor_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEvent]:
        """Query audit events with optional filters, ordered by newest first.

        WHY: Admin UI and API consumers need to search the audit trail.
        Filters are composable: you can query by event_type + actor_type,
        or event_type alone, etc.

        Note: Does not support filtering by date range or target_type directly.
        Those can be added when the audit query use case requires them.
        For now, callers can filter the details JSON in application code.
        """
        stmt = select(AuditEvent).order_by(AuditEvent.created_at.desc())
        if event_type:
            stmt = stmt.where(AuditEvent.event_type == event_type)
        if actor_type:
            stmt = stmt.where(AuditEvent.actor_type == actor_type)
        if actor_id:
            stmt = stmt.where(AuditEvent.actor_id == actor_id)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def cleanup(self, before: datetime | None = None) -> int:
        """Delete audit events older than the given datetime.

        WHY: Retention policy — audit events older than the configured
        retention period should be purged to control table growth.

        Uses bulk DELETE (not row-by-row) for efficiency.
        The before parameter defaults to settings.audit_retention_days.

        RETURN: Number of deleted rows.
        SIDE EFFECTS: Bulk DELETE from AuditEvent table.
        """
        if before is None:
            before = datetime.now(UTC) - timedelta(days=settings.audit_retention_days)
        stmt = delete(AuditEvent).where(AuditEvent.created_at < before)
        result = await self.db.execute(stmt)
        await self.db.commit()
        # SQLAlchemy's CursorResult.rowcount is Optional[int]; the
        # # type: ignore is safe because we know a DELETE always returns rowcount.
        return result.rowcount  # type: ignore[return-value]
