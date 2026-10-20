"""Add a daily LLM usage ledger.

Revision ID: e95fdda94987
Revises: c6d2f8a9b104
Create Date: 2026-10-19
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "e95fdda94987"
down_revision: Union[str, None] = "c6d2f8a9b104"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "llm_usage_day" not in inspector.get_table_names():
        op.create_table(
            "llm_usage_day",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("day", sa.String(), nullable=False),
            sa.Column("provider", sa.String(), nullable=False),
            sa.Column("model", sa.String(), nullable=False),
            sa.Column("service_tier", sa.String(), nullable=False),
            sa.Column("requests", sa.Integer(), nullable=False),
            sa.Column("input_tokens", sa.Integer(), nullable=False),
            sa.Column("output_tokens", sa.Integer(), nullable=False),
            sa.Column("cache_read_tokens", sa.Integer(), nullable=False),
            sa.Column("cache_write_tokens", sa.Integer(), nullable=False),
            sa.Column("ai_credits", sa.Float(), nullable=False),
            sa.Column("factory_credits", sa.Float(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "day", "provider", "model", "service_tier", name="uq_llm_usage_day_key"
            ),
        )
    indexes = {index["name"] for index in inspector.get_indexes("llm_usage_day")}
    for column in ("day", "provider", "model"):
        name = f"ix_llm_usage_day_{column}"
        if name not in indexes:
            op.create_index(name, "llm_usage_day", [column])


def downgrade() -> None:
    op.drop_index("ix_llm_usage_day_model", table_name="llm_usage_day")
    op.drop_index("ix_llm_usage_day_provider", table_name="llm_usage_day")
    op.drop_index("ix_llm_usage_day_day", table_name="llm_usage_day")
    op.drop_table("llm_usage_day")
