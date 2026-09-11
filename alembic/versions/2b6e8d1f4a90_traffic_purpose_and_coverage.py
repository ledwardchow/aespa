"""add traffic purpose and coverage association

Revision ID: 2b6e8d1f4a90
Revises: 7a9d3c1e5f20
Create Date: 2026-09-08
"""

from typing import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "2b6e8d1f4a90"
down_revision: str | None = "7a9d3c1e5f20"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("traffic_entry", sa.Column("purpose", sa.String(), nullable=True))
    op.add_column(
        "traffic_entry", sa.Column("coverage_cell_id", sa.Integer(), nullable=True)
    )
    op.create_index(
        "ix_traffic_entry_coverage_cell_id",
        "traffic_entry",
        ["coverage_cell_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_traffic_entry_coverage_cell_id", table_name="traffic_entry")
    op.drop_column("traffic_entry", "coverage_cell_id")
    op.drop_column("traffic_entry", "purpose")
