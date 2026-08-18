"""ORM models for MCP server registration, tools, and routing.

MCPServer         – A registered MCP (Model Context Protocol) server endpoint.
                    This is the primary entity representing an external service.
ServerTool        – A tool (function) exposed by an MCP server at registration time.
ToolVersion       – Historical snapshot of a tool's schema when it changed.
CapabilityMapping – Links a normalized Capability to a specific ServerTool on a specific
                    MCPServer, with optional input/output schema transformations.
RoutingRule       – Priority-ordered rules that control how a Capability is routed to
                    one of its mapped servers (e.g. primary vs failover, conditional routing).
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy import UUID as SAUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base, TimestampMixin, UUIDMixin


class MCPServer(UUIDMixin, TimestampMixin, Base):
    """A registered MCP server endpoint that exposes tools via the MCP protocol.

    Table: mcp_servers

    This is the central entity in the fabric. Every tool invocation ultimately
    routes to an MCPServer. Servers go through a lifecycle:
        1. Registered (initial state, health unknown).
        2. Verified (health check passes, trust level assigned).
        3. Active (serving traffic).
        4. Decommissioning (drain phase, then removal).

    Relationships (cascade delete):
        tools             – ServerTool rows (tools this server exposes).
        tool_versions     – Historical schema snapshots for change detection.
        mappings          – CapabilityMapping rows (which capabilities map to which tools).
        trust_assignments – TrustAssignment rows (which agent classes trust this server).
        routing_rules     – RoutingRule rows (how capabilities route here).

    Columns:
        name              – Human-readable label (e.g. "production-code-server").
        endpoint          – URL of the MCP server (e.g. "https://mcp.internal:8443").
        owner_team        – Team responsible for maintaining this server.
        description       – What this server does.
        labels (JSON)     – Arbitrary key-value labels for filtering and grouping.
        trust_level       – Default trust level for new trust assignments
                            ('unreviewed' until an admin evaluates it).
        health_status     – 'unknown' | 'healthy' | 'degraded' | 'unreachable'.
        last_health_check – When the last health probe was performed.
        updated_at        – When server metadata was last modified.
        version           – Reported server version (from health check).
        team_namespace    – Multi-tenant ownership scope.
        decommissioned_at – When the server was fully decommissioned.
        decommission_phase – Current decommission stage: 'draining' | 'completed'.
    """

    __tablename__ = "mcp_servers"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(1024), nullable=False)
    owner_team: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    labels: Mapped[list[Any] | None] = mapped_column(JSON, default=lambda: [])
    trust_level: Mapped[str | None] = mapped_column(String(50), default="unreviewed")
    health_status: Mapped[str | None] = mapped_column(String(50), default="unknown")
    last_health_check: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    team_namespace: Mapped[str | None] = mapped_column(String(100), nullable=True)
    decommissioned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    decommission_phase: Mapped[str | None] = mapped_column(String(50), nullable=True)

    tools = relationship("ServerTool", back_populates="server", cascade="all, delete-orphan")
    tool_versions = relationship(
        "ToolVersion", back_populates="server", cascade="all, delete-orphan"
    )
    mappings = relationship(
        "CapabilityMapping", back_populates="server", cascade="all, delete-orphan"
    )
    trust_assignments = relationship(
        "TrustAssignment", back_populates="server", cascade="all, delete-orphan"
    )
    routing_rules = relationship(
        "RoutingRule", back_populates="server", cascade="all, delete-orphan"
    )


class ServerTool(UUIDMixin, Base):
    """A tool (function/operation) exposed by an MCP server.

    Table: server_tools

    When a server is registered or re-scanned, the fabric fetches its tool list
    and creates one ServerTool row per tool. Each tool has a name, description,
    input JSON Schema, and optional output JSON Schema.

    Uniqueness constraint: (server_id, tool_name) must be unique — a server
    cannot expose two tools with the same name.

    Columns:
        server_id (FK)   – The MCPServer that exposes this tool.
        tool_name        – Name of the tool (e.g. "review_code", "deploy_service").
        description      – Human-readable description of what the tool does.
        input_schema (JSON) – JSON Schema describing the expected input parameters.
        output_schema (JSON) – JSON Schema describing the tool's return value.
    """

    __tablename__ = "server_tools"

    server_id: Mapped[uuid.UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False
    )
    tool_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_schema: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    output_schema: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    server = relationship("MCPServer", back_populates="tools")

    __table_args__ = (
        Index("idx_tools_server", "server_id"),
        Index("idx_tools_server_tool", "server_id", "tool_name", unique=True),
    )


class ToolVersion(UUIDMixin, Base):
    """Historical snapshot of a server tool's schema when it changed.

    Table: tool_versions

    When the fabric rescans a server and detects that a tool's input or output
    schema has changed, it creates a new ToolVersion row to record the old
    schemas before updating ServerTool. This enables:
        - Detecting breaking schema changes (is_breaking flag).
        - Alerting admins when tools change unexpectedly.
        - Providing a schema change timeline for debugging.

    Columns:
        server_id (FK)      – The server whose tool changed.
        tool_name           – Name of the tool that changed.
        input_schema (JSON) – The new (or changed) input schema.
        output_schema (JSON)– The new (or changed) output schema.
        is_breaking         – True if required fields were added or types changed
                              incompatibly (heuristic detection).
        detected_at         – When the change was detected during a rescan.
    """

    __tablename__ = "tool_versions"

    server_id: Mapped[uuid.UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False
    )
    tool_name: Mapped[str] = mapped_column(String(255), nullable=False)
    input_schema: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    output_schema: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    is_breaking: Mapped[bool | None] = mapped_column(default=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    server = relationship("MCPServer", back_populates="tool_versions")

    __table_args__ = (Index("idx_tool_versions_server", "server_id", "tool_name"),)


class CapabilityMapping(UUIDMixin, Base):
    """Links a normalized Capability to a specific tool on a specific server.

    Table: capability_mappings

    This is the routing table. When an agent invokes a capability (e.g. "code:review"),
    the router looks up all CapabilityMapping rows for that capability and selects
    the best one based on routing_weight, is_primary, and RoutingRule priority.

    Schema transformation: input_mapping and output_mapping are JSON objects
    that define how to translate between the capability's normalized schema and
    the server tool's native schema. This allows the same capability to be
    fulfilled by servers with different tool signatures.

    Uniqueness constraint: (capability_id, server_id, tool_name) – you can only
    have one mapping per capability+server+tool combination.

    Columns:
        capability_id (FK) – The normalized capability.
        server_id (FK)     – The server hosting the tool.
        tool_name          – The tool on that server that fulfills the capability.
        input_mapping (JSON)  – Schema transformation: capability params -> tool params.
        output_mapping (JSON) – Schema transformation: tool result -> capability result.
        is_primary            – Whether this is the preferred mapping (used as default route).
        routing_weight        – Weight for load-balanced routing. Higher weight = more traffic.
        tool_schema_digest    – SHA-256 digest of (tool_name + input_schema + output_schema).
        status                – 'active' | 'stale' | 'pending_review' | 'rejected'.
        created_at            – When this mapping was established.
    """

    __tablename__ = "capability_mappings"

    capability_id: Mapped[uuid.UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("capabilities.id", ondelete="CASCADE"), nullable=False
    )
    server_id: Mapped[uuid.UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False
    )
    tool_name: Mapped[str] = mapped_column(String(255), nullable=False)
    input_mapping: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    output_mapping: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    is_primary: Mapped[bool | None] = mapped_column(default=True)
    routing_weight: Mapped[float | None] = mapped_column(Float, default=1.0)
    tool_schema_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # SHA-256 hex digest of (tool_name + input_schema + output_schema).
    # Used by routing to detect schema drift: if the current ServerTool's digest
    # doesn't match this stored value, the mapping is stale and should not be used.
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    # Routing lifecycle status: 'active' (live), 'stale' (schema changed, needs review),
    # 'pending_review' (collision, not routable), 'stale-unverified' (re-inspection
    # failed, fail-closed, #444), 'rejected' (admin denied, retired, not routable).
    # States: active = live, stale/pending_review/stale-unverified = limbo,
    # rejected = retired. Limbo is visible and time-boxed via pending_since.
    pending_since: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Classification of why a mapping sits in limbo (#447). Distinguishes
    # "server unreachable" (decide retire-or-wait, hands-off) from "schema
    # genuinely changed" (review and re-approve, hands-on) so unreachable
    # items never bury real schema changes or count toward the reviewer's
    # pending-critical tally:
    #   unreachable      — re-inspection could not reach the server.
    #   timeout          — re-inspection timed out.
    #   drifted          — re-inspection found a schema change (needs review).
    #   schema_mismatch  — many-to-one capability-mapping collision (#441).
    failure_class: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    capability = relationship("Capability", back_populates="mappings")
    server = relationship("MCPServer", back_populates="mappings")
    reviews = relationship("MappingReview", back_populates="mapping", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_mappings_capability", "capability_id"),
        Index("idx_mappings_server", "server_id"),
        Index("idx_mappings_status", "status"),
        Index("idx_mappings_failure_class", "failure_class"),
        Index("idx_mappings_unique", "capability_id", "server_id", "tool_name", unique=True),
        Index(
            "idx_mappings_digest_unique",
            "capability_id",
            "server_id",
            "tool_schema_digest",
            unique=True,
        ),
    )


class MappingReview(UUIDMixin, Base):
    """Records an admin review when a schema-digest drift is detected.

    Table: mapping_reviews

    When a server is re-inspected and a tool's schema has changed, the affected
    CapabilityMapping is marked 'stale'. An admin reviews the change, compares
    old/new digests, and either approves ('active') or rejects ('rejected') the
    mapping. Each decision creates a MappingReview row for the audit trail.

    State machine: active ↔ stale → pending_review → active / rejected

    This model stores the before-and-after digest values so the audit trail
    can show exactly what schema identity changed and what the admin decided.

    Columns:
        mapping_id (FK)    – The capability mapping being reviewed.
        previous_digest    – SHA-256 digest before the schema change.
        new_digest         – SHA-256 digest after the schema change (same as
                             previous if rejected).
        decision           – 'approved' | 'rejected'.
        reason             – Optional free-text justification from the admin.
        reviewed_by (FK)   – Admin user who made the decision (nullable for
                             system-initiated reviews).
        created_at         – When the review was submitted.
    """

    __tablename__ = "mapping_reviews"

    mapping_id: Mapped[uuid.UUID] = mapped_column(
        SAUUID(as_uuid=True),
        ForeignKey("capability_mappings.id", ondelete="CASCADE"),
        nullable=False,
    )
    previous_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    new_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("admin_users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    mapping = relationship("CapabilityMapping", back_populates="reviews")

    __table_args__ = (
        Index("idx_mapping_reviews_mapping", "mapping_id"),
        Index("idx_mapping_reviews_decision", "decision"),
    )


class RoutingRule(UUIDMixin, Base):
    """Priority-ordered rule that controls capability-to-server routing decisions.

    Table: routing_rules

    When multiple server mappings exist for a capability, RoutingRules determine
    which server to use based on priority and conditions. For example:
        - Priority 0: route to primary server unconditionally.
        - Priority 1: route to failover server if primary is unhealthy.
        - Priority 2: route to canary server if request has "X-Canary: true" header.

    The condition field uses a simple expression language (e.g.
    {"server_health": "healthy", "labels": {"includes": "canary"}}).

    Columns:
        capability_id (FK) – The capability this rule applies to.
        server_id (FK)     – The target server for this rule.
        priority           – Lower values are evaluated first (0 = highest priority).
        condition (JSON)   – Optional condition that must be true for this rule to match.
                             If null, the rule is unconditional.
        created_at         – When the rule was created.
        created_by         – Who created the rule (admin username or system).
    """

    __tablename__ = "routing_rules"

    capability_id: Mapped[uuid.UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("capabilities.id", ondelete="CASCADE"), nullable=False
    )
    server_id: Mapped[uuid.UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False
    )
    priority: Mapped[int | None] = mapped_column(Integer, default=0)
    condition: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    capability = relationship("Capability", back_populates="routing_rules")
    server = relationship("MCPServer", back_populates="routing_rules")

    __table_args__ = (
        Index("idx_routing_rules_cap", "capability_id"),
        Index("idx_routing_rules_server", "server_id"),
    )
