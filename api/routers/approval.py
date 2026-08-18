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

from api.dependencies import get_approval_fatigue_service, get_approval_service
from api.schemas.approval import (
    ApprovalAction,
    ApprovalEnvelopeCreate,
    ApprovalEnvelopeResponse,
    ApprovalRequestCreate,
    ApprovalRequestResponse,
    ApprovalStatusResponse,
    BulkApproveRequest,
    BulkApproveResponse,
)
from api.schemas.common import PaginatedApprovals, PaginationMeta
from api.services.approval_fatigue_service import (
    ApprovalFatigueService,
    InsufficientEnvelopeError,
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
    per_page: int = 50,
    offset: int = 0,
    q: str | None = None,
    svc: ApprovalService = Depends(get_approval_service),
) -> PaginatedApprovals:
    limit = per_page
    items = await svc.list_requests(status_filter=status, limit=limit, offset=offset)
    total = await svc.count_requests(status_filter=status)
    return PaginatedApprovals(
        approvals=[item.model_dump(mode="json") for item in items],
        pagination=PaginationMeta(
            next_cursor=str(offset + limit) if offset + limit < total else None,
            has_more=offset + limit < total,
            per_page=limit,
            total=total,
        ),
    )


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


# Grant a scoped, expiring approval envelope (#442). A human pre-authorizes
# a budget for a scope; the deterministic validator burns it down per
# in-envelope action. Registered before /{request_id} so the literal
# "envelopes" path segment is not swallowed by the UUID route.
@router.post("/envelopes", status_code=201)
async def grant_envelope(
    body: ApprovalEnvelopeCreate,
    svc: ApprovalFatigueService = Depends(get_approval_fatigue_service),
) -> ApprovalEnvelopeResponse:
    envelope = await svc.grant_envelope(
        scope=body.scope,
        budget=body.budget,
        expires_at=body.expires_at,
    )
    return ApprovalEnvelopeResponse(
        id=envelope.id,
        scope=envelope.scope,
        budget=envelope.budget,
        remaining=envelope.remaining,
        expires_at=envelope.expires_at,
    )


# Bulk-approve a batch of pending requests in one action (#442), with
# explicit anomaly markers separating genuine changes from noise. Envelope
# budget (if any) is burned down and the remaining budget returned so the UI
# can surface fatigue-reduction state.
@router.post("/bulk-approve")
async def bulk_approve(
    body: BulkApproveRequest,
    svc: ApprovalFatigueService = Depends(get_approval_fatigue_service),
) -> BulkApproveResponse:
    try:
        return await svc.bulk_approve(
            envelope_id=str(body.envelope_id) if body.envelope_id else "",
            action_ids=[str(a) for a in body.action_ids],
            anomaly_ids=[str(a) for a in body.anomaly_ids],
        )
    except InsufficientEnvelopeError as exc:
        raise HTTPException(
            status_code=409,
            detail={"error": "insufficient_envelope", "message": str(exc)},
        ) from exc


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
        if body.action == "denied":
            return await svc.deny(request_id, body)
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
