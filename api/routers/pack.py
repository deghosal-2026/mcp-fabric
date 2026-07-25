"""Pack management routes.

Packs are named collections of capabilities that can be assigned to agent
classes as a group. They simplify permission management: instead of assigning
individual capabilities to each agent class, admins define a pack (e.g.
"data-analytics", "email-operations") and assign it to the relevant classes.

User journeys:
  - Admin defines a new pack with a name, description, and team namespace
    (POST /v1/packs)
  - Admin assigns capabilities to a pack (POST /v1/packs/{id}/capabilities)
  - Admin clones a pack to create a variant (POST /v1/packs/{id}/clone) —
    useful for creating team-specific forks
  - Admin deletes a pack (DELETE /v1/packs/{id}) — only succeeds if no
    agent classes are currently using it
  - Dashboard lists packs filtered by team namespace (GET /v1/packs)

Architectural notes:
  - Packs are soft-linked to capabilities (assignment records, not copies).
    Modifying a capability in one pack affects all packs that include it.
  - The clone endpoint deep-copies the pack metadata but references the
    same capability assignments — cloned packs are independent snapshots.
  - Usage stats (GET /v1/packs/{id}/usage) returns which agent classes
    are currently assigned this pack, for impact analysis before deletion.

Endpoints: POST /v1/packs, GET /v1/packs, GET /v1/packs/{id}, PUT /v1/packs/{id},
DELETE /v1/packs/{id}, POST /v1/packs/{id}/capabilities, POST /v1/packs/{id}/clone,
GET /v1/packs/{id}/usage.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import get_pack_service
from api.schemas.pack import (
    ClonePackRequest,
    PackAssignmentRequest,
    PackCreate,
    PackResponse,
)
from api.services.pack_service import PackNotFoundError, PackService

router = APIRouter(prefix="/v1/packs", tags=["packs"])


# Create a new pack. 201 = resource created. Packs start empty — capabilities
# must be assigned via POST /{pack_id}/capabilities after creation.
@router.post("", status_code=201)
async def create_pack(
    body: PackCreate,
    svc: PackService = Depends(get_pack_service),
) -> PackResponse:
    return await svc.create_pack(body)


# List packs, with optional team namespace filter and pagination.
# The `limit` is capped at 100 to prevent unbounded result sets.
# `offset`-based pagination is used for simplicity; cursor-based would
# be better at scale but is not yet implemented.
@router.get("")
async def list_packs(
    team_namespace: str | None = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    svc: PackService = Depends(get_pack_service),
) -> list[PackResponse]:
    return await svc.list_packs(team_namespace=team_namespace, limit=limit, offset=offset)


# Get a single pack by ID with its full capability list.
# Used by the pack detail view and by agent class editors when selecting
# which packs to assign. Returns 404 if the pack does not exist.
@router.get("/{pack_id}")
async def get_pack(
    pack_id: UUID,
    svc: PackService = Depends(get_pack_service),
) -> PackResponse:
    try:
        return await svc.get_pack(pack_id)
    except PackNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": str(exc)},
        ) from exc


# Full replacement of a pack's metadata (name, description, team).
# PUT is used (not PATCH) because the schema requires all fields.
# Returns 404 if the pack does not exist.
@router.put("/{pack_id}")
async def update_pack(
    pack_id: UUID,
    body: PackCreate,
    svc: PackService = Depends(get_pack_service),
) -> PackResponse:
    try:
        return await svc.update_pack(pack_id, body)
    except PackNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": str(exc)},
        ) from exc


# Delete a pack. Returns 204 with no body on success (standard for DELETE).
# The service layer may reject deletion if the pack is still assigned
# to active agent classes (referential integrity check).
@router.delete("/{pack_id}", status_code=204)
async def delete_pack(
    pack_id: UUID,
    svc: PackService = Depends(get_pack_service),
) -> None:
    try:
        await svc.delete_pack(pack_id)
    except PackNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": str(exc)},
        ) from exc


# Assign one or more capabilities to a pack.
# After assigning, the full updated pack is returned so the caller can
# confirm the new state. 404 if the pack doesn't exist.
# NOTE: This calls assign_capability then re-fetches get_pack — two service
# calls. This could be optimized with a single "assign and return" method.
@router.post("/{pack_id}/capabilities", status_code=201)
async def assign_capability(
    pack_id: UUID,
    body: PackAssignmentRequest,
    svc: PackService = Depends(get_pack_service),
) -> PackResponse:
    try:
        await svc.assign_capability(pack_id, body)
        return await svc.get_pack(pack_id)
    except PackNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": str(exc)},
        ) from exc


# Clone an existing pack with a new name. Deep-copies the pack metadata
# and capability assignments, creating an independent pack. Useful for
# creating team-specific variants (e.g. "data-analytics-eng" from
# "data-analytics"). 404 if the source pack doesn't exist.
@router.post("/{pack_id}/clone", status_code=201)
async def clone_pack(
    pack_id: UUID,
    body: ClonePackRequest,
    svc: PackService = Depends(get_pack_service),
) -> PackResponse:
    try:
        return await svc.clone_pack(pack_id, body)
    except PackNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": str(exc)},
        ) from exc


# Return usage statistics for a pack — primarily which agent classes are
# currently assigned this pack. Used by the admin UI to show impact analysis
# before deletion. Returns 404 if the pack doesn't exist.
@router.get("/{pack_id}/usage")
async def get_pack_usage(
    pack_id: UUID,
    svc: PackService = Depends(get_pack_service),
) -> dict[str, Any]:
    try:
        return await svc.get_usage_stats(pack_id)
    except PackNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": str(exc)},
        ) from exc


# Assign a pack to an agent class. This links the pack's capabilities
# to the agent class so its agents can use them. Returns 200 on success.
@router.post("/{pack_id}/classes")
async def assign_pack_to_class(
    pack_id: UUID,
    body: dict[str, Any],
    svc: PackService = Depends(get_pack_service),
) -> dict[str, Any]:
    class_id = UUID(body["agent_class_id"])
    await svc.assign_to_class(pack_id, class_id)
    return {"status": "assigned", "pack_id": str(pack_id), "class_id": str(class_id)}


# Remove a pack assignment from an agent class. This does NOT delete the
# pack itself — it only severs the assignment link. Returns 204 on success
# (the pack may still exist and be assigned to other classes).
@router.delete("/{pack_id}/classes/{class_id}", status_code=204)
async def remove_pack_from_class(
    pack_id: UUID,
    class_id: UUID,
    svc: PackService = Depends(get_pack_service),
) -> None:
    await svc.remove_from_class(pack_id, class_id)
