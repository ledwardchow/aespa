"""Add a per-run LLM budget to web test runs.

Revision ID: c41d7e9a2b53
Revises: 8e17b2a4c6d0
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "c41d7e9a2b53"
down_revision: str | None = "8e17b2a4c6d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("test_run")}
    if "llm_budget_usd" not in columns:
        with op.batch_alter_table("test_run") as batch_op:
            batch_op.add_column(sa.Column("llm_budget_usd", sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("test_run") as batch_op:
        batch_op.drop_column("llm_budget_usd")
