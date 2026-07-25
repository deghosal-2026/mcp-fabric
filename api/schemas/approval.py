"""Pydantic schemas for the approval-gated capability workflow.

Used when an agent class has trust_level='approval-gated' for a given server.
The flow is:
  1. Agent invokes capability -> router creates ApprovalRequest (pending)
  2. Admin approves/denies via PUT /api/v1/approvals/{id}/approve or /deny
  3. Router completes or rejects the original invocation

Endpoints:
  POST /api/v1/approvals               -> ApprovalRequestCreate -> ApprovalRequestResponse
  GET  /api/v1/approvals               -> list[ApprovalRequestResponse]
  GET  /api/v1/approvals/{id}          -> ApprovalRequestResponse
  PUT  /api/v1/approvals/{id}/approve  -> ApprovalAction
  PUT  /api/v1/approvals/{id}/deny     -> ApprovalAction
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ApprovalRequestCreate(BaseModel):
    """Request body for creating an approval request (POST /api/v1/approvals).

    Created automatically by the routing layer when an approval-gated capability
    is invoked. The router supplies:
      - agent_identity_id: which agent is requesting.
      - capability_id: which capability they want to invoke.
      - server_id: which server would fulfill the request.
      - request_params: the parameters the agent intends to pass (for admin review).
    """

    agent_identity_id: UUID
    capability_id: UUID
    server_id: UUID
    request_params: dict[str, Any] | None = None


class ApprovalRequestResponse(BaseModel):
    """Full approval request representation returned by the API.

    model_config = {"from_attributes": True} for ORM conversion.
    Matches the ApprovalRequest ORM model.

    Fields like approver_id and approver_note are only populated after an
    admin has acted on the request. result is populated if the approved
    invocation completed successfully.
    """

    id: UUID
    agent_identity_id: UUID
    capability_id: UUID
    server_id: UUID
    status: str
    request_params: dict[str, Any] | None = None
    requested_at: datetime
    resolved_at: datetime | None = None
    expires_at: datetime
    approver_id: UUID | None = None
    approver_note: str | None = None
    result: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class ApprovalAction(BaseModel):
    """Request body for approving or denying an approval request.

    Fields:
      - action: 'approved' or 'denied' (required).
      - approver_id: UUID of the admin making the decision.
      - note: optional reason for the decision.
    """

    action: str = Field(default="approved", pattern=r"^(approved|denied)$")
    approver_id: UUID | None = None
    note: str | None = None


class ApprovalStatusResponse(BaseModel):
    """Lightweight response returned after an approval/denial action.

    Unlike ApprovalRequestResponse, this only includes fields relevant to the
    action outcome — status, result, approver_note, and resolved_at. Used to
    confirm that the action was recorded without sending the full request
    payload back.
    """

    id: UUID
    status: str
    result: dict[str, Any] | None = None
    approver_note: str | None = None
    resolved_at: datetime | None = None
