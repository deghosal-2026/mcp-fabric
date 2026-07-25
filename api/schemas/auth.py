"""Pydantic schemas for admin authentication and MFA.

Endpoints:
  POST /api/v1/auth/login              -> LoginRequest -> TokenResponse
  POST /api/v1/auth/mfa/setup          -> MFASetupResponse
  POST /api/v1/auth/mfa/verify-setup   -> MFAVerifySetupRequest
  POST /api/v1/auth/mfa/verify         -> MFAVerifyRequest -> TokenResponse
  POST /api/v1/auth/mfa/recover        -> MFARecoveryRequest -> TokenResponse
  POST /api/v1/auth/password-reset     -> PasswordResetRequest
  POST /api/v1/auth/setup-complete     -> SetupCompleteRequest
  POST /api/v1/auth/webhooks           -> WebhookRegistrationRequest -> WebhookResponse
  GET  /api/v1/auth/webhooks           -> list[WebhookResponse]
"""

from uuid import UUID

from pydantic import BaseModel, Field

from api.schemas.admin import AdminUserResponse


class LoginRequest(BaseModel):
    """Admin login credentials (POST /api/v1/auth/login).

    username and password are both required strings. The service layer
    validates against AdminUser.password_hash (argon2/bcrypt).
    """

    username: str
    password: str


class TokenResponse(BaseModel):
    """JWT bearer token returned after successful authentication.

    Fields:
        token:       The JWT string (signed with the fabric's secret key).
        token_type:  Always 'bearer' (standard OAuth2 convention).
        expires_in:  TTL in seconds (default 8 hours = 28800s).
    """

    token: str
    token_type: str = "bearer"
    expires_in: int = 28800


class LoginResponse(TokenResponse):
    """Admin login/bootstrap response used by the UI.

    Extends the token payload with the authenticated admin user and whether
    MFA is still required before the session is fully usable.
    """

    user: AdminUserResponse
    mfa_required: bool = False


class MFASetupResponse(BaseModel):
    """MFA enrollment details returned by POST /api/v1/auth/mfa/setup.

    Fields:
        secret:        The TOTP shared secret (base32-encoded) for the authenticator app.
        qr_code:       Base64-encoded PNG of the TOTP URI QR code for easy scanning.
        recovery_codes: List of one-time recovery codes (each can bypass MFA once).
        setup_token:   Temporary token that must be submitted with the first TOTP code
                       to confirm setup (prevents partial setup attacks).
    """

    secret: str
    qr_code: str
    recovery_codes: list[str]
    setup_token: str = ""


class MFAVerifyRequest(BaseModel):
    """TOTP code submission for MFA verification during login.

    POST /api/v1/auth/mfa/verify

    code must be exactly 6 characters (standard TOTP length).
    """

    code: str = Field(min_length=6, max_length=6)


class MFAVerifySetupRequest(BaseModel):
    """TOTP code submission to confirm MFA setup completion.

    POST /api/v1/auth/mfa/verify-setup

    The user scans the QR code, enters the 6-digit code from their authenticator
    app, and submits it with the secret they received from setup. This confirms
    the TOTP seed was correctly provisioned.
    """

    secret: str
    code: str = Field(min_length=6, max_length=6)


class MFARecoveryRequest(BaseModel):
    """Recovery code submission for MFA bypass (POST /api/v1/auth/mfa/recover).

    When a user loses access to their authenticator app, they can use one of
    the recovery codes generated during MFA setup. Each recovery code is
    one-time-use and is consumed after successful verification.
    """

    recovery_code: str


class PasswordResetRequest(BaseModel):
    """Password reset email trigger (POST /api/v1/auth/password-reset).

    Sends a password reset link to the given email address if it matches
    an admin user. Always returns 200 to avoid email enumeration.
    """

    email: str


class PasswordResetCompleteRequest(BaseModel):
    """Password reset completion payload (POST /api/v1/auth/password-reset/complete).

    Fields:
        token:    The reset token from the email link (validated server-side).
        password: New password (must be 8-128 chars, validated server-side
                  for complexity requirements).
    """

    token: str
    password: str = Field(min_length=8, max_length=128)


class SetupCompleteRequest(BaseModel):
    """Initial admin setup payload (POST /api/v1/auth/setup-complete).

    Called during first-run setup to create the initial admin password.
    The MFA code is optional — it's used to verify the TOTP seed if
    MFA was configured during setup.

    Fields:
        password: New admin password (8-128 chars).
        mfa_code: Optional 6-digit TOTP code to verify MFA setup.
    """

    password: str = Field(min_length=8, max_length=128)
    mfa_code: str | None = Field(default=None, min_length=6, max_length=6)


class WebhookRegistrationRequest(BaseModel):
    """Request to register a webhook for fabric events (POST /api/v1/auth/webhooks).

    Fields:
        url:    Webhook callback URL (must start with http:// or https://).
        events: List of event types to subscribe to (e.g. ["server.created",
                "capability.mapped", "approval.resolved"]). At least one event
                is required.
    """

    url: str = Field(pattern=r"^https?://")
    events: list[str] = Field(min_length=1)


class WebhookResponse(BaseModel):
    """Webhook registration details returned by the API.

    Fields:
        id:             Unique webhook identifier.
        webhook_secret: HMAC secret for verifying webhook payload signatures
                        (only returned on creation).
        url:            The registered callback URL.
        events:         Subscribed event types.
    """

    id: UUID
    webhook_secret: str
    url: str
    events: list[str]
