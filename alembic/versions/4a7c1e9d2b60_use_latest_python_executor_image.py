"""Use the latest Python executor image for the saved default.

Revision ID: 4a7c1e9d2b60
Revises: e95fdda94987
Create Date: 2026-10-21
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "4a7c1e9d2b60"
down_revision: str | None = "e95fdda94987"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE code_execution_config "
            "SET image_ref = 'ledwardchow/aespa-python-executor:latest' "
            "WHERE image_ref = 'ledwardchow/aespa-python-executor:0.1'"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE code_execution_config "
            "SET image_ref = 'ledwardchow/aespa-python-executor:0.1' "
            "WHERE image_ref = 'ledwardchow/aespa-python-executor:latest'"
        )
    )
