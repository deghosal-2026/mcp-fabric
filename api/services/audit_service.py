"""Append-only audit event log backed by the AuditEvent model.

Provides log_event for recording actions with actor/target metadata,
query for retrieving events with optional filters, and cleanup for
removing events older than the configured retention period.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.models.audit import AuditEvent


class AuditService:
    """Append-only audit event log backed by the AuditEvent model."""

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
        """Record an audit event with actor and target metadata."""
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
        """Query audit events with optional filters, ordered by newest first."""
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

        Defaults to retention period. Returns count deleted.
        """
        if before is None:
            before = datetime.now(UTC) - timedelta(days=settings.audit_retention_days)
        stmt = delete(AuditEvent).where(AuditEvent.created_at < before)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount  # type: ignore[return-value]
