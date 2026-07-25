"""Pydantic schemas for audit event queries and export requests.

Endpoints:
  GET  /api/v1/audit              -> list[AuditEventResponse]
  POST /api/v1/audit/export       -> AuditExportRequest (triggers CSV/JSON download)
"""

from datetime import datetime
from typing import Any
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
    details: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditExportRequest(BaseModel):
    """Filter parameters for exporting audit logs (POST /api/v1/audit/export).

    All fields are optional — omitting all filters exports the full audit log
    (subject to pagination limits).

    Fields mirror the GET /v1/audit query parameters so the UI can forward
    its active filters directly to the export endpoint.

    Fields:
        event_type: filter by event type (e.g. "server_registered").
        actor_type: filter by actor type ("agent" | "admin").
        actor_id: filter by actor ID (free-text search on actor_id).
        date_from / date_to: ISO 8601 date range filter (e.g. "2024-01-01").
        format: output format — 'json' (default) or 'csv'.

    Note: format field shadows the built-in Python keyword, but Pydantic
    handles this correctly via the field name resolution.
    """

    event_type: str | None = None
    actor_type: str | None = None
    actor_id: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    format: str = "json"
