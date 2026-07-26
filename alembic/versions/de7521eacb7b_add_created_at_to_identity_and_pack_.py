"""add created_at to identity and pack resource bindings

Revision ID: de7521eacb7b
Revises: b921b570b5de
Create Date: 2026-07-25 12:04:52.745560

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'de7521eacb7b'
down_revision: str | Sequence[str] | None = 'b921b570b5de'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'identity_resource_bindings',
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    )
    op.add_column(
        'pack_resource_bindings',
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    )


def downgrade() -> None:
    op.drop_column('pack_resource_bindings', 'created_at')
    op.drop_column('identity_resource_bindings', 'created_at')
