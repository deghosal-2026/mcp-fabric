"""Pydantic schemas for audit event queries and export requests."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AuditEventResponse(BaseModel):
    """An audit event as returned by the API."""


    id: UUID
    event_type: str
    actor_type: str
    actor_id: str
    target_type: str | None = None
    target_id: str | None = None
    details: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditExportRequest(BaseModel):
    """Filter parameters for exporting audit logs."""

    date_from: str | None = None
    date_to: str | None = None
    agent_classes: list[str] | None = None
    event_types: list[str] | None = None
    format: str = "json"
