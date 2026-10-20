"""add DAST and SAST LLM concurrency settings

Revision ID: a4c6e8f0b2d4
Revises: f7b5c3d9e012
Create Date: 2026-09-22
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "a4c6e8f0b2d4"
down_revision: Union[str, Sequence[str], None] = "f7b5c3d9e012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "scanner_policy" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("scanner_policy")}
    for name in (
        "dast_max_concurrent_llm_requests",
        "sast_max_concurrent_llm_requests",
    ):
        if name not in columns:
            op.add_column(
                "scanner_policy",
                sa.Column(name, sa.Integer(), nullable=False, server_default="4"),
            )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "scanner_policy" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("scanner_policy")}
    for name in (
        "sast_max_concurrent_llm_requests",
        "dast_max_concurrent_llm_requests",
    ):
        if name in columns:
            op.drop_column("scanner_policy", name)
