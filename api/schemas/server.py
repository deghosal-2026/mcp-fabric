"""Pydantic schemas for MCP server registration and inspection.

ServerCreate is the input; ServerResponse and ServerInspectResponse
are API output shapes with tool listings and change detection.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


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
