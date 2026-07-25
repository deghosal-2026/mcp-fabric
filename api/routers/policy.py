"""Policy and agent class management routes.

Manages agent classes (role-based groups), trust assignments (what each class
is allowed to do), agent identities (API keys/tokens for machine auth), and
OPA Rego policy bundles for fine-grained authorization.

User journeys:
  - Admin creates agent classes (POST /v1/agent-classes) — e.g. "read-only",
    "operator", "admin" — each with distinct trust levels
  - Admin sets trust assignments for a class (POST .../{id}/trust) — this
    defines which operations the class can perform
  - Admin creates agent identities with API tokens (POST .../{id}/identities)
    so automated agents can authenticate
  - Admin rotates or revokes agent tokens (POST /v1/agent-identities/{id}/rotate,
    .../revoke) for security maintenance
  - Admin deploys OPA Rego policy bundles (POST /v1/admin/policies/bundle) for
    fine-grained, policy-as-code authorization beyond trust levels

Architectural notes:
  - Agent identities use the AuthService (not PolicyService) because token
    creation/rotation is an auth concern, not a policy concern.
  - OPA bundle deployment is WIP — the service validates Rego syntax before
    storing, but the OPA sidecar integration is not yet wired up.
  - Trust assignments and OPA policies are complementary: trust sets broad
    boundaries, OPA enforces fine-grained rules within those boundaries.

Endpoints: POST /v1/agent-classes, GET /v1/agent-classes, GET /v1/agent-classes/{id},
POST /v1/agent-classes/{id}/trust, POST /v1/agent-classes/{id}/identities,
GET /v1/agent-classes/{id}/identities, POST /v1/agent-identities/{id}/rotate,
POST /v1/agent-identities/{id}/revoke, POST /v1/admin/policies/bundle.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from starlette import status

from api.dependencies import get_auth_service, get_policy_service
from api.schemas.agent import (
    AgentClassCreate,
    AgentClassResponse,
    AgentIdentityCreate,
    AgentIdentityResponse,
    TrustAssignmentCreate,
    TrustAssignmentResponse,
)
from api.schemas.policy import BundleDeployRequest, OPAPolicyVersionResponse
from api.services.auth_service import AuthService
from api.services.policy_service import OPABundleError, PolicyService

router = APIRouter(prefix="/v1", tags=["policy"])


# Create a new agent class (role group), e.g. "data-scientist" or "read-only-bot".
# 201 = resource created. Agent classes are the primary grouping mechanism for
# trust, policy, and pack assignments.
@router.post("/agent-classes", status_code=201)
async def create_agent_class(
    body: AgentClassCreate,
    svc: PolicyService = Depends(get_policy_service),
) -> AgentClassResponse:
    return await svc.create_agent_class(body)


# List all agent classes, optionally filtered by team namespace.
# The team namespace filter enables multi-team deployments where each
# team manages their own agent classes without seeing other teams'.
@router.get("/agent-classes")
async def list_agent_classes(
    team_namespace: str | None = Query(None),
    svc: PolicyService = Depends(get_policy_service),
) -> list[AgentClassResponse]:
    return await svc.list_agent_classes(team_namespace=team_namespace)


# Get a single agent class by ID. Returns 404 if not found.
# Used by the class detail view and by admins reviewing class configuration
# before modifying trust or pack assignments.
@router.get("/agent-classes/{class_id}")
async def get_agent_class(
    class_id: UUID,
    svc: PolicyService = Depends(get_policy_service),
) -> AgentClassResponse:
    result = await svc.get_agent_class(class_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": f"Agent class {class_id} not found"},
        )
    return result


# Set trust level assignments for an agent class. Trust levels define what
# operations the class can perform — e.g. "read-only", "restricted-write",
# "full-admin". This is a replace-all operation (not additive), so the caller
# must send the complete list of trust assignments.
@router.post("/agent-classes/{class_id}/trust", status_code=201)
async def set_trust(
    class_id: UUID,
    body: TrustAssignmentCreate,
    svc: PolicyService = Depends(get_policy_service),
) -> TrustAssignmentResponse:
    return await svc.set_trust(class_id, body)


# Create an agent identity (API key / token) for a given agent class.
# The returned AgentIdentityResponse includes the raw token — this is the
# ONLY time the token is visible; subsequent GETs will not reveal it.
# 404 if the agent class does not exist.
@router.post("/agent-classes/{class_id}/identities", status_code=201)
async def create_agent_identity(
    class_id: UUID,
    body: AgentIdentityCreate,
    svc: AuthService = Depends(get_auth_service),
) -> AgentIdentityResponse:
    try:
        body.agent_class_id = class_id
        return await svc.create_agent_identity(body)
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": str(exc)},
        ) from exc


# List all agent identities for a given agent class.
# Returns metadata only (id, name, status, creation time) — never the
# raw token. The token is only returned once at creation time.
@router.get("/agent-classes/{class_id}/identities")
async def list_agent_identities(
    class_id: UUID,
    svc: AuthService = Depends(get_auth_service),
) -> list[AgentIdentityResponse]:
    return await svc.list_agent_identities(class_id)


# Rotate (regenerate) the token for an active agent identity.
# Returns the new token in the response. The old token is immediately
# invalidated. 404 if the identity does not exist.
@router.post("/agent-identities/{identity_id}/rotate")
async def rotate_agent_token(
    identity_id: UUID,
    svc: AuthService = Depends(get_auth_service),
) -> AgentIdentityResponse:
    try:
        return await svc.rotate_agent_token(identity_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": str(exc)},
        ) from exc


# Revoke an agent identity, preventing further token usage.
# 204 No Content on success (standard for deletion-style operations).
# The identity record is preserved for audit purposes (soft delete).
# 404 if the identity does not exist.
@router.post("/agent-identities/{identity_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_agent_token(
    identity_id: UUID,
    svc: AuthService = Depends(get_auth_service),
) -> None:
    try:
        await svc.revoke_agent_token(identity_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": str(exc)},
        ) from exc


# List deployed policy versions for the admin UI.
# Returns versions ordered by most recent deployment first.
@router.get("/admin/policies")
async def list_policy_versions(
    svc: PolicyService = Depends(get_policy_service),
) -> list[OPAPolicyVersionResponse]:
    versions = await svc.get_policy_versions(limit=50)
    return [
        OPAPolicyVersionResponse(
            id=v.id,
            version=v.version,
            bundle_hash=v.bundle_hash,
            deployed_at=v.deployed_at,
            deployed_by=v.deployed_by,
            rego_content=v.rego_content,
        )
        for v in versions
    ]


# Deploy a new OPA Rego policy bundle. The bundle contains Rego policy code
# that the OPA sidecar evaluates for authorization decisions. The service
# validates Rego syntax before accepting the bundle.
# 400 = bundle is invalid (syntax error or validation failure).
# Returns the version metadata including a bundle_hash for change tracking.
@router.post("/admin/policies/bundle", status_code=201)
async def deploy_bundle(
    body: BundleDeployRequest,
    svc: PolicyService = Depends(get_policy_service),
) -> OPAPolicyVersionResponse:
    try:
        version = await svc.deploy_bundle(
            rego_content=body.rego_content,
            deployed_by=body.deployed_by,
        )
        return OPAPolicyVersionResponse(
            id=version.id,
            version=version.version,
            bundle_hash=version.bundle_hash,
            deployed_at=version.deployed_at,
            deployed_by=version.deployed_by,
            rego_content=version.rego_content,
        )
    except OPABundleError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": "bundle_error", "message": str(exc)},
        ) from exc
