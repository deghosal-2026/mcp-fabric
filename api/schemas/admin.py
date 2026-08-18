"""Pydantic schemas for admin user management.

Used by endpoints:
  POST   /api/v1/admin/invite          -> AdminUserInvite (request)
  GET    /api/v1/admin/users/{id}      -> AdminUserResponse (response)
  PATCH  /api/v1/admin/users/{id}      -> AdminUserUpdate (request)
  GET    /api/v1/admin/users           -> list[AdminUserResponse] (response)
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AdminUserInvite(BaseModel):
    """Request body for inviting a new admin user (POST /api/v1/admin/invite).

    Validation:
        role must be one of: 'admin', 'editor', 'viewer' (regex enforced).
        team_namespace is optional; if omitted the user is global.

    model_config: Not needed — this is a pure input schema, not ORM-backed.
    """

    email: str
    role: str = Field(pattern=r"^(admin|editor|viewer)$")
    team_namespace: str | None = None


class AdminUserResponse(BaseModel):
    """Admin user representation returned by the API (response schema).

    model_config = {"from_attributes": True} enables SQLAlchemy ORM instance
    -> Pydantic conversion (used by FastAPI's ORM mode).

    Fields match the AdminUser ORM model but exclude sensitive data like
    password_hash, mfa_secret, and recovery_codes.
    """

    id: UUID
    username: str
    email: str
    role: str
    team_namespace: str | None = None
    mfa_enabled: bool = False
    status: str
    last_login_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminUserUpdate(BaseModel):
    """Request body for updating an admin user (PATCH /api/v1/admin/users/{id}).

    All fields are optional (partial update). role is validated against the
    regex if provided. Setting team_namespace to None clears it.
    """

    role: str | None = Field(default=None, pattern=r"^(admin|editor|viewer)$")
    team_namespace: str | None = None


class PackBreadthRow(BaseModel):
    """Per-agent-class pack breadth summary for the Trust Posture dashboard."""

    agent_class_id: UUID
    agent_class_name: str
    pack_count: int
    resources_covered: int
    total_resources_in_domain: int
    catch_rate: float


class PackCohesionRow(BaseModel):
    """Per-pack cohesion score for the Trust Posture dashboard.

    Independent of breadth: two packs of the same size can have opposite
    adversarial exposure depending on how tightly their members cluster.
    """

    pack_id: UUID
    pack_name: str
    resource_count: int
    cohesion_score: float
    is_semantic_band: bool
