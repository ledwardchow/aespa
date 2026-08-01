"""add browser debug settings

Revision ID: 6f50c4a9c1e8
Revises: 0044cbef2700
Create Date: 2026-07-31

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel

from alembic import op

revision: str = "6f50c4a9c1e8"
down_revision: Union[str, None] = "0044cbef2700"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "browser_debug_config",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "browser_engine", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column("browser_visible", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("browser_debug_config")
