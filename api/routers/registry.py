"""MCP server registry routes.

Manages the lifecycle of registered MCP servers: registration, discovery,
inspection, and decommissioning. The registry is the source of truth for
which MCP servers are available, their capabilities, health status, and
trust level.

User journeys:
  - Admin registers a new MCP server (POST /v1/servers) — the system probes
    the server's /health and /capabilities endpoints to validate connectivity
  - Dashboard lists all servers with filters (team, trust level, health status)
    and cursor-based pagination (GET /v1/servers)
  - Admin inspects a server's current capabilities and health (POST .../inspect)
  - Admin decommissions a server with optional graceful drain and replacement
    (POST .../decommission)

Architectural notes:
  - Registration probes the server (connectivity check) and blocks the request
    until the probe completes or times out. This means POST /v1/servers is
    not instant — it waits for the server to respond.
  - The inspect endpoint is a POST (not GET) because it triggers a live probe.
    It's not idempotent — each call makes a network request to the server.
  - Decommission supports a two-phase process: drain (stop new routing) then
    remove. The `replacement_id` field allows seamless migration.

Endpoints: POST /v1/servers, GET /v1/servers, GET /v1/servers/{id},
POST /v1/servers/{id}/inspect, POST /v1/servers/{id}/decommission.
"""

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


# Register a new MCP server by URL. This endpoint probes the server to verify
# it's reachable and supports the MCP protocol. 409 = a server with the same
# URL is already registered (idempotency guard). 400 = server unreachable or
# doesn't speak MCP. 201 = registered successfully.
# NOTE: Registration blocks until the probe completes (or times out). For
# servers behind firewalls or on slow networks, this could take several seconds.
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


# List registered servers with optional filters and cursor-based pagination.
# Filters: team (namespace), trust level, health status, and free-text search.
# Cursor-based pagination (not offset-based) for stable pagination across
# result sets that may change between requests. `per_page` capped at 100.
# The `q` parameter uses the `alias` keyword because FastAPI's Query() shadows
# the variable if named `q` without the alias workaround.
@router.get("")
async def list_servers(
    team: str | None = Query(None, alias="team_namespace"),
    trust: str | None = Query(None, alias="trust_level"),
    health: str | None = Query(None, alias="health_status"),
    q: str | None = Query(None, alias="q"),
    cursor: str | None = Query(None),
    per_page: int = Query(20, le=200),
    svc: RegistryService = Depends(get_registry_service),
) -> PaginatedServers:
    return await svc.list_servers(
        team=team,
        trust=trust,
        health=health,
        search=q,
        cursor=cursor,
        per_page=per_page,
    )


# Get a single server's detail by ID. Returns the server's metadata,
# registered capabilities, and last-known health status — but does NOT
# trigger a live probe (use POST /inspect for that). 404 if not found.
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


# Trigger a live inspection of a server's health and capabilities.
# This is a POST (not GET) because it has side effects: it makes network
# calls to the server and may update the server's health status in the DB.
# 404 = server not registered. 400 = server unreachable or misconfigured.
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


# Decommission a server with optional graceful phase control.
# Supports a two-phase decommission:
#   phase="drain" — stop routing new requests to this server (existing
#     connections complete normally)
#   phase="remove" — remove the server from the registry entirely
# The `replacement_id` field supports seamless migration: if provided,
# the system can automatically update capability mappings to point to the
# replacement server instead. 400 = decommission failed (e.g. phase conflict).
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
