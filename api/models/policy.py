from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from api.models.base import Base, UUIDMixin


class OPAPolicyVersion(UUIDMixin, Base):
    __tablename__ = "opa_policy_versions"

    version: Mapped[str] = mapped_column(String(50), nullable=False)
    bundle_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    deployed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    deployed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rego_content: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (Index("idx_opapolicy_version", "version"),)