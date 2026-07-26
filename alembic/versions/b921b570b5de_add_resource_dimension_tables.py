"""add resource dimension tables

Revision ID: b921b570b5de
Revises: 04d6cbcce89a
Create Date: 2026-07-25 11:34:20.210760

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'b921b570b5de'
down_revision: str | Sequence[str] | None = '04d6cbcce89a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('resource_dimensions',
        sa.Column('capability_id', sa.UUID(), nullable=False),
        sa.Column('dimension_key', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['capability_id'], ['capabilities.id'],
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_rd_capability', 'resource_dimensions',
                    ['capability_id'], unique=False)
    op.create_index('idx_rd_dimension', 'resource_dimensions',
                    ['dimension_key'], unique=False)
    op.create_index('uq_rd_capability_dimension', 'resource_dimensions',
                    ['capability_id', 'dimension_key'], unique=True)

    op.create_table('dimension_value_map',
        sa.Column('resource_dimension_id', sa.UUID(), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False, server_default='param'),
        sa.Column('param_path', sa.String(length=255), nullable=True),
        sa.Column('constant_value', sa.String(length=255), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['resource_dimension_id'],
                                ['resource_dimensions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_dvm_dimension', 'dimension_value_map',
                    ['resource_dimension_id'], unique=False)

    op.create_table('identity_resource_bindings',
        sa.Column('agent_identity_id', sa.UUID(), nullable=False),
        sa.Column('dimension_key', sa.String(length=100), nullable=False),
        sa.Column('allowed_value', sa.String(length=255), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['agent_identity_id'], ['agent_identities.id'],
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_irb_identity', 'identity_resource_bindings',
                    ['agent_identity_id'], unique=False)
    op.create_index('idx_irb_dimension', 'identity_resource_bindings',
                    ['dimension_key'], unique=False)
    op.create_index('uq_irb_identity_dimension_value', 'identity_resource_bindings',
                    ['agent_identity_id', 'dimension_key', 'allowed_value'], unique=True)

    op.create_table('pack_resource_bindings',
        sa.Column('pack_id', sa.UUID(), nullable=False),
        sa.Column('dimension_key', sa.String(length=100), nullable=False),
        sa.Column('allowed_value', sa.String(length=255), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['pack_id'], ['capability_packs.id'],
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_prb_pack', 'pack_resource_bindings',
                    ['pack_id'], unique=False)
    op.create_index('idx_prb_dimension', 'pack_resource_bindings',
                    ['dimension_key'], unique=False)
    op.create_index('uq_prb_pack_dimension_value', 'pack_resource_bindings',
                    ['pack_id', 'dimension_key', 'allowed_value'], unique=True)


def downgrade() -> None:
    op.drop_table('pack_resource_bindings')
    op.drop_table('identity_resource_bindings')
    op.drop_table('dimension_value_map')
    op.drop_table('resource_dimensions')
