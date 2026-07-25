"""Alert rule management and threshold evaluation for MCP Fabric.

Provides create, fire, acknowledge lifecycle for alert rules, and
threshold evaluation against recent metrics and events.

Architectural notes:
  - Uses naive UTC datetimes throughout for cross-DB compatibility
    (SQLite has no timezone support; PostgreSQL stores tz-aware).
  - Threshold evaluation queries the AuditEvent table as a metrics
    source rather than maintaining a separate metrics store.
  - Alert events are a separate model from alert rules to support
    1:many firing (one rule can fire many times).
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
    """Alert rule management and threshold evaluation for MCP Fabric.

    Depends on: AsyncSession for DB access.
    Used by: admin alert UI, automated monitoring pipeline.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_rule(self, params: AlertRuleCreate) -> AlertRuleResponse:
        """Create a new alert rule with the given parameters.

        WHY: Admin user journey — define a new alert threshold.
        SIDE EFFECTS: Persists to DB, new rules start enabled.
        RETURN: The created rule with server-generated id and timestamps.
        """
        rule = AlertRule(
            name=params.name,
            alert_type=params.alert_type,
            condition=params.condition,
            channels=params.channels,
            enabled=True,
        )
        self.db.add(rule)
        # Commit triggers flush + DB insert; refresh loads server defaults (id, created_at).
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
        """List alert rules with optional type and enabled filters.

        WHY: Admin user journey — browse configured alert rules.
        Uses offset/limit pagination (cursor pagination is overkill for rule lists).
        """
        stmt = select(AlertRule).order_by(AlertRule.name)
        if alert_type:
            stmt = stmt.where(AlertRule.alert_type == alert_type)
        if enabled is not None:
            stmt = stmt.where(AlertRule.enabled == enabled)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return [self._rule_to_response(r) for r in result.scalars().all()]

    async def get_rule(self, rule_id: UUID) -> AlertRuleResponse:
        """Get a single alert rule by ID.

        RAISES: AlertRuleNotFoundError if missing.
        """
        result = await self.db.execute(select(AlertRule).where(AlertRule.id == rule_id))
        rule = result.scalar_one_or_none()
        if rule is None:
            raise AlertRuleNotFoundError(f"Alert rule {rule_id} not found")
        return self._rule_to_response(rule)

    async def update_rule(
        self,
        rule_id: UUID,
        params: AlertRuleCreate,
    ) -> AlertRuleResponse:
        """Update all fields of an existing alert rule.

        WHY: Admin user journey — modify an alert's condition or channels.
        Full-field replacement (not partial patch); partial updates go through
        a dedicated endpoint if needed.
        RAISES: AlertRuleNotFoundError if missing.
        """
        result = await self.db.execute(select(AlertRule).where(AlertRule.id == rule_id))
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
        """Delete an alert rule by ID.

        WHY: Admin user journey — remove a stale alert rule.
        Note: Does not cascade-delete associated AlertEvents; those remain
        for audit trail purposes.
        RAISES: AlertRuleNotFoundError if missing.
        """
        result = await self.db.execute(select(AlertRule).where(AlertRule.id == rule_id))
        rule = result.scalar_one_or_none()
        if rule is None:
            raise AlertRuleNotFoundError(f"Alert rule {rule_id} not found")
        await self.db.delete(rule)
        await self.db.commit()

    async def toggle_rule(self, rule_id: UUID, enabled: bool) -> AlertRuleResponse:
        """Enable or disable an alert rule by ID.

        WHY: Admin user journey — silence a rule without deleting it.
        RAISES: AlertRuleNotFoundError if missing.
        """
        result = await self.db.execute(select(AlertRule).where(AlertRule.id == rule_id))
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

        WHY: Automated pipeline / monitoring — fires when a threshold is breached.
        This is the 'raise' action separate from the evaluation logic.
        RAISES: AlertRuleNotFoundError if rule is missing.
        SIDE EFFECTS: Creates an AlertEvent row.
        """
        result = await self.db.execute(select(AlertRule).where(AlertRule.id == rule_id))
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
        """List alert events, optionally filtered by rule ID.

        WHY: Admin user journey — review alert history for a rule or globally.
        Ordered newest-first by fired_at so operators see recent events immediately.
        """
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
        """Mark an alert event as acknowledged with the given actor details.

        WHY: Operator user journey — signal that an alert has been seen/handled.
        Uses timezone-aware UTC via Python's UTC class, but the stored value
        is naive (tzinfo stripped by the column type).
        RAISES: AlertEventNotFoundError if missing.
        SIDE EFFECTS: Sets acknowledged_at and acknowledged_by on the event.
        """
        from datetime import UTC, datetime

        result = await self.db.execute(select(AlertEvent).where(AlertEvent.id == event_id))
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

        WHY: Monitoring pipeline — periodic evaluation of threshold conditions.
        Queries AuditEvent as a lightweight metrics source rather than pulling
        from dedicated monitoring infrastructure. This is intentionally simple:
        each rule's condition defines a metric name and threshold, and we count
        matching events within a fixed lookback window.

        SIDE EFFECTS: Read-only; does NOT fire alerts. The caller is responsible
        for calling fire_alert on triggered rules.

        The _naive helper strips tzinfo for cross-DB compatibility (SQLite
        doesn't store timezone info, so comparing tz-aware against naive fails).
        """
        from api.models.audit import AuditEvent as AuditEventModel

        result = await self.db.execute(select(AlertRule).where(AlertRule.enabled.is_(True)))
        rules = result.scalars().all()
        evaluations = []
        from datetime import UTC, datetime, timedelta

        # Strips tzinfo to produce a naive UTC datetime for SQLite compatibility.
        def _naive(minutes: int) -> datetime:
            return datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=minutes)

        for rule in rules:
            triggered = False
            message = None
            condition = rule.condition or {}
            metric = condition.get("metric")
            threshold = condition.get("threshold")

            if metric == "degraded_servers" and threshold is not None:
                # Counts AuditEvent rows with event_type='server_degraded' in last 5 min.
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
                # Counts AuditEvent rows with event_type='access_denied' in last 15 min.
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
        """Convert an AlertRule ORM object to an AlertRuleResponse schema.

        Handles the enabled field: SQLite may store it as 0/1 (integer) while
        PostgreSQL stores it as boolean. The `is not False` check normalizes this.
        """
        return AlertRuleResponse(
            id=rule.id,
            name=rule.name,
            alert_type=rule.alert_type,
            condition=rule.condition,
            channels=rule.channels,
            enabled=rule.enabled is not False,
            created_at=rule.created_at,
        )
