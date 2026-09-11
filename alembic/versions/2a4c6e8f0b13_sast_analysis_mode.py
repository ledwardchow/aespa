"""add selectable SAST analysis mode

Revision ID: 2a4c6e8f0b13
Revises: 7c8d9e0f1a23
Create Date: 2026-09-10
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "2a4c6e8f0b13"
down_revision: Union[str, None] = "7c8d9e0f1a23"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if "sast_run" not in sa.inspect(op.get_bind()).get_table_names():
        return
    op.add_column(
        "sast_run",
        sa.Column(
            "analysis_mode", sa.String(), nullable=False, server_default="light"
        ),
    )
    op.create_index("ix_sast_run_analysis_mode", "sast_run", ["analysis_mode"])


def downgrade() -> None:
    if "sast_run" not in sa.inspect(op.get_bind()).get_table_names():
        return
    op.drop_index("ix_sast_run_analysis_mode", table_name="sast_run")
    op.drop_column("sast_run", "analysis_mode")
