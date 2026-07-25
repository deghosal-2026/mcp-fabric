"""Webhook registration and management routes.

Endpoints: POST /v1/agents/{agent_id}/webhooks,
GET /v1/agents/{agent_id}/webhooks,
DELETE /v1/agents/{agent_id}/webhooks/{webhook_id},
POST /v1/agents/{agent_id}/webhooks/{webhook_id}/reactivate.
"""

import secrets
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/v1/agents", tags=["webhooks"])

ALLOWED_EVENTS = frozenset({
    "capability_added",
    "capability_deprecated",
    "capability_schema_changed",
})

_webhooks: dict[tuple[str, str], dict[str, Any]] = {}


class WebhookCreate(BaseModel):
    url: str
    events: list[str]


class WebhookResponse(BaseModel):
    id: UUID
    url: str
    events: list[str]
    status: str
    webhook_secret: str | None = None


class WebhookListResponse(BaseModel):
    id: UUID
    url: str
    events: list[str]
    status: str


@router.post("/{agent_id}/webhooks", status_code=201)
async def register_webhook(
    agent_id: str,
    body: WebhookCreate,
) -> WebhookResponse:
    invalid = [e for e in body.events if e not in ALLOWED_EVENTS]
    if invalid:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "invalid_events",
                "message": f"Invalid event(s): {invalid}. Allowed: {sorted(ALLOWED_EVENTS)}",
            },
        )
    webhook_id = str(uuid4())
    secret = "whsec_" + secrets.token_hex(32)
    _webhooks[(agent_id, webhook_id)] = {
        "id": webhook_id,
        "url": body.url,
        "events": body.events,
        "status": "active",
        "webhook_secret": secret,
    }
    return WebhookResponse(
        id=UUID(webhook_id),
        url=body.url,
        events=body.events,
        status="active",
        webhook_secret=secret,
    )


@router.get("/{agent_id}/webhooks")
async def list_webhooks(
    agent_id: str,
) -> list[WebhookListResponse]:
    return [
        WebhookListResponse(
            id=UUID(data["id"]),
            url=data["url"],
            events=data["events"],
            status=data["status"],
        )
        for key, data in _webhooks.items()
        if key[0] == agent_id
    ]


@router.delete("/{agent_id}/webhooks/{webhook_id}", status_code=204)
async def delete_webhook(
    agent_id: str,
    webhook_id: str,
) -> None:
    key = (agent_id, webhook_id)
    if key not in _webhooks:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Webhook not found"},
        )
    del _webhooks[key]


@router.post("/{agent_id}/webhooks/{webhook_id}/reactivate")
async def reactivate_webhook(
    agent_id: str,
    webhook_id: str,
) -> WebhookResponse:
    key = (agent_id, webhook_id)
    hook = _webhooks.get(key)
    if hook is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Webhook not found"},
        )
    hook["status"] = "active"
    return WebhookResponse(
        id=UUID(hook["id"]),
        url=hook["url"],
        events=hook["events"],
        status=hook["status"],
    )
