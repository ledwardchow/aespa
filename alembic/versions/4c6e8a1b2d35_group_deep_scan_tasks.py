"""group Deep scan checks into worker campaigns

Revision ID: 4c6e8a1b2d35
Revises: 8e4b1c7d2a90
Create Date: 2026-09-12
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "4c6e8a1b2d35"
down_revision: Union[str, None] = "8e4b1c7d2a90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("deep_scan_task") as batch:
        batch.add_column(sa.Column("task_kind", sa.String(), nullable=False, server_default="operation"))
        batch.add_column(sa.Column("route_template", sa.String(), nullable=False, server_default=""))
        batch.add_column(sa.Column("inputs_json", sa.String(), nullable=False, server_default="[]"))
        batch.add_column(sa.Column("identities_json", sa.String(), nullable=False, server_default="[]"))
        batch.create_index("ix_deep_scan_task_task_kind", ["task_kind"])
        batch.create_index("ix_deep_scan_task_route_template", ["route_template"])

    op.create_table(
        "deep_scan_check",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("fingerprint", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("obligation_id", sa.Integer(), nullable=True),
        sa.Column("lead_id", sa.Integer(), nullable=True),
        sa.Column("attack_class", sa.String(), nullable=False),
        sa.Column("owasp_category", sa.String(), nullable=False),
        sa.Column("parameter", sa.String(), nullable=True),
        sa.Column("parameter_location", sa.String(), nullable=False),
        sa.Column("session_label", sa.String(), nullable=True),
        sa.Column("hypothesis", sa.String(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("finding_id", sa.Integer(), nullable=True),
        sa.Column("outcome", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["run_identity.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["deep_scan_task.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["obligation_id"], ["scan_obligation.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["scan_lead.id"]),
        sa.ForeignKeyConstraint(["finding_id"], ["scan_finding.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "fingerprint", name="uq_deep_scan_check_task"),
    )
    for column in (
        "run_id", "task_id", "fingerprint", "source", "obligation_id", "lead_id",
        "attack_class", "owasp_category", "priority", "status", "finding_id",
    ):
        op.create_index(f"ix_deep_scan_check_{column}", "deep_scan_check", [column])

    op.create_table(
        "deep_scan_task_finding",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("finding_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["run_identity.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["deep_scan_task.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["finding_id"], ["scan_finding.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "finding_id", name="uq_deep_scan_task_finding"),
    )
    for column in ("run_id", "task_id", "finding_id"):
        op.create_index(f"ix_deep_scan_task_finding_{column}", "deep_scan_task_finding", [column])


def downgrade() -> None:
    op.drop_table("deep_scan_task_finding")
    op.drop_table("deep_scan_check")
    with op.batch_alter_table("deep_scan_task") as batch:
        batch.drop_index("ix_deep_scan_task_route_template")
        batch.drop_index("ix_deep_scan_task_task_kind")
        batch.drop_column("identities_json")
        batch.drop_column("inputs_json")
        batch.drop_column("route_template")
        batch.drop_column("task_kind")
