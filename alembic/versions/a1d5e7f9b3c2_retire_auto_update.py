"""add scanner policy Retire.js auto-update setting

Revision ID: a1d5e7f9b3c2
Revises: c3e7a9d1f5b2
Create Date: 2026-10-09
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "a1d5e7f9b3c2"
down_revision: Union[str, Sequence[str], None] = "c3e7a9d1f5b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "scanner_policy" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("scanner_policy")}
    if "retire_auto_update" not in columns:
        op.add_column(
            "scanner_policy",
            sa.Column(
                "retire_auto_update",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "scanner_policy" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("scanner_policy")}
    if "retire_auto_update" in columns:
        op.drop_column("scanner_policy", "retire_auto_update")
