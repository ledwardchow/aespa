"""add Deep web DAST queue and settings

Revision ID: 3b5d7f9a1c24
Revises: 2a4c6e8f0b13
Create Date: 2026-09-12
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "3b5d7f9a1c24"
down_revision: Union[str, None] = "2a4c6e8f0b13"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "deep_scan_config" not in tables:
        op.create_table(
            "deep_scan_config",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("max_concurrent_workers", sa.Integer(), nullable=False),
            sa.Column("max_tasks", sa.Integer(), nullable=False),
            sa.Column("max_steps_per_task", sa.Integer(), nullable=False),
            sa.Column("include_sast_leads", sa.Boolean(), nullable=False),
            sa.Column("include_recon_checks", sa.Boolean(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
    if "deep_scan_task" not in tables:
        op.create_table(
            "deep_scan_task",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("run_id", sa.Integer(), nullable=False),
            sa.Column("fingerprint", sa.String(), nullable=False),
            sa.Column("source", sa.String(), nullable=False),
            sa.Column("obligation_id", sa.Integer(), nullable=True),
            sa.Column("lead_id", sa.Integer(), nullable=True),
            sa.Column("page_id", sa.Integer(), nullable=True),
            sa.Column("attack_class", sa.String(), nullable=False),
            sa.Column("owasp_category", sa.String(), nullable=False),
            sa.Column("target_url", sa.String(), nullable=False),
            sa.Column("http_method", sa.String(), nullable=False),
            sa.Column("parameter", sa.String(), nullable=True),
            sa.Column("session_label", sa.String(), nullable=True),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("hypothesis", sa.String(), nullable=False),
            sa.Column("priority", sa.Integer(), nullable=False),
            sa.Column("risk_level", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("attempt_count", sa.Integer(), nullable=False),
            sa.Column("max_attempts", sa.Integer(), nullable=False),
            sa.Column("worker_id", sa.String(), nullable=True),
            sa.Column("handoff_id", sa.Integer(), nullable=True),
            sa.Column("finding_id", sa.Integer(), nullable=True),
            sa.Column("outcome", sa.String(), nullable=False),
            sa.Column("error_message", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["run_id"], ["run_identity.id"]),
            sa.ForeignKeyConstraint(["obligation_id"], ["scan_obligation.id"]),
            sa.ForeignKeyConstraint(["lead_id"], ["scan_lead.id"]),
            sa.ForeignKeyConstraint(
                ["page_id"], ["crawled_page.id"], ondelete="SET NULL"
            ),
            sa.ForeignKeyConstraint(["handoff_id"], ["specialist_handoff.id"]),
            sa.ForeignKeyConstraint(
                ["finding_id"], ["scan_finding.id"], ondelete="SET NULL"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "run_id", "fingerprint", name="uq_deep_scan_task_scope"
            ),
        )
        for column in (
            "run_id",
            "fingerprint",
            "source",
            "obligation_id",
            "lead_id",
            "page_id",
            "attack_class",
            "owasp_category",
            "priority",
            "status",
            "worker_id",
            "handoff_id",
            "finding_id",
        ):
            op.create_index(f"ix_deep_scan_task_{column}", "deep_scan_task", [column])
    if "deep_scan_attempt" not in tables:
        op.create_table(
            "deep_scan_attempt",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("run_id", sa.Integer(), nullable=False),
            sa.Column("task_id", sa.Integer(), nullable=False),
            sa.Column("worker_id", sa.String(), nullable=False),
            sa.Column("attempt_number", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("traffic_ids_json", sa.String(), nullable=False),
            sa.Column("outcome", sa.String(), nullable=False),
            sa.Column("error_message", sa.String(), nullable=False),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["run_id"], ["run_identity.id"]),
            sa.ForeignKeyConstraint(["task_id"], ["deep_scan_task.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ("run_id", "task_id", "worker_id", "status"):
            op.create_index(
                f"ix_deep_scan_attempt_{column}", "deep_scan_attempt", [column]
            )


def downgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "deep_scan_attempt" in tables:
        op.drop_table("deep_scan_attempt")
    if "deep_scan_task" in tables:
        op.drop_table("deep_scan_task")
    if "deep_scan_config" in tables:
        op.drop_table("deep_scan_config")
