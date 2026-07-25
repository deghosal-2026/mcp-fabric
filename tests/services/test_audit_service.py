from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from api.services.audit_service import AuditService


class TestAuditService:
    async def test_log_event(self, db_session: AsyncSession):
        svc = AuditService(db=db_session)
        event = await svc.log_event(
            event_type="test_event",
            actor_type="agent",
            actor_id="agent-1",
            target_type="server",
            target_id="srv-1",
            details={"key": "value"},
        )
        assert event.event_type == "test_event"
        assert event.actor_id == "agent-1"
        assert event.details == {"key": "value"}

    async def test_query(self, db_session: AsyncSession):
        svc = AuditService(db=db_session)
        await svc.log_event(event_type="type_a", actor_type="agent", actor_id="a1")
        await svc.log_event(event_type="type_b", actor_type="agent", actor_id="a2")
        results = await svc.query(event_type="type_a")
        assert len(results) == 1
        assert results[0].event_type == "type_a"

    async def test_cleanup(self, db_session: AsyncSession):
        svc = AuditService(db=db_session)
        event = await svc.log_event(event_type="old", actor_type="agent", actor_id="a1")
        event.created_at = datetime.now(UTC) - timedelta(days=999)
        await db_session.commit()
        deleted = await svc.cleanup(before=datetime.now(UTC))
        assert deleted >= 1
