"""Pydantic schemas for alert rules and events."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AlertRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    alert_type: str = Field(min_length=1, max_length=100)
    condition: dict = Field(default_factory=dict)
    channels: list[str] = Field(default_factory=lambda: ["log"])


class AlertRuleResponse(BaseModel):
    id: UUID
    name: str
    alert_type: str
    condition: dict
    channels: list
    enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertEventResponse(BaseModel):
    id: UUID
    rule_id: UUID
    message: str
    details: dict | None = None
    fired_at: datetime
    acknowledged_at: datetime | None = None
    acknowledged_by: UUID | None = None

    model_config = {"from_attributes": True}


class AcknowledgeRequest(BaseModel):
    acknowledged_by: UUID


class ThresholdEvaluation(BaseModel):
    rule_id: UUID
    rule_name: str
    triggered: bool
    message: str | None = None
