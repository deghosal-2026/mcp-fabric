"""ORM model for Open Policy Agent (OPA) policy version history.

The fabric uses OPA to evaluate authorization decisions for agent-capability
pairs. Each policy version stores the raw Rego source code alongside metadata
so that administrators can:
  - Inspect what policy was active at any point in time.
  - Roll back to a previous version if a policy change causes issues.
  - Audit who deployed which policy and when.

Only the latest deployed policy is actually loaded into OPA at runtime, but
the full version history is preserved in this table.
"""

from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from api.models.base import Base, UUIDMixin


class OPAPolicyVersion(UUIDMixin, Base):
    """A specific version of an OPA Rego policy deployed to the fabric runtime.

    Table: opa_policy_versions

    Each row represents one deployment of a Rego policy bundle. Deploying a
    new version creates a new row — existing rows are never modified, ensuring
    a complete version history.

    Indexing:
        idx_opapolicy_version – Fast lookup by version string (e.g. "v1.2.3").

    Columns:
        version        – Human-readable version label (e.g. "v1", "2024-03-15-01").
                         Not necessarily numeric; the deployer chooses the scheme.
        bundle_hash    – SHA-256 of the deployed gzipped bundle file, for integrity
                         verification and to detect duplicate deployments.
        deployed_at    – When this version was deployed (server default now()).
        deployed_by    – Identity of the deployer (admin username or CI system name).
        rego_content   – The full Rego source code. Stored as Text rather than JSON
                         because Rego is plaintext policy language.
    """

    __tablename__ = "opa_policy_versions"

    version: Mapped[str] = mapped_column(String(50), nullable=False)
    bundle_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    deployed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    deployed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rego_content: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (Index("idx_opapolicy_version", "version"),)
