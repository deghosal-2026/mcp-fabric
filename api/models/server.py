import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy import UUID as SAUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base, TimestampMixin, UUIDMixin


class MCPServer(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "mcp_servers"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(1024), nullable=False)
    owner_team: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    labels: Mapped[list[Any] | None] = mapped_column(JSON, default=lambda: [])
    trust_level: Mapped[str | None] = mapped_column(String(50), default="unreviewed")
    health_status: Mapped[str | None] = mapped_column(String(50), default="unknown")
    last_health_check: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    team_namespace: Mapped[str | None] = mapped_column(String(100), nullable=True)
    decommissioned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    capability = relationship("Capability", back_populates="mappings")
    server = relationship("MCPServer", back_populates="mappings")

    __table_args__ = (
        Index("idx_mappings_capability", "capability_id"),
        Index("idx_mappings_server", "server_id"),
        Index("idx_mappings_unique", "capability_id", "server_id", "tool_name", unique=True),
    )


class RoutingRule(UUIDMixin, Base):
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