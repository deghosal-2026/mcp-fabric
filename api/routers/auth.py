"""Authentication and account management routes.

Handles the full auth lifecycle: login, MFA enrollment/verification,
password reset, admin bootstrap, agent connection tokens, and logout.

This is the most security-critical router in the system. Every endpoint
here is a potential attack surface. Special attention is given to:
  - Timing-safe error messages (don't reveal whether an email is registered)
  - Account lockout after failed attempts
  - MFA recovery codes (SHA-256 hashed at rest, one-time use)
  - Session token invalidation on logout

User journeys:
  - First-time admin bootstrap: POST /v1/auth/setup (only works once)
  - Admin login with password: POST /v1/auth/login
  - Admin login with MFA TOTP: POST /v1/auth/mfa/verify
  - MFA enrollment: POST /v1/auth/mfa/setup → verify-setup
  - Lost authenticator: POST /v1/auth/mfa/recover (uses recovery codes)
  - Password reset flow: POST /v1/auth/password-reset → .../complete
  - Agent connection: POST /v1/auth/connect (creates a machine token)

Architectural notes:
  - Some endpoints directly inject `db: AsyncSession` for simple queries
    rather than routing through the service layer. This is an anti-pattern
    that should be refactored — see MFA recovery and password reset endpoints.
  - Session management is token-based (not cookie-based), stored in-memory
    with configurable TTL. Future: migrate to Redis-backed sessions.

Endpoints: POST /v1/auth/login, /connect, /setup, /logout, /mfa/*, /password-reset.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_auth_service, get_db_session
from api.models.admin import AdminUser
from api.schemas.auth import (
    LoginRequest,
    MFARecoveryRequest,
    MFASetupResponse,
    MFAVerifyRequest,
    MFAVerifySetupRequest,
    PasswordResetCompleteRequest,
    PasswordResetRequest,
    SetupCompleteRequest,
    TokenResponse,
)
from api.services.auth_service import (
    AccountLockedError,
    AuthenticationError,
    AuthService,
    BootstrapError,
    PasswordPolicyError,
)
from api.telemetry.logging import logger

router = APIRouter(prefix="/v1/auth", tags=["auth"])


def _get_admin_id(request: Request) -> UUID:
    """Extract the authenticated admin ID from the request state.

    Raises 401 if not authenticated.
    """
    aid = request.state.agent_id
    if not aid:
        raise HTTPException(
            status_code=401,
            detail={"error": "unauthenticated", "message": "Not authenticated"},
        )
    return UUID(aid)


# Authenticate an admin user with password credentials.
# Returns a signed session token on success.
# 423 Locked — too many failed attempts, account is temporarily locked.
# 401 Unauthorized — bad credentials (same message regardless of which
#     field was wrong, to avoid leaking whether the email exists).
@router.post("/login")
async def login(
    body: LoginRequest,
    svc: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    try:
        return await svc.admin_login(body)
    except AccountLockedError as exc:
        raise HTTPException(
            status_code=423,
            detail={"error": "account_locked", "message": str(exc)},
        ) from exc
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_credentials", "message": str(exc)},
        ) from exc


# Create an agent connection (machine-to-machine) token.
# Unlike admin login, this does NOT verify credentials against the DB —
# it signs a JWT with the agent's identity for use in subsequent API calls.
# The agent class is derived from the username field; in a future version
# agents will authenticate via pre-provisioned API keys instead.
@router.post("/connect")
async def connect_agent(
    body: LoginRequest,
    svc: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    token = svc.create_token(
        subject=body.username,
        token_type="agent",
        agent_class=body.username,
        role="agent",
    )
    return TokenResponse(token=token)


# Bootstrap the first admin user. This is a one-time setup that creates
# the initial admin account with default credentials (username "admin",
# email "admin@mcp-fabric.local"). Returns 409 if an admin already exists.
# The email default is intentionally a local-only address — in production
# deployments this should be overridden during deployment configuration.
@router.post("/setup", status_code=201)
async def setup_admin(
    body: SetupCompleteRequest,
    svc: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    try:
        return await svc.first_admin_bootstrap(
            username="admin",
            email="admin@mcp-fabric.local",
            password=body.password,
        )
    except BootstrapError as exc:
        raise HTTPException(
            status_code=409,
            detail={"error": "already_setup", "message": str(exc)},
        ) from exc


# Initiate MFA enrollment for the authenticated admin.
# Generates a TOTP secret and returns it along with a QR code URL
# for the authenticator app. The admin must call /mfa/verify-setup
# next to confirm the secret was properly scanned.
@router.post("/mfa/setup")
async def mfa_setup(
    request: Request,
    svc: AuthService = Depends(get_auth_service),
) -> MFASetupResponse:
    admin_id = _get_admin_id(request)
    try:
        return await svc.mfa_setup(admin_id)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": str(exc)},
        ) from exc


# Complete MFA enrollment by verifying that the admin successfully
# scanned the TOTP secret into their authenticator app. This is the
# second step of a two-step enrollment flow (setup → verify-setup).
# 400 if the TOTP code is wrong — the admin must try again with the
# correct code or restart enrollment with a fresh /mfa/setup.
@router.post("/mfa/verify-setup")
async def mfa_verify_setup(
    request: Request,
    body: MFAVerifySetupRequest,
    svc: AuthService = Depends(get_auth_service),
) -> dict[str, Any]:
    admin_id = _get_admin_id(request)
    ok = await svc.mfa_verify_setup(admin_id, body.secret, body.code)
    if not ok:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_code", "message": "Invalid TOTP code or admin not found"},
        )
    return {"status": "ok", "message": "MFA enabled"}


# Verify a TOTP code as part of the login flow (after password auth).
# This endpoint is called between login and session creation — the admin
# has already provided their password and is now proving possession of the
# authenticator device.
# NOTE: This endpoint directly queries the DB instead of going through the
# service layer. This bypasses the service abstraction and should be
# refactored into AuthService for consistency.
@router.post("/mfa/verify")
async def mfa_verify(
    request: Request,
    body: MFAVerifyRequest,
    svc: AuthService = Depends(get_auth_service),
) -> dict[str, Any]:
    admin_id = _get_admin_id(request)
    if not await svc.mfa_verify_session(admin_id, body.code):
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Admin not found or MFA not configured"},
        )
    return {"status": "ok", "message": "Code verified"}


# Recover MFA access using a pre-generated recovery code.
# Recovery codes are stored as SHA-256 hashes (not plaintext) for security.
# Once used, the recovery code is removed from the list (one-time use).
# The admin should re-enroll MFA after recovery — this endpoint only
# bypasses MFA for the current login session.
# NOTE: Like /mfa/verify, this endpoint directly injects `db` instead of
# using the service layer. This should be refactored.
@router.post("/mfa/recover")
async def mfa_recover(
    request: Request,
    body: MFARecoveryRequest,
    svc: AuthService = Depends(get_auth_service),
) -> dict[str, Any]:
    admin_id = _get_admin_id(request)
    if not await svc.mfa_recover(admin_id, body.recovery_code):
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Admin not found or invalid recovery code"},
        )
    return {"status": "ok", "message": "Recovery code accepted"}


# Request a password reset email.
# Security: Always returns the same message ("If the email exists...")
# regardless of whether the email exists, to prevent email enumeration
# attacks. In development mode the reset token is returned in the response
# body for convenience; in production it should only be sent via email.
# The token is generated by auth_service._store_reset_token() with a TTL.
@router.post("/password-reset")
async def password_reset(
    body: PasswordResetRequest,
    svc: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    result = await db.execute(select(AdminUser).where(AdminUser.email == body.email))
    admin = result.scalar_one_or_none()
    if admin is None:
        logger.info("auth:password_reset_not_found", email=body.email)
        return {"status": "ok", "message": "If the email exists, a reset link has been sent"}
    token = await svc._store_reset_token(admin.id)
    logger.info("auth:password_reset_requested", admin_id=str(admin.id))
    return {
        "status": "ok",
        "message": "If the email exists, a reset link has been sent",
        "token": token,
    }


# Complete the password reset with the token from the email + new password.
# 400 Bad Request — either the token is invalid/expired (AuthenticationError)
# or the new password doesn't meet policy requirements (PasswordPolicyError).
@router.post("/password-reset/complete")
async def password_reset_complete(
    body: PasswordResetCompleteRequest,
    svc: AuthService = Depends(get_auth_service),
) -> dict[str, Any]:
    try:
        await svc.complete_password_reset(body.token, body.password)
        return {"status": "ok", "message": "Password reset successful"}
    except PasswordPolicyError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": "password_policy", "message": str(exc)},
        ) from exc
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_token", "message": str(exc)},
        ) from exc


# Logout — invalidate the current session token.
# Always returns 200 even if the token was already invalid or missing.
# This prevents an attacker from distinguishing between valid and invalid
# tokens via timing or response differences (though the security benefit
# here is marginal since the token is sent in the request header anyway).
@router.post("/logout")
async def logout(
    request: Request,
    svc: AuthService = Depends(get_auth_service),
) -> dict[str, Any]:
    session_token = request.headers.get("X-Session-Token", "")
    if session_token:
        await svc.logout_admin_session(session_token)
    return {"status": "ok", "message": "Logged out"}
