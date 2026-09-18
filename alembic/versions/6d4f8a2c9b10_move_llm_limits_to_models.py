"""move LLM rate limits from providers to models

Revision ID: 6d4f8a2c9b10
Revises: 7b2d4f6a8c10
Create Date: 2026-09-18

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "6d4f8a2c9b10"
down_revision: Union[str, None] = "7b2d4f6a8c10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "llm_config" not in tables:
        return

    model_columns = {item["name"] for item in inspector.get_columns("llm_config")}
    with op.batch_alter_table("llm_config") as batch:
        if "max_tpm" not in model_columns:
            batch.add_column(sa.Column("max_tpm", sa.Integer(), nullable=True))
        if "max_rpm" not in model_columns:
            batch.add_column(sa.Column("max_rpm", sa.Integer(), nullable=True))

    if "llm_provider_config" not in tables:
        return
    provider_columns = {
        item["name"] for item in inspector.get_columns("llm_provider_config")
    }
    if "max_tpm" in provider_columns:
        op.execute(
            sa.text(
                "UPDATE llm_config SET max_tpm = "
                "(SELECT max_tpm FROM llm_provider_config "
                "WHERE llm_provider_config.id = llm_config.provider_id) "
                "WHERE max_tpm IS NULL"
            )
        )
    if "max_rpm" in provider_columns:
        op.execute(
            sa.text(
                "UPDATE llm_config SET max_rpm = "
                "(SELECT max_rpm FROM llm_provider_config "
                "WHERE llm_provider_config.id = llm_config.provider_id) "
                "WHERE max_rpm IS NULL"
            )
        )
    # Do not use SQLite batch mode here. It rebuilds and drops the provider
    # table, which fails while llm_config has a foreign key referencing it.
    # These columns are not part of any constraint, so direct column drops are
    # safe and preserve the referenced table.
    if "max_tpm" in provider_columns:
        op.drop_column("llm_provider_config", "max_tpm")
    if "max_rpm" in provider_columns:
        op.drop_column("llm_provider_config", "max_rpm")


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "llm_provider_config" not in tables:
        return

    provider_columns = {
        item["name"] for item in inspector.get_columns("llm_provider_config")
    }
    if "max_tpm" not in provider_columns:
        op.add_column(
            "llm_provider_config", sa.Column("max_tpm", sa.Integer(), nullable=True)
        )
    if "max_rpm" not in provider_columns:
        op.add_column(
            "llm_provider_config", sa.Column("max_rpm", sa.Integer(), nullable=True)
        )

    if "llm_config" not in tables:
        return
    model_columns = {item["name"] for item in inspector.get_columns("llm_config")}
    if "max_tpm" in model_columns:
        op.execute(
            sa.text(
                "UPDATE llm_provider_config SET max_tpm = "
                "(SELECT MIN(max_tpm) FROM llm_config "
                "WHERE llm_config.provider_id = llm_provider_config.id)"
            )
        )
    if "max_rpm" in model_columns:
        op.execute(
            sa.text(
                "UPDATE llm_provider_config SET max_rpm = "
                "(SELECT MIN(max_rpm) FROM llm_config "
                "WHERE llm_config.provider_id = llm_provider_config.id)"
            )
        )
    if "max_tpm" in model_columns:
        op.drop_column("llm_config", "max_tpm")
    if "max_rpm" in model_columns:
        op.drop_column("llm_config", "max_rpm")
