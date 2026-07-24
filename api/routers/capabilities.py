from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db_session
from api.schemas.capability import (
    CapabilityCreate,
    CapabilityMappingCreate,
    CapabilityMappingResponse,
    CapabilityResponse,
)
from api.services.capability_service import CapabilityService

router = APIRouter(prefix="/v1/capabilities", tags=["capabilities"])


async def get_capability_service(
    db: AsyncSession = Depends(get_db_session),
) -> CapabilityService:
    return CapabilityService(db=db)


@router.post("", status_code=201)
async def create_capability(
    body: CapabilityCreate,
    svc: CapabilityService = Depends(get_capability_service),
) -> CapabilityResponse:
    return await svc.create(body)


@router.get("")
async def list_capabilities(
    domain: str | None = Query(None),
    svc: CapabilityService = Depends(get_capability_service),
) -> list[CapabilityResponse]:
    return await svc.list(domain=domain)


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


@router.post("/{capability_id}/mappings", status_code=201)
async def map_capability(
    capability_id: UUID,
    body: CapabilityMappingCreate,
    db: AsyncSession = Depends(get_db_session),
) -> CapabilityMappingResponse:
    from api.models.server import CapabilityMapping

    mapping = CapabilityMapping(
        capability_id=capability_id,
        server_id=body.server_id,
        tool_name=body.tool_name,
        input_mapping=body.input_mapping,
        output_mapping=body.output_mapping,
        is_primary=body.is_primary,
    )
    db.add(mapping)
    await db.commit()
    await db.refresh(mapping)
    return CapabilityMappingResponse(
        id=mapping.id,
        capability_id=mapping.capability_id,
        server_id=mapping.server_id,
        tool_name=mapping.tool_name,
        input_mapping=mapping.input_mapping,
        output_mapping=mapping.output_mapping,
        is_primary=mapping.is_primary,
        routing_weight=mapping.routing_weight,
    )
