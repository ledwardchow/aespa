"""Add the optional OpenAI refusal recovery setting.

Revision ID: c6d2f8a9b104
Revises: b8e2d4f6a1c3
Create Date: 2026-10-19
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "c6d2f8a9b104"
down_revision: Union[str, Sequence[str], None] = "b8e2d4f6a1c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "scanner_policy" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("scanner_policy")}
    if "openai_refusal_recovery_enabled" not in columns:
        op.add_column(
            "scanner_policy",
            sa.Column(
                "openai_refusal_recovery_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "scanner_policy" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("scanner_policy")}
    if "openai_refusal_recovery_enabled" in columns:
        op.drop_column("scanner_policy", "openai_refusal_recovery_enabled")
