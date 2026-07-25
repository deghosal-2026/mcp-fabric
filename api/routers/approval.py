"""Approval workflow routes.

Endpoints: POST /v1/approvals, GET /v1/approvals/{request_id},
POST /v1/approvals/{request_id}/review.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_approval_service
from api.schemas.approval import (
    ApprovalAction,
    ApprovalRequestCreate,
    ApprovalRequestResponse,
    ApprovalStatusResponse,
)
from api.services.approval_service import (
    ApprovalAlreadyResolvedError,
    ApprovalExpiredError,
    ApprovalNotFoundError,
    ApprovalService,
)

router = APIRouter(prefix="/v1/approvals", tags=["approvals"])


@router.get("")
async def list_approval_requests(
    status: str | None = None,
    svc: ApprovalService = Depends(get_approval_service),
) -> list[ApprovalRequestResponse]:
    """List approval requests, optionally filtered by status (pending/approved/denied)."""
    return await svc.list_requests(status_filter=status)


@router.post("", status_code=201)
async def create_approval_request(
    body: ApprovalRequestCreate,
    svc: ApprovalService = Depends(get_approval_service),
) -> ApprovalRequestResponse:
    """Create a new approval request. Returns 201 with the created request."""
    return await svc.create_request(body)


@router.get("/{request_id}")
async def get_approval_status(
    request_id: UUID,
    svc: ApprovalService = Depends(get_approval_service),
) -> ApprovalStatusResponse:
    """Get the current status of an approval request. Returns 404 if not found."""
    try:
        return await svc.get_status(request_id)
    except ApprovalNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": str(exc)},
        ) from exc


@router.post("/{request_id}/review")
async def review_approval_request(
    request_id: UUID,
    body: ApprovalAction,
    svc: ApprovalService = Depends(get_approval_service),
) -> ApprovalRequestResponse:
    """Review (approve/deny) an approval request.

    Returns 404 if not found, 409 if already resolved, 410 if expired.
    """
    try:
        return await svc.approve(request_id, body)
    except ApprovalNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": str(exc)},
        ) from exc
    except ApprovalAlreadyResolvedError as exc:
        raise HTTPException(
            status_code=409,
            detail={"error": "already_resolved", "message": str(exc)},
        ) from exc
    except ApprovalExpiredError as exc:
        raise HTTPException(
            status_code=410,
            detail={"error": "expired", "message": str(exc)},
        ) from exc
