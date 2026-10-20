"""add adaptive SAST discovery budgets

Revision ID: a91e3b7c5d20
Revises: 7f9d1cf4e066, 6d4f8a2c9b10
Create Date: 2026-09-20
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "a91e3b7c5d20"
down_revision: Union[str, Sequence[str], None] = (
    "7f9d1cf4e066",
    "6d4f8a2c9b10",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "scanner_policy" in tables:
        columns = {column["name"] for column in inspector.get_columns("scanner_policy")}
        if "sast_budget_mode" not in columns:
            op.add_column(
                "scanner_policy",
                sa.Column(
                    "sast_budget_mode",
                    sa.String(),
                    nullable=False,
                    server_default="adaptive",
                ),
            )
        if "sast_worker_budget_max" not in columns:
            op.add_column(
                "scanner_policy",
                sa.Column(
                    "sast_worker_budget_max",
                    sa.Integer(),
                    nullable=False,
                    server_default="250",
                ),
            )
    if "sast_worker" in tables:
        columns = {column["name"] for column in inspector.get_columns("sast_worker")}
        if "tool_call_budget" not in columns:
            op.add_column(
                "sast_worker",
                sa.Column(
                    "tool_call_budget",
                    sa.Integer(),
                    nullable=False,
                    server_default="0",
                ),
            )
        if "budget_basis_json" not in columns:
            op.add_column(
                "sast_worker",
                sa.Column(
                    "budget_basis_json",
                    sa.String(),
                    nullable=False,
                    server_default="{}",
                ),
            )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "sast_worker" in tables:
        columns = {column["name"] for column in inspector.get_columns("sast_worker")}
        if "budget_basis_json" in columns:
            op.drop_column("sast_worker", "budget_basis_json")
        if "tool_call_budget" in columns:
            op.drop_column("sast_worker", "tool_call_budget")
    if "scanner_policy" in tables:
        columns = {column["name"] for column in inspector.get_columns("scanner_policy")}
        if "sast_worker_budget_max" in columns:
            op.drop_column("scanner_policy", "sast_worker_budget_max")
        if "sast_budget_mode" in columns:
            op.drop_column("scanner_policy", "sast_budget_mode")
