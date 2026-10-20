"""Add tree-sitter code graph tables for SAST runs.

Revision ID: e3c5a7b9d1f2
Revises: d59e13af467b
Create Date: 2026-09-29
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "e3c5a7b9d1f2"
down_revision: Union[str, Sequence[str], None] = "d59e13af467b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sast_code_symbol",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "sast_run_id",
            sa.Integer(),
            sa.ForeignKey("sast_run.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("symbol_key", sa.String(), nullable=False),
        sa.Column("path", sa.String(), nullable=False),
        sa.Column("language", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("qualname", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=False),
        sa.Column("end_line", sa.Integer(), nullable=False),
        sa.Column("reachability", sa.String(), nullable=False),
        sa.Column("is_root", sa.Boolean(), nullable=False),
    )
    for column in ("sast_run_id", "symbol_key", "path", "reachability"):
        op.create_index(f"ix_sast_code_symbol_{column}", "sast_code_symbol", [column])
    op.create_table(
        "sast_code_call",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "sast_run_id",
            sa.Integer(),
            sa.ForeignKey("sast_run.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("path", sa.String(), nullable=False),
        sa.Column("line", sa.Integer(), nullable=False),
        sa.Column("caller_key", sa.String(), nullable=False),
        sa.Column("callee_name", sa.String(), nullable=False),
        sa.Column("receiver", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("targets_json", sa.String(), nullable=False),
    )
    for column in ("sast_run_id", "path", "caller_key"):
        op.create_index(f"ix_sast_code_call_{column}", "sast_code_call", [column])


def downgrade() -> None:
    for column in ("sast_run_id", "path", "caller_key"):
        op.drop_index(f"ix_sast_code_call_{column}", table_name="sast_code_call")
    op.drop_table("sast_code_call")
    for column in ("sast_run_id", "symbol_key", "path", "reachability"):
        op.drop_index(f"ix_sast_code_symbol_{column}", table_name="sast_code_symbol")
    op.drop_table("sast_code_symbol")
