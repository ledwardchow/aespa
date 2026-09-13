"""add Deep scan execution variants and shared evidence ledgers

Revision ID: 6d8f1a2b3c40
Revises: 4c6e8a1b2d35
Create Date: 2026-09-13
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "6d8f1a2b3c40"
down_revision: Union[str, None] = "4c6e8a1b2d35"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("deep_scan_config") as batch:
        batch.add_column(
            sa.Column(
                "initial_variants_per_campaign",
                sa.Integer(),
                nullable=False,
                server_default="2",
            )
        )
        batch.add_column(
            sa.Column(
                "max_variants_per_campaign",
                sa.Integer(),
                nullable=False,
                server_default="4",
            )
        )
        batch.add_column(
            sa.Column(
                "max_total_variants", sa.Integer(), nullable=False, server_default="400"
            )
        )
        batch.add_column(
            sa.Column(
                "adaptive_follow_up",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )
        batch.add_column(
            sa.Column(
                "minimum_signal_strength",
                sa.Integer(),
                nullable=False,
                server_default="2",
            )
        )
        batch.add_column(
            sa.Column(
                "reuse_captured_baselines",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )

    op.create_table(
        "deep_scan_variant",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("fingerprint", sa.String(), nullable=False),
        sa.Column("variant_index", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("strategy", sa.String(), nullable=False),
        sa.Column("purpose", sa.String(), nullable=False),
        sa.Column("rationale", sa.String(), nullable=False),
        sa.Column("difference", sa.String(), nullable=False),
        sa.Column("identity_requirements_json", sa.String(), nullable=False),
        sa.Column("check_ids_json", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("worker_id", sa.String(), nullable=True),
        sa.Column("handoff_id", sa.Integer(), nullable=True),
        sa.Column("assigned_purpose", sa.String(), nullable=False),
        sa.Column("current_purpose", sa.String(), nullable=False),
        sa.Column("checkpoint_json", sa.String(), nullable=False),
        sa.Column("pivot_history_json", sa.String(), nullable=False),
        sa.Column("finding_count", sa.Integer(), nullable=False),
        sa.Column("novelty_score", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.String(), nullable=False),
        sa.Column("error_message", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["run_identity.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["deep_scan_task.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["handoff_id"], ["specialist_handoff.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "fingerprint", name="uq_deep_scan_variant_task"),
    )
    for column in (
        "run_id",
        "task_id",
        "fingerprint",
        "kind",
        "strategy",
        "status",
        "priority",
        "worker_id",
        "handoff_id",
    ):
        op.create_index(f"ix_deep_scan_variant_{column}", "deep_scan_variant", [column])

    # These nullable attribution columns deliberately avoid rebuilding the two
    # older SQLite tables. Some supported legacy databases contain foreign-key
    # declarations to tables that were absent in their historical schema, and
    # SQLite reflection cannot rebuild those tables safely during startup.
    op.add_column(
        "deep_scan_attempt", sa.Column("variant_id", sa.Integer(), nullable=True)
    )
    op.create_index(
        "ix_deep_scan_attempt_variant_id", "deep_scan_attempt", ["variant_id"]
    )
    op.add_column(
        "deep_scan_task_finding",
        sa.Column("variant_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_deep_scan_task_finding_variant_id",
        "deep_scan_task_finding",
        ["variant_id"],
    )

    op.create_table(
        "deep_scan_probe_outcome",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("variant_id", sa.Integer(), nullable=True),
        sa.Column("check_id", sa.Integer(), nullable=True),
        sa.Column("traffic_id", sa.Integer(), nullable=True),
        sa.Column("fingerprint", sa.String(), nullable=False),
        sa.Column("technique", sa.String(), nullable=False),
        sa.Column("identity_label", sa.String(), nullable=False),
        sa.Column("request_summary", sa.String(), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("signal_type", sa.String(), nullable=False),
        sa.Column("signal_strength", sa.Integer(), nullable=False),
        sa.Column("evidence_json", sa.String(), nullable=False),
        sa.Column("outcome", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["run_identity.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["deep_scan_task.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["variant_id"], ["deep_scan_variant.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["check_id"], ["deep_scan_check.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["traffic_id"], ["traffic_entry.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "fingerprint", name="uq_deep_probe_outcome_run"),
    )
    for column in (
        "run_id",
        "task_id",
        "variant_id",
        "check_id",
        "traffic_id",
        "fingerprint",
        "signal_type",
    ):
        op.create_index(
            f"ix_deep_scan_probe_outcome_{column}", "deep_scan_probe_outcome", [column]
        )

    op.create_table(
        "deep_scan_claim",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("variant_id", sa.Integer(), nullable=True),
        sa.Column("fingerprint", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("finding_id", sa.Integer(), nullable=True),
        sa.Column("evidence_json", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["run_identity.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["deep_scan_task.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["variant_id"], ["deep_scan_variant.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["finding_id"], ["scan_finding.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "fingerprint", name="uq_deep_scan_claim_run"),
    )
    for column in (
        "run_id",
        "task_id",
        "variant_id",
        "fingerprint",
        "status",
        "finding_id",
    ):
        op.create_index(f"ix_deep_scan_claim_{column}", "deep_scan_claim", [column])


def downgrade() -> None:
    op.drop_table("deep_scan_claim")
    op.drop_table("deep_scan_probe_outcome")
    op.drop_index(
        "ix_deep_scan_task_finding_variant_id",
        table_name="deep_scan_task_finding",
    )
    op.drop_column("deep_scan_task_finding", "variant_id")
    op.drop_index("ix_deep_scan_attempt_variant_id", table_name="deep_scan_attempt")
    op.drop_column("deep_scan_attempt", "variant_id")
    op.drop_table("deep_scan_variant")
    with op.batch_alter_table("deep_scan_config") as batch:
        batch.drop_column("reuse_captured_baselines")
        batch.drop_column("minimum_signal_strength")
        batch.drop_column("adaptive_follow_up")
        batch.drop_column("max_total_variants")
        batch.drop_column("max_variants_per_campaign")
        batch.drop_column("initial_variants_per_campaign")
