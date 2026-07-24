from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db_session
from api.schemas.audit import AuditEventResponse, AuditExportRequest
from api.schemas.common import PaginatedAudit, PaginationMeta
from api.services.audit_service import AuditService

router = APIRouter(prefix="/v1/audit", tags=["audit"])


async def get_audit_service(
    db: AsyncSession = Depends(get_db_session),
) -> AuditService:
    return AuditService(db=db)


@router.get("")
async def list_audit_events(
    event_type: str | None = Query(None),
    actor_type: str | None = Query(None),
    actor_id: str | None = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    svc: AuditService = Depends(get_audit_service),
) -> PaginatedAudit:
    events = await svc.query(
        event_type=event_type,
        actor_type=actor_type,
        actor_id=actor_id,
        limit=limit,
        offset=offset,
    )
    return PaginatedAudit(
        events=[AuditEventResponse.model_validate(e) for e in events],
        pagination=PaginationMeta(
            next_cursor=str(offset + limit) if len(events) == limit else None,
            has_more=len(events) == limit,
            per_page=limit,
            total=0,
        ),
    )


@router.post("/export", status_code=202)
async def export_audit_logs(
    body: AuditExportRequest,
    svc: AuditService = Depends(get_audit_service),
) -> dict:
    raise HTTPException(
        status_code=501,
        detail={
            "error": "not_implemented",
            "message": "Audit export via Celery task is not yet implemented",
        },
    )
