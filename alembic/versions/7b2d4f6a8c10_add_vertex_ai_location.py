"""add Vertex AI provider location

Revision ID: 7b2d4f6a8c10
Revises: 3e7a9c1d5f20
Create Date: 2026-09-18

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel

from alembic import op

revision: str = "7b2d4f6a8c10"
down_revision: Union[str, None] = "3e7a9c1d5f20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table_name in ("llm_provider_config", "llm_config"):
        if not inspector.has_table(table_name):
            continue
        columns = {item["name"] for item in inspector.get_columns(table_name)}
        if "location" not in columns:
            with op.batch_alter_table(table_name, schema=None) as batch_op:
                batch_op.add_column(
                    sa.Column(
                        "location",
                        sqlmodel.sql.sqltypes.AutoString(),
                        nullable=True,
                    )
                )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table_name in ("llm_config", "llm_provider_config"):
        if not inspector.has_table(table_name):
            continue
        columns = {item["name"] for item in inspector.get_columns(table_name)}
        if "location" in columns:
            with op.batch_alter_table(table_name, schema=None) as batch_op:
                batch_op.drop_column("location")
