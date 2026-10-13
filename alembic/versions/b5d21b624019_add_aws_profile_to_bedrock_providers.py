"""Save an AWS profile name on Bedrock providers and model configs.

Revision ID: b5d21b624019
Revises: 47c7f6cf424a
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "b5d21b624019"
down_revision: Union[str, Sequence[str], None] = "47c7f6cf424a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table_name in ("llm_provider_config", "llm_config"):
        if not inspector.has_table(table_name):
            continue
        columns = {item["name"] for item in inspector.get_columns(table_name)}
        if "aws_profile" not in columns:
            op.add_column(
                table_name, sa.Column("aws_profile", sa.String(), nullable=True)
            )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table_name in ("llm_config", "llm_provider_config"):
        if not inspector.has_table(table_name):
            continue
        columns = {item["name"] for item in inspector.get_columns(table_name)}
        if "aws_profile" in columns:
            op.drop_column(table_name, "aws_profile")
