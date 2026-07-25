"""Policy and agent class management routes.

Endpoints: POST /v1/agent-classes, GET /v1/agent-classes, GET /v1/agent-classes/{id},
POST /v1/agent-classes/{id}/trust, POST /v1/admin/policies/bundle.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import get_policy_service
from api.schemas.agent import (
    AgentClassCreate,
    AgentClassResponse,
    TrustAssignmentCreate,
    TrustAssignmentResponse,
)
from api.schemas.policy import BundleDeployRequest, OPAPolicyVersionResponse
from api.services.policy_service import OPABundleError, PolicyService

router = APIRouter(prefix="/v1", tags=["policy"])


@router.post("/agent-classes", status_code=201)
async def create_agent_class(
    body: AgentClassCreate,
    svc: PolicyService = Depends(get_policy_service),
) -> AgentClassResponse:
    """Create a new agent class. Returns 201 with the created class."""
    return await svc.create_agent_class(body)


@router.get("/agent-classes")
async def list_agent_classes(
    team_namespace: str | None = Query(None),
    svc: PolicyService = Depends(get_policy_service),
) -> list[AgentClassResponse]:
    """List agent classes, optionally filtered by team namespace."""
    return await svc.list_agent_classes(team_namespace=team_namespace)


@router.get("/agent-classes/{class_id}")
async def get_agent_class(
    class_id: UUID,
    svc: PolicyService = Depends(get_policy_service),
) -> AgentClassResponse:
    """Get a single agent class by ID. Returns 404 if not found."""
    result = await svc.get_agent_class(class_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": f"Agent class {class_id} not found"},
        )
    return result


@router.post("/agent-classes/{class_id}/trust", status_code=201)
async def set_trust(
    class_id: UUID,
    body: TrustAssignmentCreate,
    svc: PolicyService = Depends(get_policy_service),
) -> TrustAssignmentResponse:
    """Set trust assignments for an agent class. Returns 201 with the assignment."""
    return await svc.set_trust(class_id, body)


@router.post("/admin/policies/bundle", status_code=201)
async def deploy_bundle(
    body: BundleDeployRequest,
    svc: PolicyService = Depends(get_policy_service),
) -> OPAPolicyVersionResponse:
    """Deploy a new OPA Rego policy bundle. Returns 400 if the bundle is invalid."""
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
