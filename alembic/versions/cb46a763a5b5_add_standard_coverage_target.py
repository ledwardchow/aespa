"""add standard coverage target

Revision ID: cb46a763a5b5
Revises: a8f2c6d9e4b1
Create Date: 2026-09-03 21:39:54.677136

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "cb46a763a5b5"
down_revision: Union[str, None] = "a8f2c6d9e4b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scanner_policy",
        sa.Column(
            "standard_coverage_percent",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("60"),
        ),
    )


def downgrade() -> None:
    op.drop_column("scanner_policy", "standard_coverage_percent")
