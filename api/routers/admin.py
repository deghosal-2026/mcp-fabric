"""Admin user management routes.

Endpoints: POST /v1/admin/users/invite, GET /v1/admin/users,
GET /v1/admin/users/{id}, PATCH /v1/admin/users/{id},
POST /v1/admin/users/{id}/deactivate, POST /v1/admin/users/{id}/unlock,
POST /v1/admin/users/{id}/reset-mfa.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_auth_service
from api.schemas.admin import AdminUserInvite, AdminUserResponse, AdminUserUpdate
from api.services.auth_service import AuthService

router = APIRouter(prefix="/v1/admin", tags=["admin"])


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


@router.get("/users")
async def list_admin_users(
    svc: AuthService = Depends(get_auth_service),
) -> list[AdminUserResponse]:
    return await svc.list_admins()


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


@router.post("/users/{user_id}/deactivate")
async def deactivate_admin_user(
    user_id: UUID,
    svc: AuthService = Depends(get_auth_service),
) -> AdminUserResponse:
    result = await svc.deactivate_admin(user_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Admin user not found"},
        )
    return result


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
