from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class BundleDeployRequest(BaseModel):
    rego_content: str
    deployed_by: str | None = None


class OPAPolicyVersionResponse(BaseModel):
    id: UUID
    version: str
    bundle_hash: str | None = None
    deployed_at: datetime
    deployed_by: str | None = None
    rego_content: str

    model_config = {"from_attributes": True}
