"""Pydantic schemas for MCP server registration, inspection, and decommission.

Endpoints:
  POST   /api/v1/servers                     -> ServerCreate -> ServerResponse
  GET    /api/v1/servers                     -> list[ServerResponse] (paginated)
  GET    /api/v1/servers/{id}                -> ServerDetail
  POST   /api/v1/servers/{id}/inspect        -> ServerInspectResponse
  GET    /api/v1/servers/{id}/tool-versions  -> list[ToolVersionResponse]
  GET    /api/v1/servers/{id}/routing-rules  -> list[RoutingRuleResponse]
  POST   /api/v1/servers/{id}/decommission   -> DecommissionRequest -> DecommissionResult
  GET    /api/v1/servers/{id}/dependencies   -> DependencyReport
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from api.schemas.agent import TrustAssignmentResponse
from api.schemas.capability import CapabilityMappingResponse


class ServerCreate(BaseModel):
    """Request body for registering a new MCP server (POST /api/v1/servers).

    Validation:
        name: 1-255 chars, human-readable.
        endpoint: Must start with http:// or https:// (regex enforced).
        owner_team: Optional team name for ownership tracking.
        description: Optional free-text description of what the server does.
        labels: Optional list of string labels for filtering/grouping (default []).
        team_namespace: Multi-tenant scope.

    Not set during creation (assigned by server-side logic):
        trust_level, health_status, version — default to 'unreviewed', 'unknown',
        and None respectively.
    """

    name: str = Field(min_length=1, max_length=255)
    endpoint: str = Field(pattern=r"^https?://")
    owner_team: str | None = None
    description: str | None = None
    labels: list[str] = []
    team_namespace: str | None = None


class ToolResponse(BaseModel):
    """A tool exposed by an MCP server, returned in server listings.

    model_config = {"from_attributes": True} for ORM conversion from ServerTool.

    Fields:
        id:            UUID of the ServerTool row.
        tool_name:     Name of the tool (e.g. "review_code").
        description:   What the tool does.
        input_schema:  JSON Schema describing expected input parameters.
        output_schema: JSON Schema describing the return value (nullable).
    """

    id: UUID
    tool_name: str
    description: str | None = None
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class ToolChange(BaseModel):
    """A detected change in a tool's schema between consecutive inspections.

    Produced by ServerInspectResponse when the fabric rescans a server and
    finds that a tool's schema differs from the stored version.

    Fields:
        tool_name:  Name of the tool that changed.
        changes:    JSON dict describing what changed (e.g. {"input_schema":
                    {"added_fields": ["new_param"], "removed_fields": []}}).
        is_breaking: True if the change is backward-incompatible (e.g. required
                     fields removed, parameter types changed).
    """

    tool_name: str
    changes: dict[str, Any]
    is_breaking: bool


class ServerResponse(BaseModel):
    """Full MCP server representation returned by the API.

    model_config = {"from_attributes": True} for ORM conversion.

    This is the default response shape for list and detail GET endpoints.
    Includes tool listing inline for convenience. The decommission fields
    (decommissioned_at) are null for active servers.

    Fields match the MCPServer ORM model plus:
        tools: List of ToolResponse objects for tools currently exposed.
    """

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
    """Server response enriched with a diff of tool changes since last inspect.

    Extends ServerResponse by adding three lists that describe what changed
    since the previous inspection:

        tools_added:   New tools discovered during this inspection.
        tools_removed: Tools that were present before but are now gone.
        tools_changed: Tools whose schemas have been modified, with details
                       about the changes (see ToolChange).

    This allows the admin UI to present a clear before/after diff after
    triggering a server re-scan.
    """

    tools_added: list[ToolResponse] = []
    tools_removed: list[ToolResponse] = []
    tools_changed: list[ToolChange] = []


class ToolVersionResponse(BaseModel):
    """A historical snapshot of a tool's schema at a point in time.

    model_config = {"from_attributes": True} for ORM conversion from ToolVersion.

    Used by GET /api/v1/servers/{id}/tool-versions to show the schema change
    history. Each row captures what the schema looked like at a specific
    inspection moment, along with whether the change was considered breaking.

    Fields:
        id:            UUID of the ToolVersion row.
        tool_name:     Name of the tool.
        input_schema:  The input schema as it was at the time of detection.
        output_schema: The output schema as it was at the time of detection.
        is_breaking:   Whether this version introduced a breaking change.
        detected_at:   When the change was detected during a rescan.
    """

    id: UUID
    tool_name: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None = None
    is_breaking: bool
    detected_at: datetime

    model_config = {"from_attributes": True}


class RoutingRuleResponse(BaseModel):
    """A routing rule for capability dispatch, as returned by the API.

    model_config = {"from_attributes": True} for ORM conversion from RoutingRule.

    Used by GET /api/v1/servers/{id}/routing-rules to show which capabilities
    route to this server and under what conditions.

    Fields:
        id:             UUID of the RoutingRule row.
        capability_id:  FK to the capability being routed.
        server_id:      FK to the target server.
        priority:       Evaluation order (lower = higher priority, default 0).
        condition:      Optional JSON condition for conditional routing.
        created_at:     When the rule was created.
    """

    id: UUID
    capability_id: UUID
    server_id: UUID
    priority: int = 0
    condition: dict[str, Any] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DecommissionTimeline(BaseModel):
    """Decommission status and phase timeline for a server.

    Not an ORM-backed schema — assembled from MCPServer fields.

    Fields:
        phase:             Current decommission phase: 'draining', 'completed',
                           or null if not decommissioning.
        decommissioned_at: Timestamp of full decommission (when phase='completed').
        status:            Computed status: 'active', 'decommissioning', or
                           'decommissioned'. Derived from phase and timestamps.
    """

    phase: str | None = None
    decommissioned_at: datetime | None = None
    status: str = "active"


class ServerDetail(ServerResponse):
    """Full server detail with all related entities eagerly loaded.

    Extends ServerResponse by including:
        tool_versions:        Historical schema change log (ToolVersion rows).
        trust_assignments:    Trust levels for each agent class on this server.
        capability_mappings:  Which capabilities are mapped to which tools.
        routing_rules:        How capabilities route to this server.
        decommission_timeline: Current decommission status.

    This is the response shape for GET /api/v1/servers/{id} (individual detail).
    It avoids N+1 queries by eager-loading all relationships in a single request.
    """

    tool_versions: list[ToolVersionResponse] = []
    trust_assignments: list[TrustAssignmentResponse] = []
    capability_mappings: list[CapabilityMappingResponse] = []
    routing_rules: list[RoutingRuleResponse] = []
    decommission_timeline: DecommissionTimeline | None = None


class DecommissionRequest(BaseModel):
    """Request body for initiating or advancing server decommission.

    POST /api/v1/servers/{id}/decommission

    phase must be one of:
        grace_period:  Entering decommission, with a grace period for migration.
        migration:     Active migration of dependent agents/capabilities.
        sunset:        Final phase — server is removed from the routing table.

    replacement_id is optional. If provided, it references the UUID of a
    replacement server that should handle this server's traffic after
    decommission completes.
    """

    phase: str = Field(pattern=r"^(grace_period|migration|sunset)$")
    replacement_id: UUID | None = None


class DependencyReport(BaseModel):
    """Entities that depend on a server targeted for decommission.

    Generated by GET /api/v1/servers/{id}/dependencies before decommissioning
    to help administrators understand the blast radius.

    Fields:
        capability_names:      Names of capabilities mapped to this server.
        agent_class_names:     Names of agent classes with trust assignments
                               pointing to this server.
        trust_assignment_count: Total number of trust assignments on this server.
        mapping_count:          Total number of capability mappings on this server.
    """

    capability_names: list[str] = []
    agent_class_names: list[str] = []
    trust_assignment_count: int = 0
    mapping_count: int = 0


class DecommissionResult(BaseModel):
    """Result of a decommission operation with a before-state dependency report.

    Returned by POST /api/v1/servers/{id}/decommission.

    Fields:
        server_id:    The UUID of the decommissioned server.
        phase:        The phase that was applied (grace_period, migration, sunset).
        dependencies: Snapshot of what depended on this server at the time of
                      decommission (for audit/reference).
        timeline:     Current decommission status and timestamps.
    """

    server_id: UUID
    phase: str
    dependencies: DependencyReport
    timeline: DecommissionTimeline | None = None


ServerDetail.model_rebuild()
RoutingRuleResponse.model_rebuild()
ToolVersionResponse.model_rebuild()
