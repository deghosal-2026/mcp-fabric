"""ORM models for audit logging, approvals, and alerting.

Tracks every action (AuditEvent), pending approval requests
(ApprovalRequest), alert rule definitions (AlertRule), and fired
alert events (AlertEvent).
"""

from sqlalchemy import JSON, UUID, Boolean, Column, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import relationship

from api.models.base import Base, UUIDMixin


class AuditEvent(UUIDMixin, Base):
    """Immutable record of an action performed in the fabric."""

    __tablename__ = "audit_events"

    event_type = Column(String(100), nullable=False)
    actor_type = Column(String(50), nullable=False)
    actor_id = Column(String(255), nullable=False)
    target_type = Column(String(50), nullable=True)
    target_id = Column(String(255), nullable=True)
    details = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_audit_type", "event_type"),
        Index("idx_audit_actor", "actor_type", "actor_id"),
        Index("idx_audit_time", "created_at"),
        Index("idx_audit_type_time", "event_type", "created_at"),
    )


class ApprovalRequest(UUIDMixin, Base):
    """A pending approval for a gated capability invocation."""

    __tablename__ = "approval_requests"

    agent_identity_id = Column(
        UUID(as_uuid=True), ForeignKey("agent_identities.id", ondelete="CASCADE"), nullable=False
    )
    capability_id = Column(
        UUID(as_uuid=True), ForeignKey("capabilities.id", ondelete="CASCADE"), nullable=False
    )
    server_id = Column(
        UUID(as_uuid=True), ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False
    )
    request_params = Column(JSON, nullable=True)
    status = Column(String(50), default="pending")
    approver_id = Column(
        UUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )
    approver_note = Column(Text, nullable=True)
    requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    agent_identity = relationship("AgentIdentity")
    capability = relationship("Capability")
    server = relationship("MCPServer")
    approver = relationship("AdminUser")

    __table_args__ = (
        Index("idx_approvals_status", "status"),
        Index("idx_approvals_agent", "agent_identity_id"),
    )


class AlertRule(UUIDMixin, Base):
    """A configurable rule that triggers AlertEvents on condition match."""

    __tablename__ = "alert_rules"

    name = Column(String(255), nullable=False)
    alert_type = Column(String(100), nullable=False)
    condition = Column(JSON, nullable=False)
    channels = Column(JSON, nullable=False)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_alertrules_enabled", "enabled"),
        Index("idx_alertrules_type", "alert_type"),
    )


class AlertEvent(UUIDMixin, Base):
    """A fired alert linked to a rule, optionally acknowledged by an admin."""

    __tablename__ = "alert_events"

    rule_id = Column(UUID(as_uuid=True), ForeignKey("alert_rules.id"), nullable=False)
    message = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)
    fired_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_by = Column(
        UUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )

    rule = relationship("AlertRule")
    acknowledged_by_user = relationship("AdminUser")

    __table_args__ = (
        Index("idx_alerts_fired", "fired_at"),
        Index("idx_alerts_rule", "rule_id"),
    )
