"""Pydantic schemas for capability definition and mapping.

CapabilityCreate accepts the normalized name + schemas;
CapabilityMappingCreate links a capability to a server tool.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CapabilityCreate(BaseModel):
    """Request body for defining a new normalized capability."""


    name: str = Field(min_length=1, max_length=255, pattern=r"^[a-z]+:[a-z][a-z-]*$")
    domain: str | None = None
    normalized_input_schema: dict | None = None
    normalized_output_schema: dict | None = None
    description: str | None = None


class CapabilityResponse(BaseModel):
    """Full capability representation returned by the API."""

    id: UUID
    name: str
    domain: str | None = None
    normalized_input_schema: dict | None = None
    normalized_output_schema: dict | None = None
    description: str | None = None
    status: str
    deprecated_at: datetime | None = None
    grace_period_days: int = 14
    migration_guidance: str | None = None
    created_at: datetime
    mappings_count: int = 0
    aliases: list[str] = []

    model_config = {"from_attributes": True}


class CapabilityMappingCreate(BaseModel):
    """Request body for mapping a capability to a server tool."""

    server_id: UUID
    tool_name: str
    input_mapping: dict | None = None
    output_mapping: dict | None = None
    is_primary: bool = True


class CapabilityMappingResponse(BaseModel):
    """Capability-to-server mapping as returned by the API."""

    id: UUID
    capability_id: UUID
    server_id: UUID
    tool_name: str
    input_mapping: dict | None = None
    output_mapping: dict | None = None
    is_primary: bool = True
    routing_weight: float = 1.0

    model_config = {"from_attributes": True}
