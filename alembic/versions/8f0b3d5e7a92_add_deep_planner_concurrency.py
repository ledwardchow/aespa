"""add Deep planner concurrency

Revision ID: 8f0b3d5e7a92
Revises: 7e9a2c4d6f81
Create Date: 2026-09-13
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "8f0b3d5e7a92"
down_revision: Union[str, None] = "7e9a2c4d6f81"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "deep_scan_config",
        sa.Column(
            "max_concurrent_planners",
            sa.Integer(),
            nullable=False,
            server_default="4",
        ),
    )


def downgrade() -> None:
    op.drop_column("deep_scan_config", "max_concurrent_planners")
