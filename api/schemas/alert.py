"""Pydantic schemas for alert rules and events.

Endpoints:
  POST /api/v1/alerts/rules          -> AlertRuleCreate -> AlertRuleResponse
  GET  /api/v1/alerts/rules/{id}     -> AlertRuleResponse
  POST /api/v1/alerts/events/{id}/ack -> AcknowledgeRequest
  GET  /api/v1/alerts/events         -> list[AlertEventResponse]
  POST /api/v1/alerts/evaluate       -> ThresholdEvaluation (internal/async)
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AlertRuleCreate(BaseModel):
    """Request body for creating a new alert rule (POST /api/v1/alerts/rules).

    name:      1-255 chars, human-readable label.
    alert_type: discriminator like 'error_rate', 'latency_p99', 'auth_failures'.
    condition: rule-specific JSON payload (structure varies by alert_type).
               Defaults to empty dict so the caller must provide meaningful values.
    channels:  list of notification destinations: 'log', 'slack', 'pagerduty',
               'webhook'. Defaults to ['log'].
    """

    name: str = Field(min_length=1, max_length=255)
    alert_type: str = Field(min_length=1, max_length=100)
    condition: dict = Field(default_factory=dict)
    channels: list[str] = Field(default_factory=lambda: ["log"])


class AlertRuleResponse(BaseModel):
    """Alert rule representation returned by the API.

    model_config = {"from_attributes": True} for ORM conversion.
    Matches the AlertRule ORM model structure.
    """

    id: UUID
    name: str
    alert_type: str
    condition: dict
    channels: list
    enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertEventResponse(BaseModel):
    """Alert event (firing) representation returned by the API.

    model_config = {"from_attributes": True} for ORM conversion.
    Matches the AlertEvent ORM model. Includes the rule_id FK and optional
    acknowledgment metadata.
    """

    id: UUID
    rule_id: UUID
    message: str
    details: dict | None = None
    fired_at: datetime
    acknowledged_at: datetime | None = None
    acknowledged_by: UUID | None = None

    model_config = {"from_attributes": True}


class AcknowledgeRequest(BaseModel):
    """Request body for acknowledging an alert event.

    POST /api/v1/alerts/events/{id}/ack

    acknowledged_by is the UUID of the admin user performing the action.
    This is validated against the AdminUser table by the service layer.
    """

    acknowledged_by: UUID


class ThresholdEvaluation(BaseModel):
    """Result of evaluating a single alert rule's condition threshold.

    Used internally by the alert evaluation service (not directly exposed as
    a request/response schema). The monitor evaluates all active rules and
    collects ThresholdEvaluation results to decide which AlertEvents to fire.
    """

    rule_id: UUID
    rule_name: str
    triggered: bool
    message: str | None = None
