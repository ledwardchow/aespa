"""add the post-run SAST Benchmark Lab tables

Revision ID: 6b7c8d9e0f12
Revises: 5a8c1d3e7f20
Create Date: 2026-09-10
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "6b7c8d9e0f12"
down_revision: Union[str, None] = "5a8c1d3e7f20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "benchmark_lab_config",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("panel_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("default_match_mode", sa.String(), nullable=False, server_default="assisted"),
        sa.Column("default_repetitions", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "benchmark_dataset",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("source_digest", sa.String(), nullable=True),
        sa.Column("ground_truth_json", sa.String(), nullable=False, server_default="{}"),
        sa.Column("ground_truth_digest", sa.String(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_benchmark_dataset_name", "benchmark_dataset", ["name"])
    op.create_index("ix_benchmark_dataset_source_digest", "benchmark_dataset", ["source_digest"])
    op.create_index("ix_benchmark_dataset_ground_truth_digest", "benchmark_dataset", ["ground_truth_digest"])
    op.create_table(
        "benchmark_evaluation",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("sast_run_id", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="created"),
        sa.Column("match_mode", sa.String(), nullable=False, server_default="assisted"),
        sa.Column("matching_version", sa.String(), nullable=False, server_default="deterministic-v1"),
        sa.Column("policy_json", sa.String(), nullable=False, server_default="{}"),
        sa.Column("run_provenance_json", sa.String(), nullable=False, server_default="{}"),
        sa.Column("blindness_status", sa.String(), nullable=False, server_default="warning"),
        sa.Column("blindness_checks_json", sa.String(), nullable=False, server_default="{}"),
        sa.Column("metrics_json", sa.String(), nullable=False, server_default="{}"),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["benchmark_dataset.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sast_run_id"], ["sast_run.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_benchmark_evaluation_name", "benchmark_evaluation", ["name"])
    op.create_index("ix_benchmark_evaluation_sast_run_id", "benchmark_evaluation", ["sast_run_id"])
    op.create_index("ix_benchmark_evaluation_dataset_id", "benchmark_evaluation", ["dataset_id"])
    op.create_index("ix_benchmark_evaluation_status", "benchmark_evaluation", ["status"])
    op.create_index("ix_benchmark_evaluation_blindness_status", "benchmark_evaluation", ["blindness_status"])
    op.create_table(
        "benchmark_match",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("evaluation_id", sa.Integer(), nullable=False),
        sa.Column("ground_truth_external_id", sa.String(), nullable=True),
        sa.Column("scan_lead_id", sa.Integer(), nullable=True),
        sa.Column("disposition", sa.String(), nullable=False, server_default="unreviewed"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rationale", sa.String(), nullable=False, server_default=""),
        sa.Column("human_reviewed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("review_note", sa.String(), nullable=False, server_default=""),
        sa.Column("review_history_json", sa.String(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["evaluation_id"], ["benchmark_evaluation.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scan_lead_id"], ["scan_lead.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evaluation_id", "ground_truth_external_id", name="uq_benchmark_match_ground_truth"),
        sa.UniqueConstraint("evaluation_id", "scan_lead_id", name="uq_benchmark_match_scan_lead"),
    )
    op.create_index("ix_benchmark_match_evaluation_id", "benchmark_match", ["evaluation_id"])
    op.create_index("ix_benchmark_match_ground_truth_external_id", "benchmark_match", ["ground_truth_external_id"])
    op.create_index("ix_benchmark_match_scan_lead_id", "benchmark_match", ["scan_lead_id"])
    op.create_index("ix_benchmark_match_disposition", "benchmark_match", ["disposition"])


def downgrade() -> None:
    op.drop_table("benchmark_match")
    op.drop_table("benchmark_evaluation")
    op.drop_table("benchmark_dataset")
    op.drop_table("benchmark_lab_config")
