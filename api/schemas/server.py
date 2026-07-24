"""Pydantic schemas for MCP server registration and inspection.

ServerCreate is the input; ServerResponse and ServerInspectResponse
are API output shapes with tool listings and change detection.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from api.schemas.agent import TrustAssignmentResponse
from api.schemas.capability import CapabilityMappingResponse


class ServerCreate(BaseModel):
    """Request body for registering a new MCP server."""


    name: str = Field(min_length=1, max_length=255)
    endpoint: str = Field(pattern=r"^https?://")
    owner_team: str | None = None
    description: str | None = None
    labels: list[str] = []
    team_namespace: str | None = None


class ToolResponse(BaseModel):
    """A tool exposed by an MCP server."""

    id: UUID
    tool_name: str
    description: str | None = None
    input_schema: dict
    output_schema: dict | None = None

    model_config = {"from_attributes": True}


class ToolChange(BaseModel):
    """A detected change in a tool's schema between inspections."""

    tool_name: str
    changes: dict
    is_breaking: bool


class ServerResponse(BaseModel):
    """Full server representation returned by the API."""

    id: UUID
    name: str
    endpoint: str
    owner_team: str | None = None
    description: str | None = None
    labels: list[str]
    trust_level: str
    health_status: str
    version: str | None = None
    team_namespace: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    decommissioned_at: datetime | None = None
    tools: list[ToolResponse] = []

    model_config = {"from_attributes": True}


class ServerInspectResponse(ServerResponse):
    """Server response enriched with diff of tool changes since last inspect."""

    tools_added: list[ToolResponse] = []
    tools_removed: list[ToolResponse] = []
    tools_changed: list[ToolChange] = []


class ToolVersionResponse(BaseModel):
    """A historical snapshot of a tool's schema."""

    id: UUID
    tool_name: str
    input_schema: dict
    output_schema: dict | None = None
    is_breaking: bool
    detected_at: datetime

    model_config = {"from_attributes": True}


class RoutingRuleResponse(BaseModel):
    """A priority-ordered routing rule for capability dispatch."""

    id: UUID
    capability_id: UUID
    server_id: UUID
    priority: int = 0
    condition: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DecommissionTimeline(BaseModel):
    """Decommission status and phase timeline for a server."""

    phase: str | None = None
    decommissioned_at: datetime | None = None
    status: str = "active"


class ServerDetail(ServerResponse):
    """Full server detail with all related entities eagerly loaded."""

    tool_versions: list[ToolVersionResponse] = []
    trust_assignments: list[TrustAssignmentResponse] = []
    capability_mappings: list[CapabilityMappingResponse] = []
    routing_rules: list[RoutingRuleResponse] = []
    decommission_timeline: DecommissionTimeline | None = None


class DecommissionRequest(BaseModel):
    """Request body for decommissioning an MCP server."""

    phase: str = Field(pattern=r"^(grace_period|migration|sunset)$")
    replacement_id: UUID | None = None


class DependencyReport(BaseModel):
    """Entities that depend on a server targeted for decommission."""

    capability_names: list[str] = []
    agent_class_names: list[str] = []
    trust_assignment_count: int = 0
    mapping_count: int = 0


class DecommissionResult(BaseModel):
    """Result of a decommission operation with before-state report."""

    server_id: UUID
    phase: str
    dependencies: DependencyReport
    timeline: DecommissionTimeline | None = None


ServerDetail.model_rebuild()
RoutingRuleResponse.model_rebuild()
ToolVersionResponse.model_rebuild()
