"""ORM model for OPA Rego policy version tracking.

Maintains a history of deployed Rego bundles for audit and rollback.
"""

from sqlalchemy import Column, DateTime, Index, String, Text, func

from api.models.base import Base, UUIDMixin


class OPAPolicyVersion(UUIDMixin, Base):
    """A versioned snapshot of deployed OPA Rego policy."""

    __tablename__ = "opa_policy_versions"

    version = Column(String(50), nullable=False)
    bundle_hash = Column(String(64), nullable=True)
    deployed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    deployed_by = Column(String(255), nullable=True)
    rego_content = Column(Text, nullable=False)

    __table_args__ = (Index("idx_opapolicy_version", "version"),)
