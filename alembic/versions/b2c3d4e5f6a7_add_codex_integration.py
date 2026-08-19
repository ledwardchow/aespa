"""add global Codex integration settings

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-11
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "codex_integration_config",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("executable_path", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "run_pause",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_kind", sa.String(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("reset_at", sa.DateTime(), nullable=True),
        sa.Column("message", sa.String(), nullable=False),
        sa.Column("snapshot_json", sa.String(), nullable=False),
        sa.Column("resume_stage", sa.String(), nullable=True),
        sa.Column("paused_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_kind", "run_id", name="uq_run_pause"),
    )
    op.create_index("ix_run_pause_run_kind", "run_pause", ["run_kind"])
    op.create_index("ix_run_pause_run_id", "run_pause", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_run_pause_run_id", table_name="run_pause")
    op.drop_index("ix_run_pause_run_kind", table_name="run_pause")
    op.drop_table("run_pause")
    op.drop_table("codex_integration_config")
