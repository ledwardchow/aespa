"""add_llm_max_concurrency_to_test_run

Revision ID: 2c3ed73c25da
Revises: e1a7b9c3d5f0
Create Date: 2026-08-02 11:25:52

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '2c3ed73c25da'
down_revision: Union[str, None] = 'e1a7b9c3d5f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('test_run', schema=None) as batch_op:
        batch_op.add_column(sa.Column('llm_max_concurrency', sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('test_run', schema=None) as batch_op:
        batch_op.drop_column('llm_max_concurrency')
