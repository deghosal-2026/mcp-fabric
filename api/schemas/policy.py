"""Pydantic schemas for OPA policy bundle deployment.

Endpoints:
  POST /api/v1/policy/deploy -> BundleDeployRequest -> OPAPolicyVersionResponse
  GET  /api/v1/policy/versions -> list[OPAPolicyVersionResponse]
  GET  /api/v1/policy/versions/{id} -> OPAPolicyVersionResponse
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class BundleDeployRequest(BaseModel):
    """Request body for deploying a new OPA policy version.

    POST /api/v1/policy/deploy

    Fields:
        rego_content: The full Rego source code for the policy bundle.
                      This is validated for syntactic correctness before
                      storage (semantic validation is done by OPA at load time).
        deployed_by:  Optional identity of the deployer (admin username or
                      CI system name). If omitted, defaults to the authenticated
                      user from the request context.
    """

    rego_content: str
    deployed_by: str | None = None


class OPAPolicyVersionResponse(BaseModel):
    """OPA policy version representation returned by the API.

    model_config = {"from_attributes": True} for ORM conversion.

    Matches the OPAPolicyVersion ORM model. Includes the full rego_content
    so the admin UI can display and diff policy versions. The bundle_hash
    is a SHA-256 for integrity verification.
    """

    id: UUID
    version: str
    bundle_hash: str | None = None
    deployed_at: datetime
    deployed_by: str | None = None
    rego_content: str

    model_config = {"from_attributes": True}
