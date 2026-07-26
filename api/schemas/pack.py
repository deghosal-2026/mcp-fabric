"""Pydantic schemas for capability pack CRUD and assignment.

Endpoints:
  POST /api/v1/packs                    -> PackCreate -> PackResponse
  GET  /api/v1/packs                    -> list[PackResponse]
  GET  /api/v1/packs/{id}               -> PackResponse
  POST /api/v1/packs/{id}/assignments   -> PackAssignmentRequest
  POST /api/v1/packs/{id}/clone         -> ClonePackRequest -> PackResponse
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PackCreate(BaseModel):
    """Request body for creating a new capability pack (POST /api/v1/packs).

    name is required (1-255 chars). description and team_namespace are
    optional. A capability pack is initially empty; capabilities are added
    via PackAssignmentRequest.
    """

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    team_namespace: str | None = None


class PackResponse(BaseModel):
    """Capability pack representation returned by the API.

    model_config = {"from_attributes": True} for ORM conversion.

    Includes computed aggregate fields:
      - capabilities_count: number of capabilities in the pack (for list view).
      - classes_count:      number of agent classes assigned to this pack.
    """

    id: UUID
    name: str
    description: str | None = None
    team_namespace: str | None = None
    created_at: datetime
    capabilities_count: int = 0
    classes_count: int = 0

    model_config = {"from_attributes": True}


class PackAssignmentRequest(BaseModel):
    """Request body for assigning a capability to a pack.

    POST /api/v1/packs/{id}/assignments

    This creates a PackAssignment junction row linking the pack to the
    capability. Only the capability_id is needed; the pack_id comes from
    the URL path parameter.
    """

    capability_id: UUID


class PackSecurityMetricsResponse(BaseModel):
    id: UUID
    name: str
    resource_count: int = 0
    total_resources_in_domain: int = 0
    implied_catch_rate: float = 1.0
    warning_tier: str = "none"

    model_config = {"from_attributes": True}


class ClonePackRequest(BaseModel):
    """Request body for cloning an existing capability pack.

    POST /api/v1/packs/{id}/clone

    Creates a new pack with the given name, copying all capability assignments
    from the source pack. The new pack is independent — changes to the clone
    do not affect the original.
    """

    name: str = Field(min_length=1, max_length=255)
