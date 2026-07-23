"""Pydantic schemas for admin user management."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AdminUserInvite(BaseModel):
    """Request body for inviting a new admin user."""


    email: str
    role: str = Field(pattern=r"^(admin|editor|viewer)$")
    team_namespace: str | None = None


class AdminUserResponse(BaseModel):
    """Admin user representation returned by the API."""

    id: UUID
    username: str
    email: str
    role: str
    team_namespace: str | None = None
    mfa_enabled: bool = False
    status: str
    last_login_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminUserUpdate(BaseModel):
    """Request body for updating an admin user's role or namespace."""

    role: str | None = Field(default=None, pattern=r"^(admin|editor|viewer)$")
    team_namespace: str | None = None
