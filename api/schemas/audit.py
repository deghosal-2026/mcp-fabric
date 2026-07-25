"""Pydantic schemas for audit event queries and export requests.

Endpoints:
  GET  /api/v1/audit              -> list[AuditEventResponse]
  POST /api/v1/audit/export       -> AuditExportRequest (triggers CSV/JSON download)
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AuditEventResponse(BaseModel):
    """An audit event as returned by the API (GET /api/v1/audit).

    model_config = {"from_attributes": True} for ORM conversion from AuditEvent.

    Fields match the AuditEvent ORM model. The details field contains a
    structured JSON payload describing what happened (e.g. old/new values,
    request params, client IP).
    """

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
    """Filter parameters for exporting audit logs (POST /api/v1/audit/export).

    All fields are optional — omitting all filters exports the full audit log
    (subject to pagination limits).

    Fields:
        date_from / date_to: ISO 8601 date range filter (e.g. "2024-01-01").
        agent_classes: filter by specific agent class names.
        event_types: filter by specific event types (e.g. ["server.created"]).
        format: output format — 'json' (default) or 'csv'.

    Note: format field shadows the built-in Python keyword, but Pydantic
    handles this correctly via the field name resolution.
    """

    date_from: str | None = None
    date_to: str | None = None
    agent_classes: list[str] | None = None
    event_types: list[str] | None = None
    format: str = "json"
