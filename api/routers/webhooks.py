"""Webhook registration and management routes.

Allows agents to register webhooks that fire when specific capability events
occur (capability_added, capability_deprecated, capability_schema_changed).
When an event happens, the system POSTs to the registered webhook URL with a
signed payload (using the webhook secret) so the recipient can verify it.

User journeys:
  - An agent registers a webhook to get notified when a capability they depend
    on is deprecated (POST /v1/agents/{id}/webhooks)
  - An agent lists their registered webhooks (GET /v1/agents/{id}/webhooks)
  - An agent deletes a stale webhook (DELETE .../webhooks/{id})
  - An admin reactivates a disabled webhook (POST .../webhooks/{id}/reactivate)

Architectural notes:
  - This is the ONLY router that stores data in-memory (the _webhooks dict)
    instead of the database. This is an intentional design choice for the
    v0.1 MVP — webhook registrations will be lost on server restart.
    See TODO v0.2.0: Migrate to persistent DB model.
  - Webhook secrets use a "whsec_" prefix for easy identification in logs.
  - No auth middleware is applied yet — any agent ID can manage any webhook
    (see TODO v0.2.0: Add auth middleware).

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

ALLOWED_EVENTS = frozenset(
    {
        "capability_added",
        "capability_deprecated",
        "capability_schema_changed",
    }
)

_webhooks: dict[tuple[str, str], dict[str, Any]] = {}
# TODO v0.2.0: Migrate from in-memory dict to a persistent DB model.
#              In-memory store loses all registrations on server restart.


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


# Register a new webhook for an agent. Returns a webhook_secret that the
# recipient uses to verify payload signatures. 422 = one or more event names
# are not in the allowed set. The webhook starts in "active" status.
# NOTE: Currently unauthenticated — any caller can register webhooks for any
# agent_id. v0.2.0 must add auth middleware (see TODO above).
# NOTE: Webhook data is stored in-memory only — lost on server restart.
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


# List all webhooks registered for a specific agent.
# The agent_id is used as the first element of the tuple key in _webhooks.
# Returns an empty list if the agent has no webhooks or doesn't exist.
# NOTE: The `if key[0] == agent_id` filter is O(n) — fine for in-memory
# until v0.2.0 DB migration moves this to a SQL query.
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


# Delete a webhook registration. Returns 204 on success.
# 404 if the combination of agent_id and webhook_id doesn't exist.
# The webhook_secret becomes invalid immediately — no more events will
# be sent to this URL.
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


# Reactivate a previously disabled webhook. Sets status back to "active".
# 404 if the webhook doesn't exist. Reactivation is useful when a webhook
# was automatically disabled after too many delivery failures (not yet
# implemented — the disable-on-failure logic is v0.2.0+).
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
