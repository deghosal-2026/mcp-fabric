"""ORM models for normalized capabilities and their aliases.

A Capability is a vendor-neutral tool description with normalized
schemas. CapabilityAlias provides alternative names for discovery.
"""

from sqlalchemy import JSON, UUID, Column, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import relationship

from api.models.base import Base, TimestampMixin, UUIDMixin


class Capability(UUIDMixin, TimestampMixin, Base):
    """A normalized, server-agnostic capability with input/output schemas."""

    __tablename__ = "capabilities"

    name = Column(String(255), unique=True, nullable=False)
    domain = Column(String(100), nullable=True)
    normalized_input_schema = Column(JSON, nullable=True)
    normalized_output_schema = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="active")
    deprecated_at = Column(DateTime(timezone=True), nullable=True)
    grace_period_days = Column(Integer, default=14)
    migration_guidance = Column(Text, nullable=True)
    created_by = Column(String(255), nullable=True)

    mappings = relationship(
        "CapabilityMapping", back_populates="capability", cascade="all, delete-orphan"
    )
    aliases = relationship(
        "CapabilityAlias", back_populates="capability", cascade="all, delete-orphan"
    )
    pack_assignments = relationship(
        "PackAssignment", back_populates="capability", cascade="all, delete-orphan"
    )
    routing_rules = relationship(
        "RoutingRule", back_populates="capability", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_capabilities_domain", "domain"),
        Index("idx_capabilities_status", "status"),
    )


class CapabilityAlias(UUIDMixin, Base):
    """An alternative name pointing to a canonical Capability."""

    __tablename__ = "capability_aliases"

    capability_id = Column(
        UUID(as_uuid=True), ForeignKey("capabilities.id", ondelete="CASCADE"), nullable=False
    )
    alias = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    capability = relationship("Capability", back_populates="aliases")

    __table_args__ = (
        Index("idx_aliases_alias", "alias"),
        Index("idx_aliases_capability", "capability_id"),
    )
