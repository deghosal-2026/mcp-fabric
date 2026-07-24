import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy import UUID as SAUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base, TimestampMixin, UUIDMixin


class Capability(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "capabilities"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    domain: Mapped[str | None] = mapped_column(String(100), nullable=True)
    normalized_input_schema: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    normalized_output_schema: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), default="active")
    deprecated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    grace_period_days: Mapped[int | None] = mapped_column(Integer, default=14)
    migration_guidance: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

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
    __tablename__ = "capability_aliases"

    capability_id: Mapped[uuid.UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("capabilities.id", ondelete="CASCADE"), nullable=False
    )
    alias: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    capability = relationship("Capability", back_populates="aliases")

    __table_args__ = (
        Index("idx_aliases_alias", "alias"),
        Index("idx_aliases_capability", "capability_id"),
    )