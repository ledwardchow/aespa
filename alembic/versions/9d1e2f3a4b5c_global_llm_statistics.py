"""add independent monthly LLM statistics

Revision ID: 9d1e2f3a4b5c
Revises: 1f4e7a2c9b10
Create Date: 2026-08-01

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "9d1e2f3a4b5c"
down_revision: Union[str, None] = "1f4e7a2c9b10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "llm_usage_month",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("month", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "cache_read_tokens", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "cache_write_tokens", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("ai_credits", sa.Float(), nullable=False, server_default="0"),
        sa.Column("factory_credits", sa.Float(), nullable=False, server_default="0"),
        sa.Column("input_price_usd_per_million", sa.Float(), nullable=True),
        sa.Column("output_price_usd_per_million", sa.Float(), nullable=True),
        sa.Column("cache_read_price_usd_per_million", sa.Float(), nullable=True),
        sa.Column("cache_write_price_usd_per_million", sa.Float(), nullable=True),
        sa.Column("credit_price_usd_per_million", sa.Float(), nullable=True),
        sa.Column("credit_unit", sa.String(), nullable=True),
        sa.Column("price_source", sa.String(), nullable=True),
        sa.Column("price_confidence", sa.String(), nullable=True),
        sa.Column(
            "manual_override", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("price_updated_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "month", "provider", "model", name="uq_llm_usage_month_key"
        ),
    )
    op.create_index("ix_llm_usage_month_month", "llm_usage_month", ["month"])
    op.create_index("ix_llm_usage_month_provider", "llm_usage_month", ["provider"])
    op.create_index("ix_llm_usage_month_model", "llm_usage_month", ["model"])

    op.create_table(
        "llm_price_catalog",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("input_price_usd_per_million", sa.Float(), nullable=True),
        sa.Column("output_price_usd_per_million", sa.Float(), nullable=True),
        sa.Column("cache_read_price_usd_per_million", sa.Float(), nullable=True),
        sa.Column("cache_write_price_usd_per_million", sa.Float(), nullable=True),
        sa.Column("credit_price_usd_per_million", sa.Float(), nullable=True),
        sa.Column("credit_unit", sa.String(), nullable=True),
        sa.Column("price_source", sa.String(), nullable=True),
        sa.Column("price_confidence", sa.String(), nullable=True),
        sa.Column(
            "manual_override", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "model", name="uq_llm_price_catalog_key"),
    )
    op.create_index("ix_llm_price_catalog_provider", "llm_price_catalog", ["provider"])
    op.create_index("ix_llm_price_catalog_model", "llm_price_catalog", ["model"])

    op.create_table(
        "llm_price_feed",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_url", sa.String(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_index("ix_llm_price_catalog_model", table_name="llm_price_catalog")
    op.drop_index("ix_llm_price_catalog_provider", table_name="llm_price_catalog")
    op.drop_table("llm_price_catalog")
    op.drop_table("llm_price_feed")
    op.drop_index("ix_llm_usage_month_model", table_name="llm_usage_month")
    op.drop_index("ix_llm_usage_month_provider", table_name="llm_usage_month")
    op.drop_index("ix_llm_usage_month_month", table_name="llm_usage_month")
    op.drop_table("llm_usage_month")
