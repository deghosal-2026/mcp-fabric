"""Pydantic schemas for agent classes, identities, trust, and connect.

Endpoints:
  POST /api/v1/agent-classes              -> AgentClassCreate -> AgentClassResponse
  GET  /api/v1/agent-classes/{id}         -> AgentClassResponse
  POST /api/v1/agent-identities           -> AgentIdentityCreate -> AgentIdentityResponse (token!)
  GET  /api/v1/agent-identities/{id}      -> AgentIdentityResponse
  POST /api/v1/agent/connect              -> AgentConnectResponse (handshake)
  POST /api/v1/agent-classes/{id}/trust   -> TrustAssignmentCreate -> TrustAssignmentResponse
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AgentClassCreate(BaseModel):
    """Request body for creating a new agent class (POST /api/v1/agent-classes).

    name must be non-empty (max 255 chars) and should be a human-readable
    label like "code-reviewer" or "ci-pipeline".
    """

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    team_namespace: str | None = None


class AgentClassResponse(BaseModel):
    """Agent class representation returned by the API (response schema).

    model_config = {"from_attributes": True} enables auto-conversion from
    the AgentClass ORM model.
    """

    id: UUID
    name: str
    description: str | None = None
    team_namespace: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentIdentityCreate(BaseModel):
    """Request body for creating a new agent identity (POST /api/v1/agent-identities).

    On creation, the API generates a bearer token and returns it in the response.
    The raw token is only returned once — subsequent GET requests will not include it.

    Validation:
        name: 1-255 chars.
        agent_class_id: must reference an existing AgentClass.
        rate_limit_per_min: 1-10000 (default 100).
        expires_at: optional absolute expiry datetime.
    """

    name: str = Field(min_length=1, max_length=255)
    agent_class_id: UUID
    rate_limit_per_min: int = Field(default=100, ge=1, le=10000)
    expires_at: datetime | None = None


class AgentIdentityResponse(BaseModel):
    """Agent identity representation returned by the API (response schema).

    The `token` field is only populated on the initial creation response.
    Subsequent reads will return null for `token`. The `token_prefix` field
    shows the first few characters of the token to help admins identify it
    in the UI.

    model_config = {"from_attributes": True} for ORM conversion.
    """

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
    """Response returned after successful agent authentication (handshake).

    This is sent to the agent after it presents a valid bearer token:
      - agent_id: the identity UUID for audit/logging.
      - agent_class: the agent class name for the agent's own routing logic.
      - capability_surface: list of capability names this agent is allowed to invoke.
    """

    agent_id: UUID
    agent_class: str
    capability_surface: list[str] = []


class CapabilitySurfaceItem(BaseModel):
    """A single capability visible to an agent, with trust and deprecation metadata.

    Used in the agent connect response to give agents full context about each
    capability they're allowed to invoke, including:
      - Whether approval is required before invocation.
      - Whether the capability is deprecated and what migration guidance exists.
      - The normalized JSON Schemas for input/output validation.
    """

    name: str
    normalized_input_schema: dict | None = None
    normalized_output_schema: dict | None = None
    trust_level: str
    approval_required: bool = False
    deprecated: bool = False
    migration_guidance: str | None = None


class TrustAssignmentCreate(BaseModel):
    """Request body for setting trust between an agent class and an MCP server.

    POST /api/v1/agent-classes/{id}/trust

    trust_level is validated against known values:
        - trusted:            Direct execution, no approval.
        - restricted:         Allowed with tool-scope limits.
        - approval-gated:     Requires admin approval per invocation.
        - unreviewed:         Default; effectively no access.

    tool_scope is an optional list of tool names to restrict access to (e.g.
    ["review_code", "list_reviews"]). If None, all tools on the server are
    accessible at the given trust level.
    """

    server_id: UUID
    trust_level: str = Field(pattern=r"^(trusted|restricted|approval-gated|unreviewed)$")
    tool_scope: list[str] | None = None


class TrustAssignmentResponse(BaseModel):
    """Trust assignment as returned by the API.

    model_config = {"from_attributes": True} for ORM conversion.
    """

    id: UUID
    agent_class_id: UUID
    server_id: UUID
    trust_level: str
    tool_scope: list[str] | None = None

    model_config = {"from_attributes": True}
