"""Pack management routes.

Endpoints: POST /v1/packs, GET /v1/packs, GET /v1/packs/{id}, PUT /v1/packs/{id},
DELETE /v1/packs/{id}, POST /v1/packs/{id}/capabilities, POST /v1/packs/{id}/clone,
GET /v1/packs/{id}/usage.
"""

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


@router.post("", status_code=201)
async def create_pack(
    body: PackCreate,
    svc: PackService = Depends(get_pack_service),
) -> PackResponse:
    """Create a new pack. Returns 201 with the created pack."""
    return await svc.create_pack(body)


@router.get("")
async def list_packs(
    team_namespace: str | None = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    svc: PackService = Depends(get_pack_service),
) -> list[PackResponse]:
    """List packs, optionally filtered by team namespace."""
    return await svc.list_packs(team_namespace=team_namespace, limit=limit, offset=offset)


@router.get("/{pack_id}")
async def get_pack(
    pack_id: UUID,
    svc: PackService = Depends(get_pack_service),
) -> PackResponse:
    """Get a single pack by ID. Returns 404 if not found."""
    try:
        return await svc.get_pack(pack_id)
    except PackNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": str(exc)},
        ) from exc


@router.put("/{pack_id}")
async def update_pack(
    pack_id: UUID,
    body: PackCreate,
    svc: PackService = Depends(get_pack_service),
) -> PackResponse:
    """Update an existing pack. Returns 404 if not found."""
    try:
        return await svc.update_pack(pack_id, body)
    except PackNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": str(exc)},
        ) from exc


@router.delete("/{pack_id}", status_code=204)
async def delete_pack(
    pack_id: UUID,
    svc: PackService = Depends(get_pack_service),
) -> None:
    """Delete a pack by ID. Returns 404 if not found, 204 on success."""
    try:
        await svc.delete_pack(pack_id)
    except PackNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": str(exc)},
        ) from exc


@router.post("/{pack_id}/capabilities", status_code=201)
async def assign_capability(
    pack_id: UUID,
    body: PackAssignmentRequest,
    svc: PackService = Depends(get_pack_service),
) -> PackResponse:
    """Assign a capability to a pack. Returns 404 if the pack is not found."""
    try:
        await svc.assign_capability(pack_id, body)
        return await svc.get_pack(pack_id)
    except PackNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": str(exc)},
        ) from exc


@router.post("/{pack_id}/clone", status_code=201)
async def clone_pack(
    pack_id: UUID,
    body: ClonePackRequest,
    svc: PackService = Depends(get_pack_service),
) -> PackResponse:
    """Clone an existing pack with a new name. Returns 404 if source pack not found."""
    try:
        return await svc.clone_pack(pack_id, body)
    except PackNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": str(exc)},
        ) from exc


@router.get("/{pack_id}/usage")
async def get_pack_usage(
    pack_id: UUID,
    svc: PackService = Depends(get_pack_service),
) -> dict:
    """Return usage statistics for a pack. Returns 404 if not found."""
    try:
        return await svc.get_usage_stats(pack_id)
    except PackNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": str(exc)},
        ) from exc


@router.delete("/{pack_id}/classes/{class_id}", status_code=204)
async def remove_pack_from_class(
    pack_id: UUID,
    class_id: UUID,
    svc: PackService = Depends(get_pack_service),
) -> None:
    """Remove a pack assignment from an agent class. Returns 204 on success."""
    await svc.remove_from_class(pack_id, class_id)
