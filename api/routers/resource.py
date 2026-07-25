"""Resource-dimension policy management routes (v0.2.0).

Manages resource dimensions on capabilities, param-to-value mappings,
and resource bindings for agent identities and capability packs.

Endpoints:
  POST   /admin/capabilities/{capability_id}/dimensions
  GET    /admin/capabilities/{capability_id}/dimensions
  DELETE /admin/capabilities/{capability_id}/dimensions/{dim_id}
  POST   /admin/capabilities/{capability_id}/dimensions/{dim_id}/value-map
  POST   /admin/agents/{identity_id}/resources
  GET    /admin/agents/{identity_id}/resources
  DELETE /admin/agents/{identity_id}/resources/{binding_id}
  POST   /admin/packs/{pack_id}/resources
  GET    /admin/packs/{pack_id}/resources
  DELETE /admin/packs/{pack_id}/resources/{binding_id}
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db_session
from api.schemas.resource import (
    DimensionValueMapCreate,
    DimensionValueMapResponse,
    ResourceBindingBulkRequest,
    ResourceBindingResponse,
    ResourceDimensionCreate,
    ResourceDimensionResponse,
)
from api.services.resource_service import ResourceNotFoundError, ResourceService

router = APIRouter(prefix="/admin", tags=["resource-policy"])


async def get_resource_service(
    db: AsyncSession = Depends(get_db_session),
) -> ResourceService:
    return ResourceService(db=db)


@router.post("/capabilities/{capability_id}/dimensions", status_code=201)
async def create_dimension(
    capability_id: UUID,
    body: ResourceDimensionCreate,
    svc: ResourceService = Depends(get_resource_service),
) -> ResourceDimensionResponse:
    return await svc.create_dimension(capability_id, body)


@router.get("/capabilities/{capability_id}/dimensions")
async def list_dimensions(
    capability_id: UUID,
    svc: ResourceService = Depends(get_resource_service),
) -> list[ResourceDimensionResponse]:
    return await svc.list_dimensions(capability_id)


@router.delete("/capabilities/{capability_id}/dimensions/{dim_id}", status_code=204)
async def delete_dimension(
    capability_id: UUID,
    dim_id: UUID,
    svc: ResourceService = Depends(get_resource_service),
) -> None:
    try:
        await svc.delete_dimension(dim_id)
    except ResourceNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": str(exc)},
        ) from exc


@router.post(
    "/capabilities/{capability_id}/dimensions/{dim_id}/value-map",
    status_code=201,
)
async def set_value_map(
    capability_id: UUID,
    dim_id: UUID,
    body: DimensionValueMapCreate,
    svc: ResourceService = Depends(get_resource_service),
) -> DimensionValueMapResponse:
    try:
        return await svc.set_value_map(dim_id, body)
    except ResourceNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": str(exc)},
        ) from exc


@router.post("/agents/{identity_id}/resources", status_code=200)
async def set_identity_bindings(
    identity_id: UUID,
    body: ResourceBindingBulkRequest,
    svc: ResourceService = Depends(get_resource_service),
) -> list[ResourceBindingResponse]:
    return await svc.set_identity_bindings(identity_id, body)


@router.get("/agents/{identity_id}/resources")
async def list_identity_bindings(
    identity_id: UUID,
    svc: ResourceService = Depends(get_resource_service),
) -> list[ResourceBindingResponse]:
    return await svc.list_identity_bindings(identity_id)


@router.delete("/agents/{identity_id}/resources/{binding_id}", status_code=204)
async def delete_identity_binding(
    identity_id: UUID,
    binding_id: UUID,
    svc: ResourceService = Depends(get_resource_service),
) -> None:
    try:
        await svc.delete_identity_binding(binding_id)
    except ResourceNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": str(exc)},
        ) from exc


@router.post("/packs/{pack_id}/resources", status_code=200)
async def set_pack_bindings(
    pack_id: UUID,
    body: ResourceBindingBulkRequest,
    svc: ResourceService = Depends(get_resource_service),
) -> list[ResourceBindingResponse]:
    return await svc.set_pack_bindings(pack_id, body)


@router.get("/packs/{pack_id}/resources")
async def list_pack_bindings(
    pack_id: UUID,
    svc: ResourceService = Depends(get_resource_service),
) -> list[ResourceBindingResponse]:
    return await svc.list_pack_bindings(pack_id)


@router.delete("/packs/{pack_id}/resources/{binding_id}", status_code=204)
async def delete_pack_binding(
    pack_id: UUID,
    binding_id: UUID,
    svc: ResourceService = Depends(get_resource_service),
) -> None:
    try:
        await svc.delete_pack_binding(binding_id)
    except ResourceNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": str(exc)},
        ) from exc
