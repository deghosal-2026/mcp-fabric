"""Pydantic schemas for capability routing and batch dispatch.

Endpoints:
  POST /api/v1/routing/route    -> CapabilityRequest -> RouteResult
  POST /api/v1/routing/batch    -> BatchCapabilityRequest -> BatchResult
  POST /api/v1/routing/rules    -> RoutingRuleCreate
  GET  /api/v1/routing/rules    -> list[RoutingRuleResponse]
"""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CapabilityRequest(BaseModel):
    """A single capability invocation request targeting the router.

    POST /api/v1/routing/route

    Fields:
        capability: The normalized capability name (e.g. "code:review").
        params:     Arbitrary JSON parameters that match the capability's
                    normalized_input_schema. The router will transform these
                    through the mapping's input_mapping before sending to
                    the server tool.
        resources:  Optional resource dimension values for policy evaluation
                    (v0.2.0). If not provided, Fabric attempts to extract
                    them from params via dimension_value_map.
                    E.g. {"env": "staging", "tenant": "acme-corp"}
    """

    capability: str
    params: dict[str, Any] = {}
    resources: dict[str, str] | None = None


class BatchCapabilityRequest(BaseModel):
    """Batch of capability requests for bulk dispatch.

    POST /api/v1/routing/batch

    Sends up to 10 capability requests in a single call. The router processes
    them independently and returns individual results. Failure of one request
    does not affect the others.

    Validation: min_length=1, max_length=10 requests per batch.
    """

    requests: list[CapabilityRequest] = Field(min_length=1, max_length=10)


class DenialResult(BaseModel):
    """Structured policy-denial feedback returned to the agent (#443).

    A denial is a *result*, not an opaque failure — the agent receives the
    reason, impact, and the next allowed step so it can branch or stop
    correctly rather than blind-retry through alternative tools.
    """

    denied: bool = True
    impact: str = "none"
    reason: str = ""
    suggestion: str | None = None


class RouteResult(BaseModel):
    """Result of routing and executing a single capability request.

    Fields:
        result:         The output from the server tool (transformed through
                        the output_mapping if one exists).
        server:         Human-readable name of the server that fulfilled the request.
        server_id:      UUID of the server (for audit/logging).
        latency_ms:     Round-trip time in milliseconds.
        fallback_used:  Whether this result came from a fallback server (true when
                        the primary was unhealthy or unreachable).
        routing_reason: Explanation of why this server was selected (useful for
                        debugging routing decisions).
    """

    result: dict[str, Any]
    server: str
    server_id: UUID
    latency_ms: int
    fallback_used: bool = False
    routing_reason: str | None = None


class BatchResult(BaseModel):
    """Aggregated results from a batch capability dispatch.

    Each element in results corresponds to a request in the same position
    as the BatchCapabilityRequest.requests list. Successful requests return
    a RouteResult; failed requests return a dict with 'error' and 'message'
    keys (following the FabricError pattern).
    """

    results: list[RouteResult | dict[str, Any]]


class RoutingRuleCreate(BaseModel):
    """Request body for creating a routing rule.

    POST /api/v1/routing/rules

    Fields:
        capability_id: The capability this rule applies to.
        server_id:     The target server for this rule.
        priority:      Lower values are evaluated first (0 = highest priority).
                       Defaults to 0.
        condition:     Optional JSON condition expression. If provided, the rule
                       only matches when the condition evaluates to true against
                       the current context. If null/omitted, the rule is
                       unconditional.
    """

    capability_id: UUID
    server_id: UUID
    priority: int = 0
    condition: dict[str, Any] | None = None
