"""Capability definition and mapping routes.

Capabilities are abstract function signatures (e.g. "send_email", "analyze_sentiment")
that decouple what an agent wants to do from which MCP server provides the tool.
This router manages capability CRUD, aliases, deprecation, and server mappings.

User journeys:
  - Admin defines a new capability (POST /v1/capabilities) — a named, versioned
    function signature with input/output schemas
  - Admin adds aliases so capabilities can be referenced by multiple names
    (POST /v1/capabilities/{id}/aliases) — useful for backwards compatibility
  - Admin maps a capability to a specific tool on an MCP server
    (POST /v1/capabilities/{id}/mappings) — the routing engine uses these
  - Admin deprecates old capabilities (POST /v1/capabilities/{id}/deprecate)
  - Dashboard lists all capabilities with optional domain filter (GET /v1/capabilities)

Architectural notes:
  - The /mappings endpoint creates CapabilityMapping records directly (not through
    the service layer) — an inconsistency that should be refactored.
  - Capability aliases provide polymorphic lookup: during routing, the system
    resolves the canonical capability by checking aliases.

Endpoints: POST /v1/capabilities, GET /v1/capabilities, GET /v1/capabilities/{id},
POST /v1/capabilities/{id}/aliases, POST /v1/capabilities/{id}/deprecate,
POST /v1/capabilities/{id}/mappings.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import get_capability_service
from api.schemas.capability import (
    CapabilityAliasCreate,
    CapabilityCreate,
    CapabilityMappingCreate,
    CapabilityMappingResponse,
    CapabilityResponse,
)
from api.services.capability_service import CapabilityService

# NOTE: get_capability_service from dependencies.py is the shared FastAPI
# dependency that injects a CapabilityService into route handlers. Using this
# shared dependency (rather than creating CapabilityService inline) ensures
# consistent lifecycle management and makes it easy to swap implementations
# during testing via dependency overrides.

router = APIRouter(prefix="/v1/capabilities", tags=["capabilities"])


# Create a new capability definition.
# 201 = resource created. Capabilities are the atomic units of function
# that agents request — each has a name, domain, version, and JSON schemas
# for input/output. No auth enforcement yet (v0.2 feature).
@router.post("", status_code=201)
async def create_capability(
    body: CapabilityCreate,
    svc: CapabilityService = Depends(get_capability_service),
) -> CapabilityResponse:
    return await svc.create(body)


# List all capabilities, optionally filtered by domain.
# The `domain` filter lets the frontend group capabilities by namespace
# (e.g. "communication", "analytics", "storage"). Returns an empty list
# when no capabilities exist or none match the filter.
@router.get("")
async def list_capabilities(
    domain: str | None = Query(None),
    status: str | None = Query(None),
    q: str | None = Query(None, alias="q"),
    per_page: int = Query(100, le=200, alias="per_page"),
    svc: CapabilityService = Depends(get_capability_service),
) -> dict[str, Any]:
    caps = await svc.list(domain=domain, status=status, search=q)
    return {
        "items": caps,
        "pagination": {
            "total": len(caps),
            "has_more": False,
            "per_page": per_page,
            "next_cursor": None,
        },
    }


# Get a single capability by ID. Returns 404 if the capability doesn't
# exist. Used by the capability detail view and also internally during
# routing to resolve capability schemas.
@router.get("/{capability_id}")
async def get_capability(
    capability_id: UUID,
    svc: CapabilityService = Depends(get_capability_service),
) -> CapabilityResponse:
    result = await svc.get(capability_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Capability not found"},
        )
    return result


# Add an alternative name (alias) for a capability.
# Aliases enable backwards-compatible renaming: old agents that request
# "send_email_v1" still resolve to the canonical capability "send_email".
# 404 if the capability doesn't exist; 201 on success.
@router.post("/{capability_id}/aliases", status_code=201)
async def add_capability_alias(
    capability_id: UUID,
    body: CapabilityAliasCreate,
    svc: CapabilityService = Depends(get_capability_service),
) -> CapabilityResponse:
    result = await svc.add_alias(capability_id, body.alias)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Capability not found"},
        )
    return result


# Mark a capability as deprecated. Deprecated capabilities remain in the
# system (existing mappings still work) but are excluded from new routing
# suggestions and may surface a warning in the dashboard. This is a soft
# delete — the capability is not actually removed.
@router.post("/{capability_id}/deprecate")
async def deprecate_capability(
    capability_id: UUID,
    svc: CapabilityService = Depends(get_capability_service),
) -> CapabilityResponse:
    result = await svc.deprecate(capability_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Capability not found"},
        )
    return result


# Create a mapping from a capability to a specific tool on an MCP server.
# This is the core linking mechanism: it says "capability X is provided by
# tool Y on server Z". Multiple servers can provide the same capability;
# the routing engine uses `is_primary` and `routing_weight` for load
# distribution.
# NOTE: This endpoint creates the mapping record directly (bypassing the
# CapabilityService) — an architectural inconsistency with the other
# endpoints. Future refactor should route through the service layer.
@router.post("/{capability_id}/mappings", status_code=201)
async def map_capability(
    capability_id: UUID,
    body: CapabilityMappingCreate,
    svc: CapabilityService = Depends(get_capability_service),
) -> CapabilityMappingResponse:
    return await svc.create_mapping(capability_id, body)
