"""persist the canonical page on specialist handoffs

Revision ID: 5a8c1d3e7f20
Revises: 2b6e8d1f4a90
Create Date: 2026-09-08
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "5a8c1d3e7f20"
down_revision: str | None = "2b6e8d1f4a90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "specialist_handoff" not in inspector.get_table_names():
        return
    if "page_id" in {
        column["name"] for column in inspector.get_columns("specialist_handoff")
    }:
        return
    with op.batch_alter_table("specialist_handoff") as batch_op:
        batch_op.add_column(sa.Column("page_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_specialist_handoff_page_id", ["page_id"])
        batch_op.create_foreign_key(
            "fk_specialist_handoff_page_id_crawled_page",
            "crawled_page",
            ["page_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "specialist_handoff" not in inspector.get_table_names():
        return
    if "page_id" not in {
        column["name"] for column in inspector.get_columns("specialist_handoff")
    }:
        return
    with op.batch_alter_table("specialist_handoff") as batch_op:
        batch_op.drop_constraint(
            "fk_specialist_handoff_page_id_crawled_page",
            type_="foreignkey",
        )
        batch_op.drop_index("ix_specialist_handoff_page_id")
        batch_op.drop_column("page_id")
