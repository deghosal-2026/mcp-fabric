"""ORM models for audit logging, approval requests, and alerting.

AuditEvent     – Immutable log of every significant action in the fabric.
                  Used for compliance, debugging, and reconstructing history.
ApprovalRequest – Tracks approval-gated capability invocations. When an agent
                  class has trust_level='approval-gated', the router creates an
                  ApprovalRequest and waits for an admin to approve or deny it.
AlertRule      – Configurable conditions that trigger alerts (e.g. "failure rate
                  exceeds 5% in 5 minutes").
AlertEvent     – A specific firing of an AlertRule, with optional acknowledgment.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy import UUID as SAUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base, UUIDMixin


class AuditEvent(UUIDMixin, Base):
    """Immutable record of a security-relevant action in the fabric.

    Table: audit_events

    Every server registration, capability mapping change, trust assignment,
    login, approval resolution, etc. writes an AuditEvent row. These rows
    are append-only — never updated or deleted — to preserve a reliable
    audit trail.

    Indexing strategy:
        idx_audit_type      – Filter by event_type (e.g. "server.created").
        idx_audit_actor     – Find all actions by a specific actor.
        idx_audit_time      – Time-range queries for dashboard / export.
        idx_audit_type_time – Composite index for the most common query pattern:
                              "show me all events of type X in the last N hours".

    Columns:
        event_type – Namespaced string: "server.created", "capability.mapped",
                     "agent.connected", "approval.resolved", etc.
        actor_type – 'admin_user', 'agent_identity', or 'system'.
        actor_id   – UUID of the actor (as a string for flexibility).
        target_type – Optional: what entity was acted upon ('server', 'capability').
        target_id   – Optional: UUID of the target entity.
        details (JSON) – Arbitrary structured payload describing the change
                        (e.g. old_value / new_value, request params, IP address).
        created_at – Timestamp of the event (server default, never client-supplied).
    """

    __tablename__ = "audit_events"

    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(255), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_audit_type", "event_type"),
        Index("idx_audit_actor", "actor_type", "actor_id"),
        Index("idx_audit_time", "created_at"),
        Index("idx_audit_type_time", "event_type", "created_at"),
    )


class ApprovalRequest(UUIDMixin, Base):
    """Tracks a pending / resolved approval for an approval-gated capability call.

    Table: approval_requests

    When the router intercepts a capability invocation for which the agent's
    trust level is 'approval-gated', it creates an ApprovalRequest and returns
    a pending status to the agent. An admin later approves or denies it via
    the approval API, and the router completes (or rejects) the original call.

    The request has a hard expiry (expires_at); if not resolved by that time
    it is auto-denied.

    Foreign keys:
        agent_identity_id -> agent_identities.id  (who asked)
        capability_id     -> capabilities.id       (what they want to do)
        server_id         -> mcp_servers.id        (which server to call)
        approver_id       -> admin_users.id        (who resolved it, nullable)

    Columns:
        request_params (JSON) – Parameters the agent wanted to pass to the capability.
        result (JSON)  – Output returned from the capability after approval.
        status         – 'pending' | 'approved' | 'denied' | 'expired'.
        approver_note  – Optional reason for approval/denial.
        requested_at   – When the request was created.
        resolved_at    – When an admin acted (approved or denied).
        expires_at     – Deadline; requests past this date are auto-denied.
    """

    __tablename__ = "approval_requests"

    agent_identity_id: Mapped[uuid.UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("agent_identities.id", ondelete="CASCADE"), nullable=False
    )
    capability_id: Mapped[uuid.UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("capabilities.id", ondelete="CASCADE"), nullable=False
    )
    server_id: Mapped[uuid.UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False
    )
    request_params: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), default="pending")
    approver_id: Mapped[uuid.UUID | None] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )
    approver_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    agent_identity = relationship("AgentIdentity")
    capability = relationship("Capability")
    server = relationship("MCPServer")
    approver = relationship("AdminUser")

    __table_args__ = (
        Index("idx_approvals_status", "status"),
        Index("idx_approvals_agent", "agent_identity_id"),
    )


class AlertRule(UUIDMixin, Base):
    """Configurable alert rule with a condition and notification channels.

    Table: alert_rules

    Example: "alert_type='error_rate', condition={'threshold': 0.05, 'window_minutes': 5}"

    The fabric monitor evaluates rules periodically. When a rule's condition
    evaluates to true, an AlertEvent is created.

    Columns:
        name           – Human-readable label (e.g. "High error rate on prod").
        alert_type     – Discriminator: 'error_rate', 'latency_p99', 'auth_failures', etc.
        condition (JSON) – Rule-specific condition payload (structure varies by alert_type).
        channels (JSON)  – Notification destinations: ['log', 'slack', 'pagerduty', 'webhook'].
        enabled        – Whether this rule is active. Disabled rules are still stored
                         but not evaluated.
        created_at     – When the rule was defined.
    """

    __tablename__ = "alert_rules"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(100), nullable=False)
    condition: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    channels: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    enabled: Mapped[bool | None] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_alertrules_enabled", "enabled"),
        Index("idx_alertrules_type", "alert_type"),
    )


class AlertEvent(UUIDMixin, Base):
    """A specific firing of an AlertRule, with optional administrative acknowledgment.

    Table: alert_events

    When a rule condition triggers, an AlertEvent is created. If the alert is
    acknowledged, acknowledged_at and acknowledged_by are set.

    Foreign keys:
        rule_id (FK -> alert_rules)        – Which rule fired.
        acknowledged_by (FK -> admin_users) – Admin who acknowledged the alert.

    Columns:
        rule_id         – FK to the AlertRule that generated this event.
        message         – Human-readable alert description (e.g. "Error rate 7.2% > 5%").
        details (JSON)  – Additional context (e.g. affected server IDs, metric values).
        fired_at        – When the condition was met.
        acknowledged_at – When an admin clicked "Acknowledge" in the UI.
        acknowledged_by – FK to the admin user who acknowledged.
    """

    __tablename__ = "alert_events"

    rule_id: Mapped[uuid.UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("alert_rules.id"), nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    fired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )

    rule = relationship("AlertRule")
    acknowledged_by_user = relationship("AdminUser")

    __table_args__ = (
        Index("idx_alerts_fired", "fired_at"),
        Index("idx_alerts_rule", "rule_id"),
    )
