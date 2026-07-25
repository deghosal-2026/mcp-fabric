from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db_session
from api.models.admin import AdminUser
from api.schemas.alert import AcknowledgeRequest
from api.services.alert_service import AlertService

router = APIRouter(prefix="/v1/alerts", tags=["alerts"])


async def get_alert_service(
    db: AsyncSession = Depends(get_db_session),
) -> AlertService:
    return AlertService(db=db)


@router.get("")
async def list_alerts(
    acknowledged: str | None = None,
    per_page: int = 50,
    q: str | None = None,
    offset: int = 0,
    svc: AlertService = Depends(get_alert_service),
):
    events = await svc.list_events(
        acknowledged=acknowledged,
        limit=per_page,
        offset=offset,
    )
    return {
        "items": events,
        "pagination": {
            "next_cursor": str(offset + per_page) if len(events) == per_page else None,
            "has_more": len(events) == per_page,
            "per_page": per_page,
            "total": len(events),
        },
    }


@router.post("/{alert_id}/acknowledge")
async def acknowledge(
    alert_id: UUID,
    svc: AlertService = Depends(get_alert_service),
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(select(AdminUser).where(AdminUser.role == "admin").limit(1))
    admin = result.scalar_one_or_none()
    admin_id = admin.id if admin else UUID("00000000-0000-0000-0000-000000000001")
    params = AcknowledgeRequest(acknowledged_by=admin_id)
    await svc.acknowledge_alert(alert_id, params)
    return {"status": "ok"}
