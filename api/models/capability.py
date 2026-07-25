"""ORM models for normalized capabilities and their aliases.

Capability     – The core abstraction in the fabric. A Capability represents a
                 normalized, versioned operation that can be fulfilled by one or
                 more MCP server tools. It decouples "what to do" from "which
                 server tool does it", enabling the routing layer to dispatch
                 requests dynamically.

CapabilityAlias – Alternate names for a Capability. Useful for backward
                  compatibility when renaming capabilities or for allowing
                  different agent teams to use different naming conventions.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy import UUID as SAUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base, TimestampMixin, UUIDMixin


class Capability(UUIDMixin, TimestampMixin, Base):
    """A normalized, versioned operation that the fabric routing layer can dispatch.

    Table: capabilities

    Unlike raw MCP server tools (which have arbitrary names and schemas),
    Capabilities are the fabric's normalized vocabulary. A capability name
    follows the pattern `domain:verb` (e.g. "code:review", "search:web").
    This normalization means agents only need to know capability names, not
    which server implements them.

    Lifecycle:
        - Active:   The capability is live and routable.
        - Deprecated: Still routable, but agents receive a deprecation warning.
                      After the grace period, the capability is removed.
        - Removed:  No longer available.

    Relationships (cascade delete):
        mappings       – CapabilityMapping rows linking to server tools.
        aliases        – Alternate names for this capability.
        pack_assignments – Junction rows linking to CapabilityPack.
        routing_rules  – Priority/condition-based routing rules.

    Columns:
        name (unique)       – Normalized name in `domain:verb` format.
        domain              – Optional domain grouping (e.g. "code", "search", "deploy").
        normalized_input_schema (JSON)  – The canonical input JSON Schema that agents
                                          should use when invoking this capability.
        normalized_output_schema (JSON) – The canonical output JSON Schema.
        description         – Human-readable explanation.
        status              – 'active' | 'deprecated' | 'removed'.
        deprecated_at       – When the deprecation was announced.
        grace_period_days   – How long after deprecation before the capability is removed
                              (default 14 days, giving agent owners time to migrate).
        migration_guidance  – Instructions for migrating to a replacement capability.
        created_by          – Who defined this capability (admin username or system).
    """

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
    resource_dimensions = relationship(
        "ResourceDimension", back_populates="capability", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_capabilities_domain", "domain"),
        Index("idx_capabilities_status", "status"),
    )


class CapabilityAlias(UUIDMixin, Base):
    """Alternate name for a Capability, for backward compatibility.

    Table: capability_aliases

    When a capability is renamed (e.g. "search:web" -> "search:www"), the old
    name is preserved as an alias. Agents that still use the old name will be
    transparently routed to the capability. This avoids breaking agents during
    renaming.

    Uniqueness: the alias itself is globally unique (no two capabilities can
    share the same alias).

    Columns:
        capability_id (FK) – The canonical capability this alias points to.
        alias (unique)     – The alternate name (e.g. "search:web").
        created_at         – When the alias was registered.
    """

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
