"""add component mapper config

Revision ID: 7f9d1cf4e066
Revises: b8e2f4a6c901
Create Date: 2026-08-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "7f9d1cf4e066"
down_revision: Union[str, None] = "b8e2f4a6c901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "component_mapper_config",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("max_tool_calls", sa.Integer(), nullable=False),
        sa.Column("max_source_files", sa.Integer(), nullable=False),
        sa.Column("max_source_bytes", sa.Integer(), nullable=False),
        sa.Column("max_facts", sa.Integer(), nullable=False),
        sa.Column("max_concurrent", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("component_mapper_config")
