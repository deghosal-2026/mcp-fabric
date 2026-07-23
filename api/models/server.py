"""ORM models for MCP server registration, tools, and routing.

Core entities: MCPServer (registered MCP servers), ServerTool
(individual tool endpoints), ToolVersion (schema change tracking),
CapabilityMapping (server-to-capability bridge), and RoutingRule
(priority-based capability routing).
"""

from sqlalchemy import (
    JSON,
    UUID,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from api.models.base import Base, TimestampMixin, UUIDMixin


class MCPServer(UUIDMixin, TimestampMixin, Base):
    """A registered MCP server known to the fabric."""

    __tablename__ = "mcp_servers"

    name = Column(String(255), nullable=False)
    endpoint = Column(String(1024), nullable=False)
    owner_team = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    labels = Column(JSON, default=lambda: [])
    trust_level = Column(String(50), default="unreviewed")
    health_status = Column(String(50), default="unknown")
    last_health_check = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)
    version = Column(String(50), nullable=True)
    team_namespace = Column(String(100), nullable=True)
    decommissioned_at = Column(DateTime(timezone=True), nullable=True)
    decommission_phase = Column(String(50), nullable=True)

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
    """A single tool exposed by an MCP server."""

    __tablename__ = "server_tools"

    server_id = Column(
        UUID(as_uuid=True), ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False
    )
    tool_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    input_schema = Column(JSON, nullable=False)
    output_schema = Column(JSON, nullable=True)

    server = relationship("MCPServer", back_populates="tools")

    __table_args__ = (
        Index("idx_tools_server", "server_id"),
        Index("idx_tools_server_tool", "server_id", "tool_name", unique=True),
    )


class ToolVersion(UUIDMixin, Base):
    """Historical snapshot of a tool's schema for change detection."""

    __tablename__ = "tool_versions"

    server_id = Column(
        UUID(as_uuid=True), ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False
    )
    tool_name = Column(String(255), nullable=False)
    input_schema = Column(JSON, nullable=False)
    output_schema = Column(JSON, nullable=True)
    is_breaking = Column(Boolean, default=False)
    detected_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    server = relationship("MCPServer", back_populates="tool_versions")

    __table_args__ = (Index("idx_tool_versions_server", "server_id", "tool_name"),)


class CapabilityMapping(UUIDMixin, Base):
    """Bridges a normalized capability to a concrete server tool."""

    __tablename__ = "capability_mappings"

    capability_id = Column(
        UUID(as_uuid=True), ForeignKey("capabilities.id", ondelete="CASCADE"), nullable=False
    )
    server_id = Column(
        UUID(as_uuid=True), ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False
    )
    tool_name = Column(String(255), nullable=False)
    input_mapping = Column(JSON, nullable=True)
    output_mapping = Column(JSON, nullable=True)
    is_primary = Column(Boolean, default=True)
    routing_weight = Column(Float, default=1.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    capability = relationship("Capability", back_populates="mappings")
    server = relationship("MCPServer", back_populates="mappings")

    __table_args__ = (
        Index("idx_mappings_capability", "capability_id"),
        Index("idx_mappings_server", "server_id"),
        Index("idx_mappings_unique", "capability_id", "server_id", "tool_name", unique=True),
    )


class RoutingRule(UUIDMixin, Base):
    """Priority-ordered routing rule for capability dispatch."""

    __tablename__ = "routing_rules"

    capability_id = Column(
        UUID(as_uuid=True), ForeignKey("capabilities.id", ondelete="CASCADE"), nullable=False
    )
    server_id = Column(
        UUID(as_uuid=True), ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False
    )
    priority = Column(Integer, default=0)
    condition = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(String(255), nullable=True)

    capability = relationship("Capability", back_populates="routing_rules")
    server = relationship("MCPServer", back_populates="routing_rules")

    __table_args__ = (
        Index("idx_routing_rules_cap", "capability_id"),
        Index("idx_routing_rules_server", "server_id"),
    )
