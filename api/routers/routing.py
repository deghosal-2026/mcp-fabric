"""Capability routing and routing rule management routes.

Endpoints: POST /v1/capability/request, POST /v1/capability/batch,
POST /v1/routing-rules, GET /v1/routing-rules, DELETE /v1/routing-rules/{id}.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db_session
from api.mcp import MCPClient
from api.schemas.routing import (
    BatchCapabilityRequest,
    BatchResult,
    CapabilityRequest,
    RouteResult,
    RoutingRuleCreate,
)
from api.services.routing_service import (
    CapabilityNotFoundError,
    NoServerFoundError,
    RoutingService,
)

router = APIRouter(prefix="/v1/capability", tags=["routing"])


async def get_routing_service(
    db: AsyncSession = Depends(get_db_session),
) -> RoutingService:
    """Dependency that provides a RoutingService instance."""
    return RoutingService(db=db, mcp=MCPClient())


@router.post("/request")
async def capability_request(
    body: CapabilityRequest,
    svc: RoutingService = Depends(get_routing_service),
) -> RouteResult:
    """Execute a single capability request by routing to the appropriate server.

    Returns 404 if capability or server not found.
    """
    try:
        return await svc.execute(body)
    except CapabilityNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": str(exc)},
        ) from exc
    except NoServerFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "no_server", "message": str(exc)},
        ) from exc


@router.post("/batch")
async def capability_batch(
    body: BatchCapabilityRequest,
    svc: RoutingService = Depends(get_routing_service),
) -> BatchResult:
    """Execute multiple capability requests in a batch.

    Errors per request are captured in the results.
    """
    results: list[RouteResult | dict] = []
    for req in body.requests:
        try:
            result = await svc.execute(req)
            results.append(result)
        except Exception as exc:
            results.append({"capability": req.capability, "error": str(exc)})
    return BatchResult(results=results)


router_rules = APIRouter(prefix="/v1/routing-rules", tags=["routing-rules"])


@router_rules.post("", status_code=201)
async def create_routing_rule(
    body: RoutingRuleCreate,
    svc: RoutingService = Depends(get_routing_service),
) -> dict:
    """Create a new routing rule. Returns 201 with the rule details."""
    rule = await svc.create_routing_rule(body)
    return {
        "id": str(rule.id),
        "capability_id": str(rule.capability_id),
        "server_id": str(rule.server_id),
        "priority": rule.priority,
    }


@router_rules.get("")
async def list_routing_rules(
    svc: RoutingService = Depends(get_routing_service),
) -> list[dict]:
    """List all routing rules."""
    rules = await svc.list_routing_rules()
    return [
        {
            "id": str(r.id),
            "capability_id": str(r.capability_id),
            "server_id": str(r.server_id),
            "priority": r.priority,
        }
        for r in rules
    ]


@router_rules.delete("/{rule_id}", status_code=204)
async def delete_routing_rule(
    rule_id: UUID,
    svc: RoutingService = Depends(get_routing_service),
) -> None:
    """Delete a routing rule by ID. Returns 404 if not found, 204 on success."""
    deleted = await svc.delete_routing_rule(rule_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Routing rule not found"},
        )
