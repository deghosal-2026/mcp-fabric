"""ORM models for resource-dimension policy constraints.

These tables implement the dynamic resource-dimension system that extends
the OPA policy engine from verb-only to verb+object authorization:

ResourceDimension   – Declares which resource dimensions constrain a capability
                      (e.g., ``deployment:promote`` is constrained by ``env``,
                      ``tenant``, ``service``).
DimensionValueMap   – Maps request parameters to dimension values for automatic
                      extraction at request time.
IdentityResourceBinding – Binds allowed resource values to a specific agent
                          identity (the source of truth for what an agent may
                          act on).
PackResourceBinding – Binds allowed resource values to a capability pack;
                      inherited by all agents assigned to that pack. Merged
                      with identity bindings at request time via intersection.
"""

import uuid

from sqlalchemy import UUID as SAUUID
from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base, TimestampMixin, UUIDMixin


class ResourceDimension(UUIDMixin, TimestampMixin, Base):
    """A resource dimension that constrains a capability.

    Table: resource_dimensions

    Platform engineers declare which dimensions constrain each capability.
    For example, ``deployment:promote`` might declare ``env``, ``tenant``,
    and ``service`` as its resource dimensions. Every request for that
    capability must then provide values for all declared dimensions, and
    those values must match the agent identity's allowed bindings.

    Uniqueness constraint: one (capability_id, dimension_key) pair — a
    capability cannot declare the same dimension twice.

    Columns:
        capability_id (FK -> capabilities) – The capability being constrained.
        dimension_key – Machine-readable key (e.g. ``env``, ``tenant``).
        display_name  – Human-readable label (e.g. ``Environment``).
    """

    __tablename__ = "resource_dimensions"

    capability_id: Mapped[uuid.UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("capabilities.id", ondelete="CASCADE"), nullable=False
    )
    dimension_key: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    capability = relationship("Capability", back_populates="resource_dimensions")
    value_maps = relationship(
        "DimensionValueMap", back_populates="resource_dimension", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_rd_capability", "capability_id"),
        Index("idx_rd_dimension", "dimension_key"),
        Index("uq_rd_capability_dimension", "capability_id", "dimension_key", unique=True),
    )


class DimensionValueMap(UUIDMixin, TimestampMixin, Base):
    """Maps a request parameter path to a resource dimension value.

    Table: dimension_value_map

    When an agent sends a capability request, Fabric must extract the
    resource values from the request. This table tells Fabric where to
    look: either from a JSON path within the request ``params`` (source
    ``param``) or from a fixed constant value (source ``constant``).

    For example:
      - dimension ``env`` with param_path ``params.env`` → reads
        ``request.params["env"]``.
      - dimension ``tenant`` with source ``constant`` and
        constant_value ``acme-corp`` → always uses ``acme-corp``.

    Columns:
        resource_dimension_id (FK) – Parent dimension.
        source – ``param`` (extract from request) or ``constant`` (fixed).
        param_path – JSON path within params (e.g. ``params.env``).
        constant_value – Fixed value used when source is ``constant``.
    """

    __tablename__ = "dimension_value_map"

    resource_dimension_id: Mapped[uuid.UUID] = mapped_column(
        SAUUID(as_uuid=True),
        ForeignKey("resource_dimensions.id", ondelete="CASCADE"),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="param")
    param_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    constant_value: Mapped[str | None] = mapped_column(String(255), nullable=True)

    resource_dimension = relationship("ResourceDimension", back_populates="value_maps")

    __table_args__ = (
        Index("idx_dvm_dimension", "resource_dimension_id"),
    )


class IdentityResourceBinding(UUIDMixin, TimestampMixin, Base):
    """Binds allowed resource values to an agent identity.

    Table: identity_resource_bindings

    Each row represents one allowed value for one resource dimension for one
    agent identity. For example, an agent identity ``release-engineer-01``
    might have bindings:
      - dimension_key ``env``, allowed_value ``staging``
      - dimension_key ``env``, allowed_value ``dev``
      - dimension_key ``tenant``, allowed_value ``acme-corp``

    These bindings are the source of truth for what resources an agent may
    act on. The model cannot escalate beyond what is bound here — any
    request for a dimension value not in this table is denied.

    Uniqueness constraint: one (agent_identity_id, dimension_key, allowed_value)
    triple — an identity cannot have duplicate bindings.

    Columns:
        agent_identity_id (FK -> agent_identities) – The identity being bound.
        dimension_key – Which dimension (e.g. ``env``).
        allowed_value – An allowed value for that dimension (e.g. ``staging``).
    """

    __tablename__ = "identity_resource_bindings"

    agent_identity_id: Mapped[uuid.UUID] = mapped_column(
        SAUUID(as_uuid=True),
        ForeignKey("agent_identities.id", ondelete="CASCADE"),
        nullable=False,
    )
    dimension_key: Mapped[str] = mapped_column(String(100), nullable=False)
    allowed_value: Mapped[str] = mapped_column(String(255), nullable=False)

    agent_identity = relationship("AgentIdentity", back_populates="resource_bindings")

    __table_args__ = (
        Index("idx_irb_identity", "agent_identity_id"),
        Index("idx_irb_dimension", "dimension_key"),
        Index(
            "uq_irb_identity_dimension_value",
            "agent_identity_id", "dimension_key", "allowed_value",
            unique=True,
        ),
    )


class PackResourceBinding(UUIDMixin, TimestampMixin, Base):
    """Binds allowed resource values to a capability pack.

    Table: pack_resource_bindings

    Capability packs can carry resource bindings that apply to every agent
    assigned to the pack. At request time, the effective allowed resources
    are the intersection of identity bindings and pack bindings per dimension.

    For example:
      - Identity binding: ``env: [staging, prod]``
      - Pack binding: ``env: [staging]``
      - Effective: ``env: [staging]``

    This lets platform engineers set organization-wide minimums via packs
    while still allowing per-agent overrides (as long as they fall within
    the pack's boundaries).

    Uniqueness constraint: one (pack_id, dimension_key, allowed_value) triple.

    Columns:
        pack_id (FK -> capability_packs) – The pack being bound.
        dimension_key – Which dimension (e.g. ``env``).
        allowed_value – An allowed value for that dimension (e.g. ``staging``).
    """

    __tablename__ = "pack_resource_bindings"

    pack_id: Mapped[uuid.UUID] = mapped_column(
        SAUUID(as_uuid=True),
        ForeignKey("capability_packs.id", ondelete="CASCADE"),
        nullable=False,
    )
    dimension_key: Mapped[str] = mapped_column(String(100), nullable=False)
    allowed_value: Mapped[str] = mapped_column(String(255), nullable=False)

    pack = relationship("CapabilityPack", back_populates="resource_bindings")

    __table_args__ = (
        Index("idx_prb_pack", "pack_id"),
        Index("idx_prb_dimension", "dimension_key"),
        Index(
            "uq_prb_pack_dimension_value",
            "pack_id", "dimension_key", "allowed_value",
            unique=True,
        ),
    )
