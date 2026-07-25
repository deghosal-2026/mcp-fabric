"""Authentication and account management routes.

Endpoints: POST /v1/auth/login, /connect, /setup, /logout, /mfa/*, /password-reset.
"""

import hashlib
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


@router.post("/login")
async def login(
    body: LoginRequest,
    svc: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Authenticate an admin user and return a token.

    Returns 423 if account locked, 401 if credentials invalid.
    """
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


@router.post("/connect")
async def connect_agent(
    body: LoginRequest,
    svc: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Create an agent connection token. Returns a signed token for the agent."""
    token = svc.create_token(
        subject=body.username,
        token_type="agent",
        agent_class=body.username,
        role="agent",
    )
    return TokenResponse(token=token)


@router.post("/setup", status_code=201)
async def setup_admin(
    body: SetupCompleteRequest,
    svc: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Perform first-time admin setup. Returns 409 if already set up."""
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


@router.post("/mfa/setup")
async def mfa_setup(
    request: Request,
    svc: AuthService = Depends(get_auth_service),
) -> MFASetupResponse:
    """Initiate MFA setup for the authenticated admin. Returns 404 if admin not found."""
    admin_id = _get_admin_id(request)
    try:
        return await svc.mfa_setup(admin_id)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": str(exc)},
        ) from exc


@router.post("/mfa/verify-setup")
async def mfa_verify_setup(
    request: Request,
    body: MFAVerifySetupRequest,
    svc: AuthService = Depends(get_auth_service),
) -> dict:
    """Verify and enable MFA by confirming the TOTP code. Returns 400 if the code is invalid."""
    admin_id = _get_admin_id(request)
    ok = await svc.mfa_verify_setup(admin_id, body.secret, body.code)
    if not ok:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_code", "message": "Invalid TOTP code or admin not found"},
        )
    return {"status": "ok", "message": "MFA enabled"}


@router.post("/mfa/verify")
async def mfa_verify(
    request: Request,
    body: MFAVerifyRequest,
    svc: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Verify a TOTP code during login. Returns 404 if admin not found, 400 if code invalid."""
    admin_id = _get_admin_id(request)
    result = await db.execute(
        select(AdminUser).where(AdminUser.id == admin_id)
    )
    admin = result.scalar_one_or_none()
    if admin is None or not admin.mfa_secret:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Admin not found or MFA not configured"},
        )
    if not svc.mfa_verify(admin.mfa_secret, body.code):
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_code", "message": "Invalid TOTP code"},
        )
    return {"status": "ok", "message": "Code verified"}


@router.post("/mfa/recover")
async def mfa_recover(
    request: Request,
    body: MFARecoveryRequest,
    svc: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Recover MFA access using a recovery code.

    Returns 404 if admin not found, 400 if code invalid.
    """
    admin_id = _get_admin_id(request)
    result = await db.execute(
        select(AdminUser).where(AdminUser.id == admin_id)
    )
    admin = result.scalar_one_or_none()
    if admin is None or not admin.recovery_codes:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Admin not found or no recovery codes"},
        )
    code_hash = hashlib.sha256(body.recovery_code.encode()).hexdigest()
    if code_hash not in admin.recovery_codes:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_code", "message": "Invalid recovery code"},
        )
    admin.recovery_codes = [c for c in admin.recovery_codes if c != code_hash]
    await db.commit()
    return {"status": "ok", "message": "Recovery code accepted"}


@router.post("/password-reset")
async def password_reset(
    body: PasswordResetRequest,
    svc: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Request a password reset email. Returns a reset token in dev, emails it in production."""
    result = await db.execute(
        select(AdminUser).where(AdminUser.email == body.email)
    )
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


@router.post("/password-reset/complete")
async def password_reset_complete(
    body: PasswordResetCompleteRequest,
    svc: AuthService = Depends(get_auth_service),
) -> dict:
    """Complete a password reset using a token and new password."""
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


@router.post("/logout")
async def logout(
    request: Request,
    svc: AuthService = Depends(get_auth_service),
) -> dict:
    """Invalidate the current admin session. Returns 200 regardless."""
    session_token = request.headers.get("X-Session-Token", "")
    if session_token:
        await svc.logout_admin_session(session_token)
    return {"status": "ok", "message": "Logged out"}
