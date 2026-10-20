"""count LLM usage and prices separately per speed tier

Revision ID: b8e2d4f6a1c3
Revises: c41d7e9a2b53
Create Date: 2026-10-17
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "b8e2d4f6a1c3"
down_revision: Union[str, Sequence[str], None] = "c41d7e9a2b53"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = {
    "llm_usage_month": ("uq_llm_usage_month_key", ["month", "provider", "model"]),
    "llm_price_catalog": ("uq_llm_price_catalog_key", ["provider", "model"]),
}


def _has_service_tier(table: str) -> bool | None:
    """Return None when the table is missing, else whether it has the column."""
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return None
    return "service_tier" in {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    for table, (constraint, columns) in _TABLES.items():
        if _has_service_tier(table) is not False:
            continue
        with op.batch_alter_table(table, recreate="always") as batch:
            batch.add_column(
                sa.Column(
                    "service_tier", sa.String(), nullable=False, server_default=""
                )
            )
            batch.drop_constraint(constraint, type_="unique")
            batch.create_unique_constraint(constraint, [*columns, "service_tier"])


def downgrade() -> None:
    bind = op.get_bind()
    for table, (constraint, columns) in _TABLES.items():
        if not _has_service_tier(table):
            continue
        bind.execute(sa.text(f"DELETE FROM {table} WHERE service_tier != ''"))
        with op.batch_alter_table(table, recreate="always") as batch:
            batch.drop_constraint(constraint, type_="unique")
            batch.create_unique_constraint(constraint, columns)
            batch.drop_column("service_tier")
