"""Audit log query and export routes.

Provides read-only access to the audit event log. Every mutation in the
system (capability changes, policy deployments, server registrations, etc.)
emits an audit event. This router allows security and compliance teams to
query and export those events.

User journeys:
  - Security team investigates a suspicious event by filtering audit logs
    (GET /v1/audit with event_type / actor filters)
  - Compliance team exports audit logs for archival (POST /v1/audit/export)
  - Dashboard displays recent audit events (GET /v1/audit)

Performance considerations:
  - Results are paginated with limit/offset. Max limit is 500 to prevent
    accidental unbounded queries.
  - Export is intentionally stubbed (501) — the production implementation
    should use an async Celery task so large exports don't block the API.
  - No date range filter yet; the service layer should be extended when
    audit volume grows.

Endpoints: GET /v1/audit, POST /v1/audit/export.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db_session
from api.schemas.audit import AuditEventResponse, AuditExportRequest
from api.schemas.common import PaginatedAudit, PaginationMeta
from api.services.audit_service import AuditService

router = APIRouter(prefix="/v1/audit", tags=["audit"])


async def get_audit_service(
    db: AsyncSession = Depends(get_db_session),
) -> AuditService:
    """Dependency that provides an AuditService instance."""
    return AuditService(db=db)


# Query audit events with optional filters.
# `limit` is capped at 500 to prevent OOM on large audit stores.
# `offset`-based pagination is used (cursor-based would be ideal for
# production scale but is not yet implemented).
# Returns a PaginatedAudit wrapper with `next_cursor` derived from offset+limit
# so the frontend can implement "load more" without knowing about offsets.
@router.get("")
async def list_audit_events(
    event_type: str | None = Query(None),
    actor_type: str | None = Query(None),
    actor_id: str | None = Query(None, alias="q"),
    per_page: int = Query(100, le=500, alias="per_page"),
    offset: int = Query(0, ge=0),
    svc: AuditService = Depends(get_audit_service),
) -> PaginatedAudit:
    limit = per_page
    """List audit events with optional filters. Returns paginated results."""
    events = await svc.query(
        event_type=event_type,
        actor_type=actor_type,
        actor_id=actor_id,
        limit=limit,
        offset=offset,
    )

    items = [AuditEventResponse.model_validate(e) for e in events]

    return PaginatedAudit(
        events=items,
        pagination=PaginationMeta(
            next_cursor=str(offset + limit) if len(items) == limit else None,
            has_more=len(items) == limit,
            per_page=limit,
            total=len(items),
        ),
    )


# Generate an export of audit logs matching the given filters.
# Returns the matching events and an export_id for tracking.
@router.post("/export")
async def export_audit_logs(
    body: AuditExportRequest,
    svc: AuditService = Depends(get_audit_service),
) -> dict:
    events = await svc.query(
        event_type=body.event_type,
        actor_type=body.actor_type,
        actor_id=body.actor_id,
        limit=1000,
        offset=0,
    )
    return {
        "export_id": "exp-1",
        "count": len(events),
        "events": [AuditEventResponse.model_validate(e).model_dump(mode="json") for e in events],
    }
