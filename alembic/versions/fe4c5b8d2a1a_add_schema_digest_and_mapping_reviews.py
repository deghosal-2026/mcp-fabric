"""add tool_schema_digest, status to capability_mappings and mapping_reviews table

Revision ID: fe4c5b8d2a1a
Revises: de7521eacb7b
Create Date: 2026-07-25 22:15:00.000000
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "fe4c5b8d2a1a"
down_revision: str | None = "de7521eacb7b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Compute a deterministic SHA-256 digest from a tool's name, input schema, and output schema.
# This digest is stored on the mapping to detect schema drift during server inspection.
# Input/output schemas are JSON-serialized with sorted keys for consistent hashing.
def _compute_digest(tool_name: str, input_schema: object, output_schema: object) -> str:
    raw = tool_name
    raw += json.dumps(input_schema, sort_keys=True, default=str) if input_schema else ""
    raw += json.dumps(output_schema, sort_keys=True, default=str) if output_schema else ""
    return hashlib.sha256(raw.encode()).hexdigest()


def upgrade() -> None:
    # --- Phase 1: Add columns to capability_mappings ---
    # tool_schema_digest stores the SHA-256 hash of the tool schema at mapping creation/review time.
    # status tracks whether the mapping is active, stale, or rejected.
    op.add_column(
        "capability_mappings",
        sa.Column("tool_schema_digest", sa.String(64), nullable=True),
    )
    op.add_column(
        "capability_mappings",
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
    )
    # Index for efficient lookups by status (e.g., find all stale mappings).
    op.create_index(
        "idx_mappings_status",
        "capability_mappings",
        ["status"],
    )
    # Unique constraint prevents duplicate mappings with the same capability, server, AND digest.
    # A digest change forces a new mapping or a review, preventing silent schema drift.
    op.create_index(
        "idx_mappings_digest_unique",
        "capability_mappings",
        ["capability_id", "server_id", "tool_schema_digest"],
        unique=True,
        postgresql_nulls_not_distinct=False,
    )

    # --- Phase 2: Create mapping_reviews table ---
    # Records every approve/reject decision on a mapping, including the digest
    # before and after the review for full audit trail.
    op.create_table(
        "mapping_reviews",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "mapping_id",
            sa.UUID(),
            sa.ForeignKey("capability_mappings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("previous_digest", sa.String(64), nullable=True),
        sa.Column("new_digest", sa.String(64), nullable=True),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "reviewed_by",
            sa.UUID(),
            sa.ForeignKey("admin_users.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_mapping_reviews_mapping",
        "mapping_reviews",
        ["mapping_id"],
    )
    op.create_index(
        "idx_mapping_reviews_decision",
        "mapping_reviews",
        ["decision"],
    )

    # --- Phase 3: Backfill existing mappings ---
    # For every existing mapping WITHOUT a digest, compute one by joining
    # capability_mappings -> server_tools on server_id + tool_name.
    conn = op.get_bind()
    meta = sa.MetaData()
    meta.reflect(bind=conn, only=("capability_mappings", "server_tools"))
    cm = meta.tables["capability_mappings"]
    st = meta.tables["server_tools"]

    join = cm.join(st, sa.and_(cm.c.server_id == st.c.server_id, cm.c.tool_name == st.c.tool_name))
    stmt = (
        sa.select(cm.c.id, st.c.tool_name, st.c.input_schema, st.c.output_schema)
        .select_from(join)
        .where(cm.c.tool_schema_digest.is_(None))
    )
    rows = conn.execute(stmt).fetchall()

    # Compute the digest from tool_name + input_schema + output_schema (SHA-256)
    # and write it back to the mapping row along with an initial "active" status.
    for row in rows:
        digest = _compute_digest(row.tool_name, row.input_schema, row.output_schema)
        conn.execute(
            cm.update().where(cm.c.id == row.id).values(tool_schema_digest=digest, status="active")
        )


# Reverses the upgrade: drop mapping_reviews table and its indexes, then
# remove the columns and indexes added to capability_mappings.
def downgrade() -> None:
    op.drop_index("idx_mapping_reviews_decision", table_name="mapping_reviews")
    op.drop_index("idx_mapping_reviews_mapping", table_name="mapping_reviews")
    op.drop_table("mapping_reviews")

    op.drop_index("idx_mappings_digest_unique", table_name="capability_mappings")
    op.drop_index("idx_mappings_status", table_name="capability_mappings")
    op.drop_column("capability_mappings", "status")
    op.drop_column("capability_mappings", "tool_schema_digest")
