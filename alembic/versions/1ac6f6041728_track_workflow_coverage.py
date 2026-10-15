"""Track security tests for crawler workflows.

Revision ID: 1ac6f6041728
Revises: a7c3e9f1b2d4
Create Date: 2026-10-15
"""

import sqlalchemy as sa

from alembic import op

revision = "1ac6f6041728"
down_revision = "a7c3e9f1b2d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    # An earlier version of this migration could stop part way through on
    # SQLite, leaving the new table and Alembic's scratch copy behind.
    if "_alembic_tmp_deep_scan_task" in tables:
        op.drop_table("_alembic_tmp_deep_scan_task")
    if "workflow_coverage_item" not in tables:
        _create_workflow_coverage_item()
    _add_deep_scan_task_link(bind)


def _create_workflow_coverage_item() -> None:
    op.create_table(
        "workflow_coverage_item",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "test_run_id",
            sa.Integer(),
            sa.ForeignKey("run_identity.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("root_note_id", sa.Integer(), nullable=False),
        sa.Column("latest_note_id", sa.Integer(), nullable=False),
        sa.Column("reached_page_id", sa.Integer(), sa.ForeignKey("crawled_page.id")),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("goal", sa.String(), nullable=False),
        sa.Column("reached_page_url", sa.String(), nullable=False),
        sa.Column("crawl_traffic_max_id", sa.Integer(), nullable=False),
        sa.Column("test_kind", sa.String(), nullable=False),
        sa.Column("owasp_category", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("evidence_json", sa.String(), nullable=False),
        sa.Column("finding_id", sa.Integer(), sa.ForeignKey("scan_finding.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "test_run_id",
            "root_note_id",
            "test_kind",
            name="uq_workflow_coverage_item_run_note_kind",
        ),
    )
    for column in (
        "test_run_id",
        "root_note_id",
        "latest_note_id",
        "test_kind",
        "owasp_category",
        "status",
    ):
        op.create_index(
            f"ix_workflow_coverage_item_{column}",
            "workflow_coverage_item",
            [column],
        )


def _add_deep_scan_task_link(bind) -> None:
    if bind.dialect.name == "sqlite":
        # Rebuilding deep_scan_task (Alembic batch mode) drops the old table
        # while runtime connections enforce foreign keys, which fails on child
        # rows or cascades deletes into them. SQLite can add a nullable FK
        # column in place, so no rebuild is needed.
        op.execute(
            "ALTER TABLE deep_scan_task ADD COLUMN workflow_test_id INTEGER "
            "CONSTRAINT fk_deep_scan_task_workflow_test_id "
            "REFERENCES workflow_coverage_item (id)"
        )
    else:
        op.add_column(
            "deep_scan_task",
            sa.Column("workflow_test_id", sa.Integer(), nullable=True),
        )
        op.create_foreign_key(
            "fk_deep_scan_task_workflow_test_id",
            "deep_scan_task",
            "workflow_coverage_item",
            ["workflow_test_id"],
            ["id"],
        )
    op.create_index(
        "ix_deep_scan_task_workflow_test_id", "deep_scan_task", ["workflow_test_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_deep_scan_task_workflow_test_id", table_name="deep_scan_task")
    # Batch mode drops the column's foreign key with it. SQLite does not keep
    # the name of a constraint added with ADD COLUMN, so it cannot be dropped
    # by name first.
    with op.batch_alter_table("deep_scan_task") as batch_op:
        batch_op.drop_column("workflow_test_id")
    op.drop_table("workflow_coverage_item")
