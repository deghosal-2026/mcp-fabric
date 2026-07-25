"""Tests for AlertService: rule CRUD, fire, acknowledge, threshold evaluation."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.alert import AcknowledgeRequest, AlertRuleCreate
from api.services.alert_service import (
    AlertEventNotFoundError,
    AlertRuleNotFoundError,
    AlertService,
)


@pytest.fixture
def alert_svc(db_session: AsyncSession) -> AlertService:
    return AlertService(db=db_session)


class TestAlertRuleCRUD:
    async def test_create_rule(self, alert_svc):
        rule = await alert_svc.create_rule(
            AlertRuleCreate(
                name="high-degradation",
                alert_type="server_health",
                condition={"metric": "degraded_servers", "threshold": 3},
                channels=["slack"],
            )
        )
        assert rule.name == "high-degradation"
        assert rule.alert_type == "server_health"
        assert rule.enabled is True
        assert rule.id is not None

    async def test_get_rule(self, alert_svc):
        created = await alert_svc.create_rule(AlertRuleCreate(name="test-rule", alert_type="test"))
        fetched = await alert_svc.get_rule(created.id)
        assert fetched.name == "test-rule"

    async def test_get_rule_not_found(self, alert_svc):
        with pytest.raises(AlertRuleNotFoundError):
            await alert_svc.get_rule(uuid4())

    async def test_list_rules(self, alert_svc):
        await alert_svc.create_rule(AlertRuleCreate(name="rule-a", alert_type="type1"))
        await alert_svc.create_rule(AlertRuleCreate(name="rule-b", alert_type="type2"))
        rules = await alert_svc.list_rules()
        assert len(rules) == 2

    async def test_list_rules_empty(self, alert_svc):
        assert await alert_svc.list_rules() == []

    async def test_list_rules_filters_type(self, alert_svc):
        await alert_svc.create_rule(AlertRuleCreate(name="health-rule", alert_type="health"))
        await alert_svc.create_rule(AlertRuleCreate(name="sec-rule", alert_type="security"))
        result = await alert_svc.list_rules(alert_type="health")
        assert len(result) == 1
        assert result[0].name == "health-rule"

    async def test_update_rule(self, alert_svc):
        created = await alert_svc.create_rule(AlertRuleCreate(name="old-name", alert_type="test"))
        updated = await alert_svc.update_rule(
            created.id, AlertRuleCreate(name="new-name", alert_type="test")
        )
        assert updated.name == "new-name"

    async def test_update_rule_not_found(self, alert_svc):
        with pytest.raises(AlertRuleNotFoundError):
            await alert_svc.update_rule(uuid4(), AlertRuleCreate(name="nope", alert_type="test"))

    async def test_delete_rule(self, alert_svc):
        created = await alert_svc.create_rule(AlertRuleCreate(name="to-delete", alert_type="test"))
        await alert_svc.delete_rule(created.id)
        with pytest.raises(AlertRuleNotFoundError):
            await alert_svc.get_rule(created.id)

    async def test_delete_rule_not_found(self, alert_svc):
        with pytest.raises(AlertRuleNotFoundError):
            await alert_svc.delete_rule(uuid4())

    async def test_toggle_rule(self, alert_svc):
        created = await alert_svc.create_rule(AlertRuleCreate(name="toggle-me", alert_type="test"))
        disabled = await alert_svc.toggle_rule(created.id, enabled=False)
        assert disabled.enabled is False
        enabled_again = await alert_svc.toggle_rule(created.id, enabled=True)
        assert enabled_again.enabled is True


class TestAlertFire:
    async def test_fire_alert(self, alert_svc):
        rule = await alert_svc.create_rule(AlertRuleCreate(name="fire-test", alert_type="test"))
        event = await alert_svc.fire_alert(rule.id, "Server is down", {"server": "api-1"})
        assert event.rule_id == rule.id
        assert event.message == "Server is down"
        assert event.details == {"server": "api-1"}
        assert event.acknowledged_at is None

    async def test_fire_alert_rule_not_found(self, alert_svc):
        with pytest.raises(AlertRuleNotFoundError):
            await alert_svc.fire_alert(uuid4(), "test")

    async def test_list_events(self, alert_svc):
        rule = await alert_svc.create_rule(AlertRuleCreate(name="event-list", alert_type="test"))
        await alert_svc.fire_alert(rule.id, "event 1")
        await alert_svc.fire_alert(rule.id, "event 2")
        events = await alert_svc.list_events()
        assert len(events) == 2

    async def test_list_events_empty(self, alert_svc):
        assert await alert_svc.list_events() == []

    async def test_list_events_filter_by_rule(self, alert_svc):
        r1 = await alert_svc.create_rule(AlertRuleCreate(name="r1", alert_type="test"))
        r2 = await alert_svc.create_rule(AlertRuleCreate(name="r2", alert_type="test"))
        await alert_svc.fire_alert(r1.id, "from r1")
        await alert_svc.fire_alert(r2.id, "from r2")
        r1_events = await alert_svc.list_events(rule_id=r1.id)
        assert len(r1_events) == 1
        assert r1_events[0].message == "from r1"


class TestAlertAcknowledge:
    async def test_acknowledge_alert(self, alert_svc):
        rule = await alert_svc.create_rule(AlertRuleCreate(name="ack-test", alert_type="test"))
        event = await alert_svc.fire_alert(rule.id, "needs ack")
        acked = await alert_svc.acknowledge_alert(
            event.id, AcknowledgeRequest(acknowledged_by=uuid4())
        )
        assert acked.acknowledged_at is not None
        assert acked.acknowledged_by is not None

    async def test_acknowledge_not_found(self, alert_svc):
        with pytest.raises(AlertEventNotFoundError):
            await alert_svc.acknowledge_alert(uuid4(), AcknowledgeRequest(acknowledged_by=uuid4()))


class TestAlertThresholds:
    async def test_evaluate_thresholds_empty(self, alert_svc):
        results = await alert_svc.evaluate_thresholds()
        assert results == []

    async def test_evaluate_thresholds_no_trigger(self, alert_svc):
        await alert_svc.create_rule(
            AlertRuleCreate(
                name="high-degradation",
                alert_type="server_health",
                condition={"metric": "degraded_servers", "threshold": 999},
            )
        )
        results = await alert_svc.evaluate_thresholds()
        assert len(results) == 1
        assert results[0].triggered is False

    async def test_evaluate_thresholds_triggers_on_degraded_servers(
        self, alert_svc, db_session: AsyncSession
    ):
        from api.models.audit import AuditEvent

        rule = await alert_svc.create_rule(
            AlertRuleCreate(
                name="degraded-check",
                alert_type="server_health",
                condition={"metric": "degraded_servers", "threshold": 2},
            )
        )
        for _ in range(3):
            db_session.add(
                AuditEvent(
                    event_type="server_degraded",
                    actor_type="system",
                    actor_id="health-checker",
                    details={},
                )
            )
        await db_session.commit()
        results = await alert_svc.evaluate_thresholds()
        triggered = [r for r in results if r.rule_id == rule.id]
        assert len(triggered) == 1
        assert triggered[0].triggered is True

    async def test_evaluate_thresholds_triggers_on_denied_requests(
        self, alert_svc, db_session: AsyncSession
    ):
        from api.models.audit import AuditEvent

        rule = await alert_svc.create_rule(
            AlertRuleCreate(
                name="denied-check",
                alert_type="security",
                condition={"metric": "denied_requests", "threshold": 1},
            )
        )
        for _ in range(2):
            db_session.add(
                AuditEvent(
                    event_type="access_denied",
                    actor_type="system",
                    actor_id="policy-enforcer",
                    details={},
                )
            )
        await db_session.commit()
        results = await alert_svc.evaluate_thresholds()
        triggered = [r for r in results if r.rule_id == rule.id]
        assert len(triggered) == 1
        assert triggered[0].triggered is True

    async def test_evaluate_thresholds_disabled_rule_skipped(
        self, alert_svc, db_session: AsyncSession
    ):
        from api.models.audit import AuditEvent

        rule = await alert_svc.create_rule(
            AlertRuleCreate(
                name="disabled-check",
                alert_type="server_health",
                condition={"metric": "degraded_servers", "threshold": 1},
            )
        )
        await alert_svc.toggle_rule(rule.id, enabled=False)
        db_session.add(
            AuditEvent(
                event_type="server_degraded",
                actor_type="system",
                actor_id="health-checker",
                details={},
            )
        )
        await db_session.commit()
        results = await alert_svc.evaluate_thresholds()
        assert len(results) == 0
