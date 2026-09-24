"""Add namespaced extension secrets.

Revision ID: 465996cd1ec3
Revises: a4c6e8f0b2d4
Create Date: 2026-09-23
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "465996cd1ec3"
down_revision: Union[str, Sequence[str], None] = "a4c6e8f0b2d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "extension_secret",
        sa.Column("namespace", sa.String(), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("namespace", "key"),
    )


def downgrade() -> None:
    op.drop_table("extension_secret")
