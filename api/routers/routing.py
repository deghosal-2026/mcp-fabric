"""Capability routing and routing rule management routes.

This is the core execution engine: agents submit capability requests, and the
routing service determines which MCP server provides that capability, formats
the request according to the input mapping, executes it, and returns the result.
Also manages explicit routing rules that override the default resolution logic.

User journeys:
  - An agent sends a single capability request (POST /v1/capability/request) —
    the system resolves the capability to a server, calls the tool, and returns
    the result
  - An agent sends a batch of requests (POST /v1/capability/batch) — useful
    for workflows that need multiple capabilities simultaneously
  - Admin creates explicit routing rules (POST /v1/routing-rules) to pin a
    capability to a specific server (bypassing the default resolution)
  - Admin lists/deletes routing rules (GET/DELETE /v1/routing-rules)

Architectural notes:
  - The router uses two prefixes: /v1/capability for execution endpoints and
    /v1/routing-rules for rule management. This is because they serve different
    consumers (agents vs. admins) but are logically related.
  - The RoutingService instantiates an MCPClient() directly — a dependency
    injection improvement would allow swapping the client for testing.
  - Batch execution is sequential (requests execute one at a time). Parallel
    execution would improve throughput but introduces complexity around error
    isolation and rate limiting.

Endpoints: POST /v1/capability/request, POST /v1/capability/batch,
POST /v1/routing-rules, GET /v1/routing-rules, DELETE /v1/routing-rules/{id}.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
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
    PolicyDeniedError,
    ResourceDeniedError,
    RoutingService,
)

router = APIRouter(prefix="/v1/capability", tags=["routing"])


async def get_routing_service(
    db: AsyncSession = Depends(get_db_session),
) -> RoutingService:
    """Dependency that provides a RoutingService instance."""
    return RoutingService(db=db, mcp=MCPClient())


# Execute a single capability request: resolve capability → server, call the
# tool, return the result. This is the primary execution endpoint for agents.
# 404 = the capability name doesn't exist, or no server is registered that
# provides it. Both errors return 404 but with different error codes so the
# caller can distinguish "unknown capability" from "known but no provider".
@router.post("/request")
async def capability_request(
    body: CapabilityRequest,
    request: Request,
    svc: RoutingService = Depends(get_routing_service),
) -> RouteResult:
    try:
        identity_id = getattr(request.state, "agent_id", None)
        identity_uuid = UUID(identity_id) if identity_id else None
        return await svc.execute(body, identity_id=identity_uuid)
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
    except ResourceDeniedError as exc:
        raise HTTPException(
            status_code=403,
            detail={"error": "resource_not_allowed", "message": str(exc)},
        ) from exc
    except PolicyDeniedError as exc:
        # Structured denial feedback (#443): the agent receives impact, reason,
        # and the next allowed step so it can branch or stop — not blind-retry.
        raise HTTPException(
            status_code=403,
            detail={
                "error": "denied",
                "denied": True,
                "impact": exc.denial.impact,
                "reason": exc.denial.reason,
                "suggestion": exc.denial.suggestion,
            },
        ) from exc


# Execute multiple capability requests in a batch.
# Unlike the single request endpoint, this does NOT return 404 for individual
# failures — it captures errors per-request in the results list and returns
# all results together. This allows the caller to handle partial failures
# gracefully instead of losing all results when one request fails.
# NOTE: Requests execute SEQUENTIALLY (not in parallel). This avoids
# connection pool exhaustion on the MCP clients but means slow servers
# delay the entire batch. A future optimization could execute independent
# requests in parallel with a configurable concurrency limit.
@router.post("/batch")
async def capability_batch(
    body: BatchCapabilityRequest,
    svc: RoutingService = Depends(get_routing_service),
) -> BatchResult:
    results: list[RouteResult | dict[str, Any]] = []
    for req in body.requests:
        try:
            result = await svc.execute(req)
            results.append(result)
        except PolicyDeniedError as exc:
            results.append(
                {
                    "capability": req.capability,
                    "denied": True,
                    "impact": exc.denial.impact,
                    "reason": exc.denial.reason,
                    "suggestion": exc.denial.suggestion,
                }
            )
        except Exception as exc:
            results.append({"capability": req.capability, "error": str(exc)})
    return BatchResult(results=results)


router_rules = APIRouter(prefix="/v1/routing-rules", tags=["routing-rules"])


# Create an explicit routing rule that pins a capability to a specific server.
# Rules override the default resolution logic (which picks the server with
# the highest routing_weight for the primary mapping). Higher priority rules
# win when multiple rules match the same capability. 201 on success.
@router_rules.post("", status_code=201)
async def create_routing_rule(
    body: RoutingRuleCreate,
    svc: RoutingService = Depends(get_routing_service),
) -> dict[str, Any]:
    rule = await svc.create_routing_rule(body)
    return {
        "id": str(rule.id),
        "capability_id": str(rule.capability_id),
        "server_id": str(rule.server_id),
        "priority": rule.priority,
    }


# List all routing rules. Returns an empty list if no rules are defined.
# Rules are evaluated in priority order during capability resolution.
@router_rules.get("")
async def list_routing_rules(
    svc: RoutingService = Depends(get_routing_service),
) -> list[dict[str, Any]]:
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


# Delete a routing rule by ID. Returns 204 on success (standard for DELETE).
# 404 if the rule does not exist — the caller can safely retry the request
# without side effects (idempotent for the "rule doesn't exist" case).
@router_rules.delete("/{rule_id}", status_code=204)
async def delete_routing_rule(
    rule_id: UUID,
    svc: RoutingService = Depends(get_routing_service),
) -> None:
    deleted = await svc.delete_routing_rule(rule_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Routing rule not found"},
        )
