"""Shared Pydantic schemas for pagination, errors, and policy decisions.

These schemas are reused across multiple API endpoint groups for consistent
response shapes. They are not specific to any single resource.

TYPE_CHECKING imports avoid circular dependencies between schema modules.
The forward references (list["ServerResponse"]) are resolved by the
model_rebuild() calls in __init__.py.
"""

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from api.schemas.audit import AuditEventResponse
    from api.schemas.server import ServerResponse


class PaginationMeta(BaseModel):
    """Cursor-based pagination metadata included in all paginated responses.

    Fields:
        next_cursor: Opaque cursor string for the next page (null if last page).
        has_more:    Whether additional pages exist beyond this one.
        per_page:    Number of items per page (default 50, max 200).
        total:       Total number of items matching the query (approximate for
                     large datasets; cursor pagination may not have an exact count).
    """

    next_cursor: str | None = None
    has_more: bool = False
    per_page: int = Field(default=50, ge=1, le=200)
    total: int = 0


class PaginatedServers(BaseModel):
    """Paginated list of MCP servers (GET /api/v1/servers).

    Uses forward reference to ServerResponse (defined in api.schemas.server).
    The forward ref is resolved via model_rebuild() in __init__.py.

    The `servers` field is the primary storage. An `items` alias is added
    for frontend consumers that expect a generic `items` array.
    """

    servers: list["ServerResponse"]
    pagination: PaginationMeta

    @property
    def items(self) -> list["ServerResponse"]:  # type: ignore[name-defined]
        return self.servers


class PaginatedAudit(BaseModel):
    """Paginated list of audit events (GET /api/v1/audit).

    Uses forward reference to AuditEventResponse (defined in api.schemas.audit).

    The `events` field is the primary storage. An `items` alias is added
    for frontend consumers that expect a generic `items` array.
    """

    events: list["AuditEventResponse"]
    pagination: PaginationMeta

    @property
    def items(self) -> list["AuditEventResponse"]:  # type: ignore[name-defined]
        return self.events


class PaginatedApprovals(BaseModel):
    """Paginated list of approval requests (GET /api/v1/approvals).

    Uses dict[str, Any] instead of a forward reference to avoid circular imports
    with the approval schemas. The response serializer converts ORM rows to dicts.
    """

    approvals: list[dict[str, Any]]
    pagination: PaginationMeta

    @property
    def items(self) -> list[dict[str, Any]]:
        return self.approvals


class FabricError(BaseModel):
    """Standard error response envelope for the fabric API.

    All error responses follow this shape for consistency:
      - error:      Machine-readable error code (e.g. "NOT_FOUND", "VALIDATION_ERROR").
      - message:    Human-readable error description.
      - details:    Optional structured payload with more context (e.g. field-level
                    validation errors).
      - request_id: Correlation ID for tracing the failed request in logs.
      - suggestion: Optional suggested fix for the caller.
      - retry_after: Seconds to wait before retrying (for rate-limit errors).
    """

    error: str
    message: str
    details: dict | None = None
    request_id: str | None = None
    suggestion: str | None = None
    retry_after: int | None = None


class PolicyDecision(BaseModel):
    """OPA policy evaluation result for an agent-capability pair.

    Returned by the OPA policy engine when deciding whether an agent class
    is allowed to invoke a capability on a specific server.

    Fields:
        allow:             Whether the action is permitted.
        approval_required: If true, the router should create an ApprovalRequest
                           and wait for admin action before proceeding.
        trust_level:       The resolved trust level for this agent-capability pair.
        agent_class:       The agent class name for audit/logging.
        cross_team:        Whether the request crosses team namespace boundaries
                           (may trigger additional policy checks).
    """

    allow: bool
    approval_required: bool = False
    trust_level: str = "unreviewed"
    agent_class: str | None = None
    cross_team: bool = False
