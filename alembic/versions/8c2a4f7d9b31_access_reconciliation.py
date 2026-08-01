"""add crawler access reconciliation setting

Revision ID: 8c2a4f7d9b31
Revises: 6f50c4a9c1e8
Create Date: 2026-07-31

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "8c2a4f7d9b31"
down_revision: Union[str, None] = "6f50c4a9c1e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "crawler_config",
        sa.Column(
            "enable_access_reconciliation",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("crawler_config", "enable_access_reconciliation")
