"""add durable ALICE goals

Revision ID: 91c4e7a2d5b8
Revises: 8b4d2e6f9a10
Create Date: 2026-09-04
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "91c4e7a2d5b8"
down_revision: str | None = "8b4d2e6f9a10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "alice_goal",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("test_run_id", sa.Integer(), nullable=False),
        sa.Column("run_kind", sa.String(), nullable=False),
        sa.Column("session_key", sa.String(), nullable=False),
        sa.Column("objective", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("checkpoint_json", sa.String(), nullable=False),
        sa.Column("completion_json", sa.String(), nullable=False),
        sa.Column("blocker", sa.String(), nullable=False),
        sa.Column("pause_reason", sa.String(), nullable=False),
        sa.Column("cycle_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("paused_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["test_run_id"], ["run_identity.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "run_kind", "test_run_id", "session_key", name="uq_alice_goal_owner"
        ),
    )
    op.create_index("ix_alice_goal_test_run_id", "alice_goal", ["test_run_id"])
    op.create_index("ix_alice_goal_run_kind", "alice_goal", ["run_kind"])
    op.create_index("ix_alice_goal_session_key", "alice_goal", ["session_key"])
    op.create_index("ix_alice_goal_status", "alice_goal", ["status"])


def downgrade() -> None:
    op.drop_index("ix_alice_goal_status", table_name="alice_goal")
    op.drop_index("ix_alice_goal_session_key", table_name="alice_goal")
    op.drop_index("ix_alice_goal_run_kind", table_name="alice_goal")
    op.drop_index("ix_alice_goal_test_run_id", table_name="alice_goal")
    op.drop_table("alice_goal")
