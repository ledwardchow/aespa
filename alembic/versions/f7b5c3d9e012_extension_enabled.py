"""add extension enabled state

Revision ID: f7b5c3d9e012
Revises: d6a4f2c8e901
Create Date: 2026-09-20
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "f7b5c3d9e012"
down_revision: Union[str, Sequence[str], None] = "d6a4f2c8e901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "extension_setting" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("extension_setting")}
    if "enabled" not in columns:
        op.add_column(
            "extension_setting",
            sa.Column(
                "enabled", sa.Boolean(), nullable=False, server_default=sa.true()
            ),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "extension_setting" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("extension_setting")}
    if "enabled" in columns:
        op.drop_column("extension_setting", "enabled")
