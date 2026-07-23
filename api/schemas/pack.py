"""Pydantic schemas for capability pack CRUD and assignment."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PackCreate(BaseModel):
    """Request body for creating a new capability pack."""


    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    team_namespace: str | None = None


class PackResponse(BaseModel):
    """Capability pack representation returned by the API."""

    id: UUID
    name: str
    description: str | None = None
    team_namespace: str | None = None
    created_at: datetime
    capabilities_count: int = 0
    classes_count: int = 0

    model_config = {"from_attributes": True}


class PackAssignmentRequest(BaseModel):
    """Request body for assigning a capability to a pack."""

    capability_id: UUID


class ClonePackRequest(BaseModel):
    """Request body for cloning an existing capability pack."""

    name: str = Field(min_length=1, max_length=255)
