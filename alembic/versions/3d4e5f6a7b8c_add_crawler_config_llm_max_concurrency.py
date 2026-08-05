"""add_crawler_config_llm_max_concurrency

Revision ID: 3d4e5f6a7b8c
Revises: 2c3ed73c25da
Create Date: 2026-08-02 11:33:30

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3d4e5f6a7b8c"
down_revision: Union[str, None] = "2c3ed73c25da"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("crawler_config", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("llm_max_concurrency", sa.Integer(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("crawler_config", schema=None) as batch_op:
        batch_op.drop_column("llm_max_concurrency")
