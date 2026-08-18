"""add failure_class to capability_mappings

Revision ID: c7a9b1e52f41
Revises: 696dced30fd9
Create Date: 2026-08-17 09:12:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7a9b1e52f41"
down_revision: str | Sequence[str] | None = "696dced30fd9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add failure_class to capability_mappings for queue prioritization (#447).

    failure_class records why a mapping entered the review queue:
      'unreachable'     - MCP server could not be reached during re-inspection
      'timeout'         - list_tools timed out during re-inspection
      'drifted'         - tool schema changed vs last verified digest
      'schema_mismatch' - capability input/output schema changed (collision)
    NULL only for limbo rows created before this migration.
    """
    op.add_column(
        "capability_mappings",
        sa.Column("failure_class", sa.String(20), nullable=True),
    )
    op.create_index("idx_mappings_failure_class", "capability_mappings", ["failure_class"])


def downgrade() -> None:
    """Remove failure_class from capability_mappings."""
    op.drop_index("idx_mappings_failure_class", table_name="capability_mappings")
    op.drop_column("capability_mappings", "failure_class")