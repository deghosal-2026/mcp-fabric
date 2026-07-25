"""Alert rule management and threshold evaluation for MCP Fabric.

Provides create, fire, acknowledge lifecycle for alert rules, and
threshold evaluation against recent metrics and events.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.audit import AlertEvent, AlertRule
from api.schemas.alert import (
    AcknowledgeRequest,
    AlertEventResponse,
    AlertRuleCreate,
    AlertRuleResponse,
    ThresholdEvaluation,
)


class AlertRuleNotFoundError(Exception):
    """Raised when an alert rule ID is not found."""


class AlertEventNotFoundError(Exception):
    """Raised when an alert event ID is not found."""


class AlertService:
    """Alert rule management and threshold evaluation for MCP Fabric."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_rule(self, params: AlertRuleCreate) -> AlertRuleResponse:
        """Create a new alert rule with the given parameters."""
        rule = AlertRule(
            name=params.name,
            alert_type=params.alert_type,
            condition=params.condition,
            channels=params.channels,
            enabled=True,
        )
        self.db.add(rule)
        await self.db.commit()
        await self.db.refresh(rule)
        return self._rule_to_response(rule)

    async def list_rules(
        self,
        alert_type: str | None = None,
        enabled: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AlertRuleResponse]:
        """List alert rules with optional type and enabled filters."""
        stmt = select(AlertRule).order_by(AlertRule.name)
        if alert_type:
            stmt = stmt.where(AlertRule.alert_type == alert_type)
        if enabled is not None:
            stmt = stmt.where(AlertRule.enabled == enabled)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return [self._rule_to_response(r) for r in result.scalars().all()]

    async def get_rule(self, rule_id: UUID) -> AlertRuleResponse:
        """Get a single alert rule by ID. Raises AlertRuleNotFoundError if missing."""
        result = await self.db.execute(
            select(AlertRule).where(AlertRule.id == rule_id)
        )
        rule = result.scalar_one_or_none()
        if rule is None:
            raise AlertRuleNotFoundError(f"Alert rule {rule_id} not found")
        return self._rule_to_response(rule)

    async def update_rule(
        self,
        rule_id: UUID,
        params: AlertRuleCreate,
    ) -> AlertRuleResponse:
        """Update all fields of an existing alert rule."""
        result = await self.db.execute(
            select(AlertRule).where(AlertRule.id == rule_id)
        )
        rule = result.scalar_one_or_none()
        if rule is None:
            raise AlertRuleNotFoundError(f"Alert rule {rule_id} not found")
        rule.name = params.name
        rule.alert_type = params.alert_type
        rule.condition = params.condition
        rule.channels = params.channels
        await self.db.commit()
        await self.db.refresh(rule)
        return self._rule_to_response(rule)

    async def delete_rule(self, rule_id: UUID) -> None:
        """Delete an alert rule by ID. Raises AlertRuleNotFoundError if missing."""
        result = await self.db.execute(
            select(AlertRule).where(AlertRule.id == rule_id)
        )
        rule = result.scalar_one_or_none()
        if rule is None:
            raise AlertRuleNotFoundError(f"Alert rule {rule_id} not found")
        await self.db.delete(rule)
        await self.db.commit()

    async def toggle_rule(self, rule_id: UUID, enabled: bool) -> AlertRuleResponse:
        """Enable or disable an alert rule by ID."""
        result = await self.db.execute(
            select(AlertRule).where(AlertRule.id == rule_id)
        )
        rule = result.scalar_one_or_none()
        if rule is None:
            raise AlertRuleNotFoundError(f"Alert rule {rule_id} not found")
        rule.enabled = enabled
        await self.db.commit()
        await self.db.refresh(rule)
        return self._rule_to_response(rule)

    async def fire_alert(
        self,
        rule_id: UUID,
        message: str,
        details: dict | None = None,
    ) -> AlertEventResponse:
        """Create a new alert event for the given rule.

        Raises AlertRuleNotFoundError if rule is missing.
        """
        result = await self.db.execute(
            select(AlertRule).where(AlertRule.id == rule_id)
        )
        rule = result.scalar_one_or_none()
        if rule is None:
            raise AlertRuleNotFoundError(f"Alert rule {rule_id} not found")
        event = AlertEvent(
            rule_id=rule_id,
            message=message,
            details=details or {},
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return AlertEventResponse(
            id=event.id,
            rule_id=event.rule_id,
            message=event.message,
            details=event.details,
            fired_at=event.fired_at,
            acknowledged_at=event.acknowledged_at,
            acknowledged_by=event.acknowledged_by,
        )

    async def list_events(
        self,
        rule_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AlertEventResponse]:
        """List alert events, optionally filtered by rule ID."""
        stmt = select(AlertEvent).order_by(AlertEvent.fired_at.desc())
        if rule_id:
            stmt = stmt.where(AlertEvent.rule_id == rule_id)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return [
            AlertEventResponse(
                id=e.id,
                rule_id=e.rule_id,
                message=e.message,
                details=e.details,
                fired_at=e.fired_at,
                acknowledged_at=e.acknowledged_at,
                acknowledged_by=e.acknowledged_by,
            )
            for e in result.scalars().all()
        ]

    async def acknowledge_alert(
        self,
        event_id: UUID,
        params: AcknowledgeRequest,
    ) -> AlertEventResponse:
        """Mark an alert event as acknowledged with the given actor details."""
        from datetime import UTC, datetime

        result = await self.db.execute(
            select(AlertEvent).where(AlertEvent.id == event_id)
        )
        event = result.scalar_one_or_none()
        if event is None:
            raise AlertEventNotFoundError(f"Alert event {event_id} not found")
        event.acknowledged_at = datetime.now(UTC)
        event.acknowledged_by = params.acknowledged_by
        await self.db.commit()
        await self.db.refresh(event)
        return AlertEventResponse(
            id=event.id,
            rule_id=event.rule_id,
            message=event.message,
            details=event.details,
            fired_at=event.fired_at,
            acknowledged_at=event.acknowledged_at,
            acknowledged_by=event.acknowledged_by,
        )

    async def evaluate_thresholds(self) -> list[ThresholdEvaluation]:
        """Evaluate all enabled alert rules against recent metrics.

        Returns their triggered state.
        """
        from api.models.audit import AuditEvent as AuditEventModel

        result = await self.db.execute(
            select(AlertRule).where(AlertRule.enabled.is_(True))
        )
        rules = result.scalars().all()
        evaluations = []
        from datetime import UTC, datetime, timedelta

        def _naive(minutes: int) -> datetime:
            return datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=minutes)

        for rule in rules:
            triggered = False
            message = None
            condition = rule.condition or {}
            metric = condition.get("metric")
            threshold = condition.get("threshold")

            if metric == "degraded_servers" and threshold is not None:
                count = (
                    await self.db.execute(
                        select(func.count(AuditEventModel.id)).where(
                            AuditEventModel.event_type == "server_degraded",
                            AuditEventModel.created_at > _naive(5),
                        )
                    )
                ).scalar() or 0
                if count >= int(threshold):
                    triggered = True
                    message = f"{count} servers degraded in last 5 minutes (threshold: {threshold})"

            elif metric == "denied_requests" and threshold is not None:
                count = (
                    await self.db.execute(
                        select(func.count(AuditEventModel.id)).where(
                            AuditEventModel.event_type == "access_denied",
                            AuditEventModel.created_at > _naive(15),
                        )
                    )
                ).scalar() or 0
                if count >= int(threshold):
                    triggered = True
                    message = f"{count} denied requests in last 15 minutes (threshold: {threshold})"

            evaluations.append(
                ThresholdEvaluation(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    triggered=triggered,
                    message=message,
                )
            )
        return evaluations

    def _rule_to_response(self, rule: AlertRule) -> AlertRuleResponse:
        """Convert an AlertRule ORM object to an AlertRuleResponse schema."""
        return AlertRuleResponse(
            id=rule.id,
            name=rule.name,
            alert_type=rule.alert_type,
            condition=rule.condition,
            channels=rule.channels,
            enabled=rule.enabled is not False,
            created_at=rule.created_at,
        )
