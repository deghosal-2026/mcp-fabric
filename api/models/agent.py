import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy import UUID as SAUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base, TimestampMixin, UUIDMixin


class AgentClass(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "agent_classes"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    team_namespace: Mapped[str | None] = mapped_column(String(100), nullable=True)

    trust_assignments = relationship(
        "TrustAssignment", back_populates="agent_class", cascade="all, delete-orphan"
    )
    agent_identities = relationship(
        "AgentIdentity", back_populates="agent_class", cascade="all, delete-orphan"
    )
    class_packs = relationship(
        "AgentClassPack", back_populates="agent_class", cascade="all, delete-orphan"
    )


class TrustAssignment(UUIDMixin, Base):
    __tablename__ = "trust_assignments"

    agent_class_id: Mapped[uuid.UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("agent_classes.id", ondelete="CASCADE"), nullable=False
    )
    server_id: Mapped[uuid.UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False
    )
    trust_level: Mapped[str] = mapped_column(String(50), nullable=False)
    tool_scope: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    agent_class = relationship("AgentClass", back_populates="trust_assignments")
    server = relationship("MCPServer", back_populates="trust_assignments")

    __table_args__ = (
        Index("idx_trust_class", "agent_class_id"),
        Index("uq_trust_class_server", "agent_class_id", "server_id", unique=True),
    )


class AgentIdentity(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "agent_identities"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    agent_class_id: Mapped[uuid.UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("agent_classes.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    token_prefix: Mapped[str | None] = mapped_column(String(10), nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), default="active")
    rate_limit_per_min: Mapped[int | None] = mapped_column(Integer, default=100)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    grace_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rotated_from_id: Mapped[uuid.UUID | None] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("agent_identities.id"), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    agent_class = relationship("AgentClass", back_populates="agent_identities")

    __table_args__ = (
        Index("idx_identities_class", "agent_class_id"),
        Index("idx_identities_status", "status"),
        Index("idx_identities_token", "token_hash"),
    )


class CapabilityPack(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "capability_packs"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    team_namespace: Mapped[str | None] = mapped_column(String(100), nullable=True)

    pack_assignments = relationship(
        "PackAssignment", back_populates="pack", cascade="all, delete-orphan"
    )
    class_packs = relationship(
        "AgentClassPack", back_populates="pack", cascade="all, delete-orphan"
    )


class PackAssignment(UUIDMixin, Base):
    __tablename__ = "pack_assignments"

    pack_id: Mapped[uuid.UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("capability_packs.id", ondelete="CASCADE"), nullable=False
    )
    capability_id: Mapped[uuid.UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("capabilities.id", ondelete="CASCADE"), nullable=False
    )

    pack = relationship("CapabilityPack", back_populates="pack_assignments")
    capability = relationship("Capability", back_populates="pack_assignments")

    __table_args__ = (
        Index("idx_packassignment_pack", "pack_id"),
        Index("idx_packassignment_capability", "capability_id"),
    )


class AgentClassPack(UUIDMixin, Base):
    __tablename__ = "agent_class_packs"

    agent_class_id: Mapped[uuid.UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("agent_classes.id", ondelete="CASCADE"), nullable=False
    )
    pack_id: Mapped[uuid.UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("capability_packs.id", ondelete="CASCADE"), nullable=False
    )

    agent_class = relationship("AgentClass", back_populates="class_packs")
    pack = relationship("CapabilityPack", back_populates="class_packs")

    __table_args__ = (
        Index("idx_agentclasspack_class", "agent_class_id"),
        Index("idx_agentclasspack_pack", "pack_id"),
    )
