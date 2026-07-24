from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import get_registry_service
from api.schemas.common import PaginatedServers
from api.schemas.server import (
    DecommissionRequest,
    DecommissionResult,
    ServerCreate,
    ServerDetail,
    ServerInspectResponse,
    ServerResponse,
)
from api.services import (
    DecommissionError,
    DuplicateServerError,
    RegistryService,
    ServerNotFoundError,
    ServerUnreachableError,
)

router = APIRouter(prefix="/v1/servers", tags=["servers"])


@router.post("", status_code=201)
async def register_server(
    body: ServerCreate,
    svc: RegistryService = Depends(get_registry_service),
) -> ServerResponse:
    try:
        return await svc.register(body)
    except DuplicateServerError as exc:
        raise HTTPException(
            status_code=409,
            detail={"error": "duplicate", "message": str(exc)},
        ) from exc
    except ServerUnreachableError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": "unreachable", "message": str(exc)},
        ) from exc


@router.get("")
async def list_servers(
    team: str | None = Query(None),
    trust: str | None = Query(None),
    health: str | None = Query(None),
    q: str | None = Query(None, alias="q"),
    cursor: str | None = Query(None),
    per_page: int = Query(20, le=100),
    svc: RegistryService = Depends(get_registry_service),
) -> PaginatedServers:
    return await svc.list_servers(
        team=team, trust=trust, health=health,
        search=q, cursor=cursor, per_page=per_page,
    )


@router.get("/{server_id}")
async def get_server(
    server_id: UUID,
    svc: RegistryService = Depends(get_registry_service),
) -> ServerDetail:
    try:
        return await svc.get_server(server_id)
    except ServerNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": str(exc)},
        ) from exc


@router.post("/{server_id}/inspect")
async def inspect_server(
    server_id: UUID,
    svc: RegistryService = Depends(get_registry_service),
) -> ServerInspectResponse:
    try:
        return await svc.inspect(server_id)
    except ServerNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": str(exc)},
        ) from exc
    except ServerUnreachableError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": "unreachable", "message": str(exc)},
        ) from exc


@router.post("/{server_id}/decommission")
async def decommission_server(
    server_id: UUID,
    body: DecommissionRequest,
    svc: RegistryService = Depends(get_registry_service),
) -> DecommissionResult:
    try:
        return await svc.decommission(
            server_id=server_id,
            phase=body.phase,
            replacement_id=body.replacement_id,
        )
    except ServerNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": str(exc)},
        ) from exc
    except DecommissionError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": "decommission_error", "message": str(exc)},
        ) from exc
