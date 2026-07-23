"""Pydantic schemas for agent classes, identities, trust, and connect.

Covers CRUD for agent classes/identities and the agent connect
handshake that returns the capability surface.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AgentClassCreate(BaseModel):
    """Request body for creating a new agent class."""


    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    team_namespace: str | None = None


class AgentClassResponse(BaseModel):
    """Agent class representation returned by the API."""

    id: UUID
    name: str
    description: str | None = None
    team_namespace: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentIdentityCreate(BaseModel):
    """Request body for creating a new agent identity."""

    name: str = Field(min_length=1, max_length=255)
    agent_class_id: UUID
    rate_limit_per_min: int = Field(default=100, ge=1, le=10000)
    expires_at: datetime | None = None


class AgentIdentityResponse(BaseModel):
    """Agent identity representation (includes raw token on creation)."""

    id: UUID
    name: str
    agent_class_id: UUID
    token_prefix: str | None = None
    status: str
    rate_limit_per_min: int = 100
    expires_at: datetime | None = None
    created_at: datetime
    token: str | None = None

    model_config = {"from_attributes": True}


class AgentConnectResponse(BaseModel):
    """Response returned to an agent after successful authentication."""

    agent_id: UUID
    agent_class: str
    capability_surface: list[str] = []


class CapabilitySurfaceItem(BaseModel):
    """A single capability visible to an agent with trust metadata."""

    name: str
    normalized_input_schema: dict | None = None
    normalized_output_schema: dict | None = None
    trust_level: str
    approval_required: bool = False
    deprecated: bool = False
    migration_guidance: str | None = None


class TrustAssignmentCreate(BaseModel):
    """Request body for setting trust between an agent class and server."""

    server_id: UUID
    trust_level: str = Field(pattern=r"^(trusted|restricted|approval-gated|unreviewed)$")
    tool_scope: list[str] | None = None


class TrustAssignmentResponse(BaseModel):
    """Trust assignment as returned by the API."""

    id: UUID
    agent_class_id: UUID
    server_id: UUID
    trust_level: str
    tool_scope: list[str] | None = None

    model_config = {"from_attributes": True}
