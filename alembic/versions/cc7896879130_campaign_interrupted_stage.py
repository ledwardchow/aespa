"""campaign_interrupted_stage

Revision ID: cc7896879130
Revises: 00c6c82b48b7
Create Date: 2026-08-02 17:45:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cc7896879130"
down_revision: Union[str, None] = "00c6c82b48b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("assessment_campaign", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "interrupted_stage",
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=True,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("assessment_campaign", schema=None) as batch_op:
        batch_op.drop_column("interrupted_stage")
