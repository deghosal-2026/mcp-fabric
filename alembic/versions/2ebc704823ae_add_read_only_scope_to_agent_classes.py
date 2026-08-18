"""add read-only scope to agent classes

Revision ID: 2ebc704823ae
Revises: fe4c5b8d2a1a
Create Date: 2026-08-16 19:49:16.499145

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2ebc704823ae"
down_revision: str | Sequence[str] | None = "fe4c5b8d2a1a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add is_read_only flag to agent_classes (read-scoped agents)."""
    op.add_column(
        "agent_classes",
        sa.Column("is_read_only", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.alter_column("agent_classes", "is_read_only", server_default=None)


def downgrade() -> None:
    """Remove is_read_only flag from agent_classes."""
    op.drop_column("agent_classes", "is_read_only")
