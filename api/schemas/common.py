"""Shared Pydantic schemas for pagination, errors, and policy decisions.

Used across multiple API endpoints for consistent response shapes.
"""

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from api.schemas.audit import AuditEventResponse
    from api.schemas.server import ServerResponse


class PaginationMeta(BaseModel):
    """Cursor-based pagination metadata."""

    next_cursor: str | None = None
    has_more: bool = False
    per_page: int = Field(default=50, ge=1, le=200)
    total: int = 0


class PaginatedServers(BaseModel):
    """Paginated list of MCP servers."""

    servers: list["ServerResponse"]
    pagination: PaginationMeta


class PaginatedAudit(BaseModel):
    """Paginated list of audit events."""

    events: list["AuditEventResponse"]
    pagination: PaginationMeta


class PaginatedApprovals(BaseModel):
    """Paginated list of approval requests."""

    approvals: list[dict[str, Any]]
    pagination: PaginationMeta


class FabricError(BaseModel):
    """Standard error response envelope for the fabric API."""

    error: str
    message: str
    details: dict | None = None
    request_id: str | None = None
    suggestion: str | None = None
    retry_after: int | None = None


class PolicyDecision(BaseModel):
    """OPA policy evaluation result for an agent-capability pair."""

    allow: bool
    approval_required: bool = False
    trust_level: str = "unreviewed"
    agent_class: str | None = None
    cross_team: bool = False
