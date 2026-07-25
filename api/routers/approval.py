"""Approval workflow routes.

Manages approval requests for privileged operations (e.g. deploying a new
MCP server with a high trust level, decommissioning a production server).
This implements a human-in-the-loop gating mechanism: an agent or user creates
a request, and a reviewer (typically another admin) either approves or denies it.

User journeys:
  - An automated process creates an approval request (POST /v1/approvals)
  - A human reviewer reviews pending requests (GET /v1/approvals)
  - The reviewer approves or denies (POST /v1/approvals/{id}/review)
  - The original caller polls for status (GET /v1/approvals/{id})

Architectural notes:
  - Approval requests have a TTL (expiration) after which they are
    automatically denied. Expired requests return 410 Gone.
  - Once resolved (approved or denied), the request is immutable —
    re-reviewing returns 409 Conflict.
  - This is a synchronous approval flow. Future iterations may add
    async notification (webhooks/email) when a review is needed.

Endpoints: GET /v1/approvals, POST /v1/approvals, GET /v1/approvals/{request_id},
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


# List approval requests, optionally filtered by status.
# Intended for the review dashboard UI — reviewers view pending requests
# and act on them. The `status` filter is nullable so callers can list
# everything or scope to a specific state.
@router.get("")
async def list_approval_requests(
    status: str | None = None,
    svc: ApprovalService = Depends(get_approval_service),
) -> list[ApprovalRequestResponse]:
    return await svc.list_requests(status_filter=status)


# Create a new approval request that must be manually reviewed.
# 201 = resource created. The request starts in "pending" status.
# No auth enforcement here yet — the caller identity is captured
# in the request payload when auth middleware is wired up.
@router.post("", status_code=201)
async def create_approval_request(
    body: ApprovalRequestCreate,
    svc: ApprovalService = Depends(get_approval_service),
) -> ApprovalRequestResponse:
    return await svc.create_request(body)


# Poll the current status of an approval request. Used by automated
# callers that created a request and are waiting for a human to review it.
# Returns 404 if the request_id doesn't exist (or has been purged).
@router.get("/{request_id}")
async def get_approval_status(
    request_id: UUID,
    svc: ApprovalService = Depends(get_approval_service),
) -> ApprovalStatusResponse:
    try:
        return await svc.get_status(request_id)
    except ApprovalNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": str(exc)},
        ) from exc


# Review (approve/deny) an approval request.
# 404 = no such request; 409 = already approved/denied (immutable);
# 410 = request TTL expired, no longer actionable.
# The 410 Gone status is semantically precise here: the request is
# permanently unavailable for action, not just missing.
@router.post("/{request_id}/review")
async def review_approval_request(
    request_id: UUID,
    body: ApprovalAction,
    svc: ApprovalService = Depends(get_approval_service),
) -> ApprovalRequestResponse:
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
