"""store the endpoint base URL for monthly LLM usage rows

Revision ID: a7c8e9f0b1d2
Revises: 9d1e2f3a4b5c
Create Date: 2026-08-01

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "a7c8e9f0b1d2"
down_revision: Union[str, None] = "9d1e2f3a4b5c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("llm_usage_month", sa.Column("base_url", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("llm_usage_month", "base_url")
