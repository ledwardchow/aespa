"""Add a per-model speed tier.

Revision ID: a7c3e9f1b2d4
Revises: 5520f43b1a6e
Create Date: 2026-10-15
"""

import sqlalchemy as sa

from alembic import op

revision = "a7c3e9f1b2d4"
down_revision = "5520f43b1a6e"
branch_labels = None
depends_on = None


def _columns() -> set[str] | None:
    inspector = sa.inspect(op.get_bind())
    if "llm_config" not in inspector.get_table_names():
        return None
    return {column["name"] for column in inspector.get_columns("llm_config")}


def upgrade() -> None:
    columns = _columns()
    if columns is None or "service_tier" in columns:
        return
    op.add_column(
        "llm_config",
        sa.Column("service_tier", sa.String(), nullable=True),
    )


def downgrade() -> None:
    columns = _columns()
    if columns is None or "service_tier" not in columns:
        return
    op.drop_column("llm_config", "service_tier")
