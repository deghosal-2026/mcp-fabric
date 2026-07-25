"""Pydantic schemas for resource-dimension policy constraints.

Endpoints (v0.2.0):
  POST /admin/capabilities/{id}/dimensions
      -> ResourceDimensionCreate -> ResourceDimensionResponse
  GET /admin/capabilities/{id}/dimensions
      -> list[ResourceDimensionResponse]
  DELETE /admin/capabilities/{id}/dimensions/{dim_id}
  POST /admin/capabilities/{id}/dimensions/{dim_id}/value-map
      -> DimensionValueMapCreate -> DimensionValueMapResponse
  POST /admin/agents/{identity_id}/resources
      -> ResourceBindingBulkRequest
  GET /admin/agents/{identity_id}/resources
      -> list[ResourceBindingResponse]
  DELETE /admin/agents/{identity_id}/resources/{binding_id}
  POST /admin/packs/{pack_id}/resources
      -> ResourceBindingBulkRequest
  GET /admin/packs/{pack_id}/resources
      -> list[ResourceBindingResponse]
  DELETE /admin/packs/{pack_id}/resources/{binding_id}
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ResourceDimensionCreate(BaseModel):
    """Request body for declaring a resource dimension on a capability.

    POST /admin/capabilities/{id}/dimensions

    Fields:
        dimension_key – Machine-readable key, lowercase with underscores
                        (e.g. ``env``, ``tenant``, ``service``).
        display_name  – Optional human-readable label.
    """

    dimension_key: str = Field(min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    display_name: str | None = Field(default=None, max_length=255)


class ResourceDimensionResponse(BaseModel):
    """A resource dimension as returned by the API."""

    id: UUID
    capability_id: UUID
    dimension_key: str
    display_name: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DimensionValueMapCreate(BaseModel):
    """Request body for setting a param-to-dimension value mapping.

    POST /admin/capabilities/{id}/dimensions/{dim_id}/value-map

    Fields:
        source – ``param`` to extract from request params, or ``constant``
                 for a fixed value.
        param_path – JSON path within params (e.g. ``params.deploy.env``).
                     Required when source is ``param``.
        constant_value – Fixed value. Required when source is ``constant``.
    """

    source: str = Field(default="param", pattern=r"^(param|constant)$")
    param_path: str | None = Field(default=None, max_length=255)
    constant_value: str | None = Field(default=None, max_length=255)


class DimensionValueMapResponse(BaseModel):
    """A param-to-dimension mapping as returned by the API."""

    id: UUID
    resource_dimension_id: UUID
    source: str
    param_path: str | None = None
    constant_value: str | None = None

    model_config = {"from_attributes": True}


class ResourceBindingValue(BaseModel):
    """A single allowed resource value for a dimension.

    Used in bulk request/response for agent identity and pack bindings.
    """

    dimension_key: str = Field(min_length=1, max_length=100)
    allowed_value: str = Field(min_length=1, max_length=255)


class ResourceBindingBulkRequest(BaseModel):
    """Bulk set resource bindings for an agent identity or pack.

    POST /admin/agents/{identity_id}/resources
    POST /admin/packs/{pack_id}/resources

    This replaces all existing bindings atomically.
    """

    bindings: list[ResourceBindingValue] = Field(default_factory=list)


class ResourceBindingResponse(BaseModel):
    """A single resource binding as returned by the API."""

    id: UUID
    agent_identity_id: UUID | None = None
    pack_id: UUID | None = None
    dimension_key: str
    allowed_value: str
    created_at: datetime

    model_config = {"from_attributes": True}
