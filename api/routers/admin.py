"""Admin user management routes.

Administrative endpoints for managing admin users — invite, update,
deactivate, unlock, and reset MFA. These are privileged operations
intended for use by a super-admin user interface. Every endpoint
requires admin authentication (enforced by middleware, not here).

User journeys:
  - Root admin invites new admins via email (POST /users/invite)
  - Super-admin dashboard lists/manages all admins (GET/PATCH /users)
  - Security team unlocks locked accounts or resets MFA (POST .../unlock, .../reset-mfa)

Security notes:
  - These endpoints check admin auth via middleware, but do NOT currently
    enforce super-admin vs. admin role distinction (see deactivate TODO).
  - All mutations (deactivate, unlock, reset-mfa) return the updated
    AdminUserResponse so the caller can confirm the state change.
  - 404 is returned for unknown IDs rather than 403 to avoid leaking
    information about whether a given UUID refers to a real admin.

Endpoints: POST /v1/admin/users/invite, GET /v1/admin/users,
GET /v1/admin/users/{id}, PATCH /v1/admin/users/{id},
POST /v1/admin/users/{id}/deactivate, POST /v1/admin/users/{id}/unlock,
POST /v1/admin/users/{id}/reset-mfa.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_approval_service, get_auth_service, get_registry_service
from api.schemas.admin import AdminUserInvite, AdminUserResponse, AdminUserUpdate
from api.schemas.dashboard import DashboardStats
from api.services.approval_service import ApprovalService
from api.services.auth_service import AuthService
from api.services.registry_service import RegistryService

router = APIRouter(prefix="/v1/admin", tags=["admin"])


# Invite a new admin user via email.
# 201 = resource created. 409 = the email/username already exists (idempotency
# guard — the frontend should prompt the user to use a different email).
@router.post("/users/invite", status_code=201)
async def invite_admin_user(
    body: AdminUserInvite,
    svc: AuthService = Depends(get_auth_service),
) -> AdminUserResponse:
    try:
        return await svc.invite_admin(body)
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"error": "already_exists", "message": str(exc)},
        ) from exc


# List all admin users. Returns an empty list if none exist (this is
# expected during initial deployment before any invites are sent).
@router.get("/users")
async def list_admin_users(
    svc: AuthService = Depends(get_auth_service),
) -> list[AdminUserResponse]:
    return await svc.list_admins()


# Get a single admin user by ID. Returns 404 if the user does not exist.
# The 404 vs 403 choice is deliberate: we don't want to reveal whether a
# UUID corresponds to a real admin to an unauthenticated caller.
@router.get("/users/{user_id}")
async def get_admin_user(
    user_id: UUID,
    svc: AuthService = Depends(get_auth_service),
) -> AdminUserResponse:
    result = await svc.get_admin(user_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Admin user not found"},
        )
    return result


# Partial update of an admin user (e.g. name, role). PATCH is used (not PUT)
# because this is a partial update — we accept only the fields that should
# change. Returns 404 if the user does not exist.
@router.patch("/users/{user_id}")
async def update_admin_user(
    user_id: UUID,
    body: AdminUserUpdate,
    svc: AuthService = Depends(get_auth_service),
) -> AdminUserResponse:
    result = await svc.update_admin(user_id, body)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Admin user not found"},
        )
    return result


# Deactivate (soft-delete) an admin user. The user retains their record
# in the DB but can no longer log in. This is a POST (not DELETE) because
# deactivation is reversible (the user can be re-activated later).
@router.post("/users/{user_id}/deactivate")
async def deactivate_admin_user(
    user_id: UUID,
    svc: AuthService = Depends(get_auth_service),
) -> AdminUserResponse:
    # TODO v0.2.0: Accept a request context to check `requesting_admin_id`
    #              and reject if the admin is deactivating themselves.
    result = await svc.deactivate_admin(user_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Admin user not found"},
        )
    return result


# Unlock a locked admin account. Accounts are locked after too many failed
# login attempts (configurable threshold in auth_service). This is a POST
# (idempotent in effect — unlocking an already-unlocked account is a no-op
# at the service layer but still returns 200).
@router.post("/users/{user_id}/unlock")
async def unlock_admin_user(
    user_id: UUID,
    svc: AuthService = Depends(get_auth_service),
) -> AdminUserResponse:
    result = await svc.unlock_admin(user_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Admin user not found"},
        )
    return result


# Reset an admin user's MFA configuration (e.g. if they lost their
# authenticator device). The admin will need to re-enroll MFA on next login.
# This is a privileged operation — only another admin can perform it.
@router.post("/users/{user_id}/reset-mfa")
async def reset_admin_mfa(
    user_id: UUID,
    svc: AuthService = Depends(get_auth_service),
) -> AdminUserResponse:
    result = await svc.reset_admin_mfa(user_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Admin user not found"},
        )
    return result


@router.get("/dashboard")
async def dashboard_stats(
    registry: RegistryService = Depends(get_registry_service),
    approvals: ApprovalService = Depends(get_approval_service),
) -> DashboardStats:
    counts = await registry.count_by_health()
    pending = await approvals.count_pending()

    return DashboardStats(
        server_count=counts.get("total", 0),
        healthy_servers=counts.get("healthy", 0),
        degraded_servers=counts.get("degraded", 0),
        pending_approvals=pending,
    )
