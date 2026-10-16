"""Give workflow security checks a stable inventory key.

Revision ID: 91c4b6e7a205
Revises: 1ac6f6041728
Create Date: 2026-10-16
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "91c4b6e7a205"
down_revision = "1ac6f6041728"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.get_context().autocommit_block():
            bind.exec_driver_sql("PRAGMA foreign_keys=OFF")
    with op.batch_alter_table(
        "workflow_coverage_item", recreate="always", reflect_kwargs={"resolve_fks": False}
    ) as batch:
        batch.alter_column("root_note_id", existing_type=sa.Integer(), nullable=True)
        batch.alter_column("latest_note_id", existing_type=sa.Integer(), nullable=True)
    if bind.dialect.name == "sqlite":
        with op.get_context().autocommit_block():
            bind.exec_driver_sql("PRAGMA foreign_keys=ON")
    op.add_column(
        "workflow_coverage_item",
        sa.Column("workflow_key", sa.String(), nullable=False, server_default=""),
    )
    op.execute(
        "UPDATE workflow_coverage_item SET workflow_key = 'note:' || root_note_id"
    )
    op.create_index(
        "uq_workflow_coverage_item_run_key_kind",
        "workflow_coverage_item",
        ["test_run_id", "workflow_key", "test_kind"],
        unique=True,
    )
    op.create_index(
        "ix_workflow_coverage_item_workflow_key",
        "workflow_coverage_item",
        ["workflow_key"],
    )


def downgrade() -> None:
    op.execute(
        "UPDATE deep_scan_task SET workflow_test_id = NULL "
        "WHERE workflow_test_id IN ("
        "SELECT id FROM workflow_coverage_item WHERE root_note_id IS NULL)"
    )
    op.execute("DELETE FROM workflow_coverage_item WHERE root_note_id IS NULL")
    op.drop_index(
        "ix_workflow_coverage_item_workflow_key", table_name="workflow_coverage_item"
    )
    op.drop_index(
        "uq_workflow_coverage_item_run_key_kind", table_name="workflow_coverage_item"
    )
    op.drop_column("workflow_coverage_item", "workflow_key")
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.get_context().autocommit_block():
            bind.exec_driver_sql("PRAGMA foreign_keys=OFF")
    with op.batch_alter_table(
        "workflow_coverage_item", recreate="always", reflect_kwargs={"resolve_fks": False}
    ) as batch:
        batch.alter_column("root_note_id", existing_type=sa.Integer(), nullable=False)
        batch.alter_column("latest_note_id", existing_type=sa.Integer(), nullable=False)
    if bind.dialect.name == "sqlite":
        with op.get_context().autocommit_block():
            bind.exec_driver_sql("PRAGMA foreign_keys=ON")
