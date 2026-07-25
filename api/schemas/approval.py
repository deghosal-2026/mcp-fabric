"""Pydantic schemas for the approval-gated capability workflow."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ApprovalRequestCreate(BaseModel):
    agent_identity_id: UUID
    capability_id: UUID
    server_id: UUID
    request_params: dict | None = None


class ApprovalRequestResponse(BaseModel):
    id: UUID
    agent_identity_id: UUID
    capability_id: UUID
    server_id: UUID
    status: str
    request_params: dict | None = None
    requested_at: datetime
    resolved_at: datetime | None = None
    expires_at: datetime
    approver_id: UUID | None = None
    approver_note: str | None = None
    result: dict | None = None

    model_config = {"from_attributes": True}


class ApprovalAction(BaseModel):
    approver_id: UUID
    note: str | None = None


class ApprovalStatusResponse(BaseModel):
    id: UUID
    status: str
    result: dict | None = None
    approver_note: str | None = None
    resolved_at: datetime | None = None
