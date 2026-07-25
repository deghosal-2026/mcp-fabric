"""Pydantic schemas for admin authentication and MFA.

Covers login, token response, MFA setup/verify, password reset,
webhook registration, and initial setup flow.
"""

from uuid import UUID

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Admin login credentials."""


    username: str
    password: str


class TokenResponse(BaseModel):
    """JWT bearer token returned after successful login."""

    token: str
    token_type: str = "bearer"
    expires_in: int = 28800


class MFASetupResponse(BaseModel):
    """MFA enrollment details including TOTP secret and recovery codes."""

    secret: str
    qr_code: str
    recovery_codes: list[str]
    setup_token: str = ""


class MFAVerifyRequest(BaseModel):
    """TOTP code submission for MFA verification."""

    code: str = Field(min_length=6, max_length=6)


class MFAVerifySetupRequest(BaseModel):
    """TOTP code submission to confirm MFA setup."""

    secret: str
    code: str = Field(min_length=6, max_length=6)


class MFARecoveryRequest(BaseModel):
    """Recovery code submission for MFA bypass."""

    recovery_code: str


class PasswordResetRequest(BaseModel):
    """Password reset email request."""

    email: str


class PasswordResetCompleteRequest(BaseModel):
    """Password reset payload with token and new password."""

    token: str
    password: str = Field(min_length=8, max_length=128)


class SetupCompleteRequest(BaseModel):
    """Initial admin setup payload (password + optional MFA code)."""

    password: str = Field(min_length=8, max_length=128)
    mfa_code: str | None = Field(default=None, min_length=6, max_length=6)


class WebhookRegistrationRequest(BaseModel):
    """Request to register a webhook for fabric events."""

    url: str = Field(pattern=r"^https?://")
    events: list[str] = Field(min_length=1)


class WebhookResponse(BaseModel):
    """Webhook registration details returned by the API."""

    id: UUID
    webhook_secret: str
    url: str
    events: list[str]
