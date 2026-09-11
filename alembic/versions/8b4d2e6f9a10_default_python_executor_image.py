"""default Python executor image and Test Lead role

Revision ID: 8b4d2e6f9a10
Revises: 694ea9e58709
Create Date: 2026-09-04
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "8b4d2e6f9a10"
down_revision: str | None = "694ea9e58709"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE code_execution_config "
            "SET image_ref = 'ledwardchow/aespa-python-executor:0.1' "
            "WHERE image_ref = 'aespa-python-executor:0.1'"
        )
    )
    op.execute(
        sa.text(
            "UPDATE code_execution_config "
            "SET allowed_roles_json = '[\"alice\",\"specialist\",\"test_lead\"]' "
            "WHERE allowed_roles_json IN "
            "('[\"alice\",\"specialist\"]', '[\"alice\", \"specialist\"]')"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE code_execution_config "
            "SET image_ref = 'aespa-python-executor:0.1' "
            "WHERE image_ref = 'ledwardchow/aespa-python-executor:0.1'"
        )
    )
    op.execute(
        sa.text(
            "UPDATE code_execution_config "
            "SET allowed_roles_json = '[\"alice\",\"specialist\"]' "
            "WHERE allowed_roles_json = '[\"alice\",\"specialist\",\"test_lead\"]'"
        )
    )
