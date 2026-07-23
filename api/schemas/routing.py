"""Pydantic schemas for capability routing and batch dispatch."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CapabilityRequest(BaseModel):
    """A single capability invocation request targeting the router."""


    capability: str
    params: dict[str, Any] = {}


class BatchCapabilityRequest(BaseModel):
    """Batch of capability requests for bulk dispatch."""

    requests: list[CapabilityRequest] = Field(min_length=1, max_length=10)


class RouteResult(BaseModel):
    """Result of routing a single capability request."""

    result: dict[str, Any]
    server: str
    server_id: UUID
    latency_ms: int
    fallback_used: bool = False
    routing_reason: str | None = None


class BatchResult(BaseModel):
    """Aggregated results from a batch capability dispatch."""

    results: list[RouteResult | dict[str, Any]]


class RoutingRuleCreate(BaseModel):
    """Request body for creating a routing rule."""

    capability_id: UUID
    server_id: UUID
    priority: int = 0
    condition: dict | None = None
