"""ORM models for agent classes, identities, trust, and capability packs.

Defines the agent taxonomy (AgentClass), per-agent credentials
(AgentIdentity), trust assignments to servers, and capability pack
grouping (CapabilityPack, PackAssignment, AgentClassPack).
"""

from sqlalchemy import JSON, UUID, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from api.models.base import Base, TimestampMixin, UUIDMixin


class AgentClass(UUIDMixin, TimestampMixin, Base):
    """A named role that groups agents with shared trust and permissions."""

    __tablename__ = "agent_classes"

    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    team_namespace = Column(String(100), nullable=True)

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
    """Links an agent class to a server with a specific trust level."""

    __tablename__ = "trust_assignments"

    agent_class_id = Column(
        UUID(as_uuid=True), ForeignKey("agent_classes.id", ondelete="CASCADE"), nullable=False
    )
    server_id = Column(
        UUID(as_uuid=True), ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False
    )
    trust_level = Column(String(50), nullable=False)
    tool_scope = Column(JSON, nullable=True)

    agent_class = relationship("AgentClass", back_populates="trust_assignments")
    server = relationship("MCPServer", back_populates="trust_assignments")

    __table_args__ = (Index("idx_trust_class", "agent_class_id"),)


class AgentIdentity(UUIDMixin, TimestampMixin, Base):
    """A specific agent credential tied to an agent class."""

    __tablename__ = "agent_identities"

    name = Column(String(255), unique=True, nullable=False)
    agent_class_id = Column(
        UUID(as_uuid=True), ForeignKey("agent_classes.id", ondelete="CASCADE"), nullable=False
    )
    token_hash = Column(String(512), nullable=False)
    token_prefix = Column(String(10), nullable=True)
    status = Column(String(50), default="active")
    rate_limit_per_min = Column(Integer, default=100)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    grace_period_end = Column(DateTime(timezone=True), nullable=True)
    rotated_from_id = Column(UUID(as_uuid=True), ForeignKey("agent_identities.id"), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    agent_class = relationship("AgentClass", back_populates="agent_identities")

    __table_args__ = (
        Index("idx_identities_class", "agent_class_id"),
        Index("idx_identities_status", "status"),
        Index("idx_identities_token", "token_hash"),
    )


class CapabilityPack(UUIDMixin, TimestampMixin, Base):
    """A named bundle of capabilities that can be assigned to agent classes."""

    __tablename__ = "capability_packs"

    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    team_namespace = Column(String(100), nullable=True)

    pack_assignments = relationship(
        "PackAssignment", back_populates="pack", cascade="all, delete-orphan"
    )
    class_packs = relationship(
        "AgentClassPack", back_populates="pack", cascade="all, delete-orphan"
    )


class PackAssignment(UUIDMixin, Base):
    """Many-to-many join between CapabilityPack and Capability."""

    __tablename__ = "pack_assignments"

    pack_id = Column(
        UUID(as_uuid=True), ForeignKey("capability_packs.id", ondelete="CASCADE"), nullable=False
    )
    capability_id = Column(
        UUID(as_uuid=True), ForeignKey("capabilities.id", ondelete="CASCADE"), nullable=False
    )

    pack = relationship("CapabilityPack", back_populates="pack_assignments")
    capability = relationship("Capability", back_populates="pack_assignments")

    __table_args__ = (
        Index("idx_packassignment_pack", "pack_id"),
        Index("idx_packassignment_capability", "capability_id"),
    )


class AgentClassPack(UUIDMixin, Base):
    """Many-to-many join between AgentClass and CapabilityPack."""

    __tablename__ = "agent_class_packs"

    agent_class_id = Column(
        UUID(as_uuid=True), ForeignKey("agent_classes.id", ondelete="CASCADE"), nullable=False
    )
    pack_id = Column(
        UUID(as_uuid=True), ForeignKey("capability_packs.id", ondelete="CASCADE"), nullable=False
    )

    agent_class = relationship("AgentClass", back_populates="class_packs")
    pack = relationship("CapabilityPack", back_populates="class_packs")

    __table_args__ = (
        Index("idx_agentclasspack_class", "agent_class_id"),
        Index("idx_agentclasspack_pack", "pack_id"),
    )
