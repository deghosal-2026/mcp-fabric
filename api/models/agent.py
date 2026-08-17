"""ORM models for agent classes, agent identities, capability packs, and trust.

These tables form the core of the fabric's agent management:

AgentClass     – A logical group / role (e.g. "code-reviewer", "deploy-bot").
                 An AgentClass defines what category of agent this is.
TrustAssignment – Declares which MCP servers an AgentClass is allowed to call,
                  at what trust level (trusted / restricted / approval-gated).
AgentIdentity  – A concrete authentication credential belonging to an AgentClass.
                 An AgentClass can have multiple identities (e.g. staging + prod).
CapabilityPack – A named group of capabilities that can be assigned to classes.
PackAssignment – Many-to-many link between CapabilityPack and Capability.
AgentClassPack – Many-to-many link between AgentClass and CapabilityPack.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy import UUID as SAUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base, TimestampMixin, UUIDMixin


class AgentClass(UUIDMixin, TimestampMixin, Base):
    """Logical group/role for agents (e.g. "code-reviewer", "deploy-bot").

    Table: agent_classes

    An AgentClass is the unit of trust and authorization. Instead of granting
    permissions to individual agent identities, you assign trust to the class,
    and every identity within the class inherits those permissions. This follows
    RBAC principles where the class is the "role".

    Relationships (cascade delete):
        trust_assignments – List of TrustAssignment rows linking this class to MCP servers.
        agent_identities – List of AgentIdentity rows (concrete credentials).
        class_packs      – List of AgentClassPack rows (capability-pack membership).

    Columns:
        name (unique)   – Human-readable label (e.g. "ci-pipeline").
        description     – Optional explanation of the class's purpose.
        team_namespace  – Multi-tenant scope; if set, this class is visible only
                          within that team's namespace.
    """

    __tablename__ = "agent_classes"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    team_namespace: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # When True, this agent class is read-scoped: it may only invoke read-only
    # tools. Mutating tools are denied at the request level regardless of trust.
    is_read_only: Mapped[bool] = mapped_column(default=False, nullable=False)

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
    """Declares what trust level an AgentClass has for a specific MCP server.

    Table: trust_assignments

    Without a TrustAssignment row, an AgentClass has no access to the server.
    The trust_level determines how requests are handled:
        - trusted:        Allowed directly, no approval needed.
        - restricted:     Allowed but may have tool-scope limits.
        - approval-gated: Requires an admin to approve each invocation.
        - unreviewed:     Default; effectively blocked until reviewed.

    Uniqueness constraint: one (agent_class_id, server_id) pair — a class can
    only have one trust level per server.

    Columns:
        agent_class_id (FK -> agent_classes) – The class receiving trust.
        server_id (FK -> mcp_servers)        – The server being trusted.
        trust_level  – 'trusted' | 'restricted' | 'approval-gated' | 'unreviewed'.
        tool_scope (JSON) – Optional list of tool names or patterns to restrict
                            access to a subset of the server's tools.
    """

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
    """A concrete agent authentication credential.

    Table: agent_identities

    An AgentIdentity belongs to exactly one AgentClass. When an agent connects
    to the fabric, it presents a bearer token; the fabric looks up the token_hash
    to find the identity, then uses the identity's agent_class_id to determine
    trust and permissions.

    Token rotation is supported: rotated_from_id points to the previous identity
    that was replaced, preserving an audit trail.

    Columns:
        name (unique)      – Human label (e.g. "prod-ci-agent-v2").
        agent_class_id (FK)– The class this identity belongs to.
        token_hash         – bcrypt/Argon2id hash of the agent's bearer token (never
                             store the raw token).
        token_prefix       – First few chars of the raw token (for display in UI so
                             admins can recognise which token is which).
        status             – 'active', 'revoked', 'expired'.
        rate_limit_per_min – Per-identity rate cap (default 100 req/min).
        expires_at         – Optional expiry; after this date the token cannot be used.
        grace_period_end   – For deprecated tokens: window during which the old token
                             still works (used during rotation).
        rotated_from_id (FK) – Self-referential FK pointing to the previous identity
                               that this one replaced. NULL for first-generation tokens.
        revoked_at         – When the identity was manually revoked.
    """

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
    resource_bindings = relationship(
        "IdentityResourceBinding", back_populates="agent_identity", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_identities_class", "agent_class_id"),
        Index("idx_identities_status", "status"),
        Index("idx_identities_token", "token_hash"),
    )


class CapabilityPack(UUIDMixin, TimestampMixin, Base):
    """A named group of capabilities that can be assigned to agent classes.

    Table: capability_packs

    Capability packs are a convenience abstraction: instead of assigning 20
    individual capabilities to each AgentClass, you create a pack (e.g.
    "developer-tools") and assign the pack to the class. Changes to the pack
    automatically propagate to all assigned classes.

    Relationships:
        pack_assignments – Links to Capability via PackAssignment.
        class_packs      – Links to AgentClass via AgentClassPack.

    Columns:
        name (unique)   – Human label (e.g. "ci-cd-basics").
        description     – Explanation of what capabilities the pack contains.
        team_namespace  – Multi-tenant scope.
    """

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
    resource_bindings = relationship(
        "PackResourceBinding", back_populates="pack", cascade="all, delete-orphan"
    )


class PackAssignment(UUIDMixin, Base):
    """Many-to-many join: which capabilities belong to which packs.

    Table: pack_assignments

    This is a pure junction table. Deleting a CapabilityPack cascades to delete
    its PackAssignment rows. Deleting a Capability similarly cascades.

    Columns:
        pack_id (FK)       – References capability_packs.id.
        capability_id (FK) – References capabilities.id.
    """

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
    """Many-to-many join: which packs are assigned to which agent classes.

    Table: agent_class_packs

    Pure junction table. Deleting either side cascades to remove the join row.
    There is no uniqueness constraint on (agent_class_id, pack_id) — the
    application layer should enforce that, but the current schema allows
    duplicates (a design choice to keep the model simple).

    Columns:
        agent_class_id (FK) – References agent_classes.id.
        pack_id (FK)        – References capability_packs.id.
    """

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
