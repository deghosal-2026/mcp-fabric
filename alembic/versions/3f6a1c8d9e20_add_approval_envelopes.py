"""add approval_envelopes for budgeted approvals

Revision ID: 3f6a1c8d9e20
Revises: c7a9b1e52f41
Create Date: 2026-08-17 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3f6a1c8d9e20"
down_revision: str | Sequence[str] | None = "c7a9b1e52f41"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create approval_envelopes to support scoped, expiring approval budgets (#442)."""
    op.create_table(
        "approval_envelopes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scope", sa.String(100), nullable=False),
        sa.Column("budget", sa.Integer(), nullable=False),
        sa.Column("remaining", sa.Integer(), nullable=False),
        sa.Column(
            "expires_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_envelope_scope", "approval_envelopes", ["scope"])


def downgrade() -> None:
    """Drop approval_envelopes and its scope index."""
    op.drop_index("idx_envelope_scope", table_name="approval_envelopes")
    op.drop_table("approval_envelopes")