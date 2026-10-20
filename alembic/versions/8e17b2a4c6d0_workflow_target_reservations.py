"""Reserve exact grouped-route targets for workflow attempts.

Revision ID: 8e17b2a4c6d0
Revises: 45623834b15e
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "8e17b2a4c6d0"
down_revision: str | None = "45623834b15e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("workflow_target_reservation"):
        op.create_table(
            "workflow_target_reservation",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("test_run_id", sa.Integer(), nullable=False),
            sa.Column("owner_key", sa.String(), nullable=False),
            sa.Column("target_url", sa.String(), nullable=False),
            sa.Column("route_pattern", sa.String(), nullable=False),
            sa.Column("example_url", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["test_run_id"], ["run_identity.id"], ondelete="CASCADE"
            ),
            sa.UniqueConstraint(
                "test_run_id", "owner_key", name="uq_workflow_target_owner"
            ),
            sa.UniqueConstraint(
                "test_run_id", "target_url", name="uq_workflow_target_url"
            ),
        )
    if "ix_workflow_target_reservation_test_run_id" not in {
        index["name"]
        for index in sa.inspect(op.get_bind()).get_indexes(
            "workflow_target_reservation"
        )
    }:
        op.create_index(
            "ix_workflow_target_reservation_test_run_id",
            "workflow_target_reservation",
            ["test_run_id"],
        )


def downgrade() -> None:
    op.drop_index(
        "ix_workflow_target_reservation_test_run_id",
        table_name="workflow_target_reservation",
    )
    op.drop_table("workflow_target_reservation")
