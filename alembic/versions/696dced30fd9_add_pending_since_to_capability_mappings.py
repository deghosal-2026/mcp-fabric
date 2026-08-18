"""add pending_since to capability_mappings

Revision ID: 696dced30fd9
Revises: 2ebc704823ae
Create Date: 2026-08-16 20:32:36.050231

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "696dced30fd9"
down_revision: str | Sequence[str] | None = "2ebc704823ae"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add pending_since to capability_mappings for stale-review age alerts (#444)."""
    op.add_column(
        "capability_mappings",
        sa.Column("pending_since", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_mappings_pending_since", "capability_mappings", ["pending_since"])


def downgrade() -> None:
    """Remove pending_since from capability_mappings."""
    op.drop_index("idx_mappings_pending_since", table_name="capability_mappings")
    op.drop_column("capability_mappings", "pending_since")
