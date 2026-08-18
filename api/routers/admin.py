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

Schema-digest management endpoints:
  - GET  /v1/admin/mappings/stale        — list stale mappings for review
  - POST /v1/admin/mappings/{id}/review  — approve/reject a stale mapping
  - GET  /v1/admin/capabilities/{id}/ambiguity — show mapping ambiguity
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import (
    get_approval_service,
    get_auth_service,
    get_capability_service,
    get_db_session,
    get_registry_service,
    get_resource_service,
)
from api.schemas.admin import (
    AdminUserInvite,
    AdminUserResponse,
    AdminUserUpdate,
    PackBreadthRow,
    PackCohesionRow,
)

# Import capability schemas for schema-digest review endpoints
# (CapabilityMappingResponse, MappingReviewCreate, MappingReviewResponse)
# and CapabilityService for the review business logic.
from api.schemas.capability import (
    BulkRetireRequest,
    BulkRetireResponse,
    CapabilityMappingResponse,
    MappingReviewCreate,
    MappingReviewResponse,
    ReviewQueueSummary,
)
from api.schemas.dashboard import DashboardStats
from api.services.approval_service import ApprovalService
from api.services.auth_service import AuthService
from api.services.capability_service import CapabilityService
from api.services.registry_service import RegistryService
from api.services.resource_service import ResourceService

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
    request: Request,
    svc: AuthService = Depends(get_auth_service),
) -> AdminUserResponse:
    requesting_admin_id = getattr(request.state, "agent_id", None)
    if requesting_admin_id and str(user_id) == requesting_admin_id:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "self_deactivation",
                "message": "Admins cannot deactivate themselves",
            },
        )
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


@router.get("/trust-posture/pack-breadth")
async def pack_breadth(
    svc: ResourceService = Depends(get_resource_service),
) -> list[PackBreadthRow]:
    rows = await svc.get_pack_breadth()
    return [PackBreadthRow(**r) for r in rows]  # type: ignore[arg-type]


@router.get("/trust-posture/cohesion")
async def pack_cohesion(
    svc: ResourceService = Depends(get_resource_service),
) -> list[PackCohesionRow]:
    rows = await svc.get_pack_cohesion()
    return [PackCohesionRow(**r) for r in rows]  # type: ignore[arg-type]


# ============================================================================
# Schema-Digest Mapping Review Endpoints
# ============================================================================


# List all stale mappings that need admin review.
# The frontend Pending Reviews page polls this to show the review queue.
# Returns CapabilityMappingResponse[] — each stale mapping includes the
# stored tool_schema_digest so the frontend can show what changed.
# Optional ?failure_class= filters to a single reason (#447).
@router.get("/mappings/stale")
async def list_stale_mappings(
    failure_class: str | None = None,
    svc: CapabilityService = Depends(get_capability_service),
) -> list[CapabilityMappingResponse]:
    return await svc.get_stale_mappings(failure_class=failure_class)


# Live priority summary of the review queue (#447). Separates unreachable
# (hands-off) items from genuine schema changes so the blank flag hides
# real actionable work. Used by the admin UI and the external watchdog.
@router.get("/mappings/summary")
async def get_mappings_summary(
    svc: CapabilityService = Depends(get_capability_service),
) -> ReviewQueueSummary:
    return await svc.get_queue_summary()


# Bulk-retire review items without per-item review (#447). Target a whole
# failure_class ("unreachable") or an explicit list of mapping IDs. Retired
# items become 'rejected' and are removed from the queue.
@router.post("/mappings/retire")
async def bulk_retire_mappings(
    body: BulkRetireRequest,
    svc: CapabilityService = Depends(get_capability_service),
) -> BulkRetireResponse:
    if not body.failure_class and not body.mapping_ids:
        raise HTTPException(
            status_code=422,
            detail={"error": "no_target", "message": "Specify failure_class or mapping_ids"},
        )
    retired = await svc.bulk_retire(failure_class=body.failure_class, mapping_ids=body.mapping_ids)
    return BulkRetireResponse(retired=retired, failure_class=body.failure_class)


# List overdue limbo mappings — items whose pending_since exceeds the threshold (#444).
# Used by the staleness watchdog and dashboard to surface items that have been
# in limbo too long. Default threshold is 24 hours.
@router.get("/mappings/overdue")
async def list_overdue_mappings(
    threshold_hours: int = 24,
    svc: CapabilityService = Depends(get_capability_service),
) -> list[CapabilityMappingResponse]:
    return await svc.get_overdue_reviews(threshold_hours=threshold_hours)


# Review (approve or reject) a stale mapping.
# Creates a MappingReview audit record. On approval, the mapping's digest
# is recomputed from the current tool schema and status goes back to 'active'.
# On rejection, the mapping stays rejected and is skipped by routing.
# 422 is returned for invalid decisions (anything other than 'approved'/'rejected').
@router.post("/mappings/{mapping_id}/review", status_code=201)
async def review_mapping(
    mapping_id: UUID,
    body: MappingReviewCreate,
    svc: CapabilityService = Depends(get_capability_service),
) -> MappingReviewResponse:
    try:
        return await svc.review_mapping(mapping_id, body)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_decision", "message": str(exc)},
        ) from exc


# Get ambiguity details for a capability — shows all mappings with their
# status, digest, and digest match vs current tool schema.
# Useful for the admin dashboard's ambiguity visualization: when a capability
# has multiple mappings, some may be stale or have different schemas.
@router.get("/capabilities/{capability_id}/ambiguity")
async def get_ambiguity(
    capability_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> list[CapabilityMappingResponse]:
    from sqlalchemy import select

    from api.models.server import CapabilityMapping

    result = await db.execute(
        select(CapabilityMapping)
        .where(CapabilityMapping.capability_id == capability_id)
        .order_by(CapabilityMapping.created_at.desc())
    )
    mappings = result.scalars().all()
    return [
        CapabilityMappingResponse(
            id=m.id,
            capability_id=m.capability_id,
            server_id=m.server_id,
            tool_name=m.tool_name,
            input_mapping=m.input_mapping,
            output_mapping=m.output_mapping,
            is_primary=m.is_primary or True,
            routing_weight=m.routing_weight or 1.0,
            tool_schema_digest=m.tool_schema_digest,
            status=m.status,
        )
        for m in mappings
    ]


# List many-to-one capability-mapping collisions (#441).
# When multiple distinct tools map to the same normalized capability, this
# is a collision — the raw schemas may not intend semantic equivalence.
# Colliding mappings are marked pending_review and must be approved before
# they become routable.
@router.get("/capabilities/{capability_id}/collisions")
async def get_collisions(
    capability_id: UUID,
    svc: CapabilityService = Depends(get_capability_service),
) -> list[CapabilityMappingResponse]:
    return await svc.get_collisions(capability_id)
