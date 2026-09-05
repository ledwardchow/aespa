"""add normalized SAST work program and evidence receipts

Revision ID: a8f2c6d9e4b1
Revises: b3c4d5e6f7a8
Create Date: 2026-08-30
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "a8f2c6d9e4b1"
down_revision: Union[str, None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _run_fk() -> sa.ForeignKey:
    return sa.ForeignKey("sast_run.id", ondelete="CASCADE")


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    # Several migration tests and some very old installations start from a
    # deliberately partial schema. There is no SAST state to upgrade there.
    if "sast_run" not in tables:
        return
    op.add_column(
        "sast_run",
        sa.Column(
            "completion_status",
            sa.String(),
            nullable=False,
            server_default="pending",
        ),
    )
    op.create_index(
        "ix_sast_run_completion_status",
        "sast_run",
        ["completion_status"],
        unique=False,
    )
    if "scan_lead" in tables:
        op.add_column(
            "scan_lead", sa.Column("source_work_item_id", sa.Integer(), nullable=True)
        )
        op.create_index(
            "ix_scan_lead_source_work_item_id",
            "scan_lead",
            ["source_work_item_id"],
            unique=False,
        )

    op.create_table(
        "sast_source_file",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sast_run_id", sa.Integer(), _run_fk(), nullable=False),
        sa.Column("path", sa.String(), nullable=False),
        sa.Column("language", sa.String(), nullable=False, server_default="Other"),
        sa.Column("size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sha256", sa.String(), nullable=False, server_default=""),
        sa.Column(
            "classification", sa.String(), nullable=False, server_default="production"
        ),
        sa.Column(
            "production_relevant",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "classification_reason", sa.String(), nullable=False, server_default=""
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("sast_run_id", "path", name="uq_sast_source_file_path"),
    )
    for column in (
        "sast_run_id",
        "path",
        "language",
        "sha256",
        "classification",
        "production_relevant",
    ):
        op.create_index(f"ix_sast_source_file_{column}", "sast_source_file", [column])

    op.create_table(
        "sast_surface_item",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sast_run_id", sa.Integer(), _run_fk(), nullable=False),
        sa.Column(
            "source_file_id",
            sa.Integer(),
            sa.ForeignKey("sast_source_file.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False, server_default=""),
        sa.Column("name", sa.String(), nullable=False, server_default=""),
        sa.Column("path", sa.String(), nullable=False, server_default=""),
        sa.Column("line", sa.Integer(), nullable=True),
        sa.Column("symbol", sa.String(), nullable=False, server_default=""),
        sa.Column("trust_level", sa.String(), nullable=False, server_default="unknown"),
        sa.Column(
            "production_reachable",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column("details_json", sa.String(), nullable=False, server_default="{}"),
        sa.Column(
            "provenance", sa.String(), nullable=False, server_default="deterministic"
        ),
        sa.Column("fingerprint", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "sast_run_id",
            "fingerprint",
            name="uq_sast_surface_item_fingerprint",
        ),
    )
    for column in (
        "sast_run_id",
        "source_file_id",
        "kind",
        "category",
        "path",
        "trust_level",
        "production_reachable",
        "provenance",
        "fingerprint",
    ):
        op.create_index(f"ix_sast_surface_item_{column}", "sast_surface_item", [column])

    op.create_table(
        "sast_partition",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sast_run_id", sa.Integer(), _run_fk(), nullable=False),
        sa.Column("partition_key", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False, server_default=""),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column(
            "production_reachable",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column("file_paths_json", sa.String(), nullable=False, server_default="[]"),
        sa.Column(
            "shared_paths_json", sa.String(), nullable=False, server_default="[]"
        ),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("sast_run_id", "partition_key", name="uq_sast_partition"),
    )
    for column in (
        "sast_run_id",
        "partition_key",
        "status",
        "production_reachable",
    ):
        op.create_index(f"ix_sast_partition_{column}", "sast_partition", [column])

    op.create_table(
        "sast_worker",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sast_run_id", sa.Integer(), _run_fk(), nullable=False),
        sa.Column(
            "partition_id",
            sa.Integer(),
            sa.ForeignKey("sast_partition.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("worker_key", sa.String(), nullable=False),
        sa.Column("class_group", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("summary", sa.String(), nullable=False, server_default=""),
        sa.Column("error_message", sa.String(), nullable=False, server_default=""),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("sast_run_id", "worker_key", name="uq_sast_worker_key"),
    )
    for column in (
        "sast_run_id",
        "partition_id",
        "worker_key",
        "class_group",
        "status",
    ):
        op.create_index(f"ix_sast_worker_{column}", "sast_worker", [column])

    op.create_table(
        "sast_work_item",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sast_run_id", sa.Integer(), _run_fk(), nullable=False),
        sa.Column(
            "partition_id",
            sa.Integer(),
            sa.ForeignKey("sast_partition.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "surface_item_id",
            sa.Integer(),
            sa.ForeignKey("sast_surface_item.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "worker_id",
            sa.Integer(),
            sa.ForeignKey("sast_worker.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("work_key", sa.String(), nullable=False),
        sa.Column("work_type", sa.String(), nullable=False, server_default="input"),
        sa.Column("class_group", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("disposition", sa.String(), nullable=False, server_default=""),
        sa.Column("reasoning", sa.String(), nullable=False, server_default=""),
        sa.Column("trace_json", sa.String(), nullable=False, server_default="[]"),
        sa.Column("controls_json", sa.String(), nullable=False, server_default="[]"),
        sa.Column("evidence_json", sa.String(), nullable=False, server_default="[]"),
        sa.Column("lead_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("sast_run_id", "work_key", name="uq_sast_work_item_key"),
    )
    for column in (
        "sast_run_id",
        "partition_id",
        "surface_item_id",
        "worker_id",
        "work_key",
        "work_type",
        "class_group",
        "status",
        "lead_id",
    ):
        op.create_index(f"ix_sast_work_item_{column}", "sast_work_item", [column])

    op.create_table(
        "sast_evidence_receipt",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sast_run_id", sa.Integer(), _run_fk(), nullable=False),
        sa.Column(
            "worker_id",
            sa.Integer(),
            sa.ForeignKey("sast_worker.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("phase", sa.String(), nullable=False, server_default="discovery"),
        sa.Column("tool_name", sa.String(), nullable=False),
        sa.Column("path", sa.String(), nullable=False, server_default=""),
        sa.Column("start_line", sa.Integer(), nullable=True),
        sa.Column("end_line", sa.Integer(), nullable=True),
        sa.Column("search_pattern", sa.String(), nullable=False, server_default=""),
        sa.Column("include_pattern", sa.String(), nullable=False, server_default=""),
        sa.Column("files_in_scope", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "files_with_matches", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("matches_returned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "characters_returned", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("truncated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("details_json", sa.String(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    for column in ("sast_run_id", "worker_id", "phase", "tool_name", "path"):
        op.create_index(
            f"ix_sast_evidence_receipt_{column}", "sast_evidence_receipt", [column]
        )


def downgrade() -> None:
    op.drop_table("sast_evidence_receipt")
    op.drop_table("sast_work_item")
    op.drop_table("sast_worker")
    op.drop_table("sast_partition")
    op.drop_table("sast_surface_item")
    op.drop_table("sast_source_file")
    op.drop_index("ix_scan_lead_source_work_item_id", table_name="scan_lead")
    op.drop_column("scan_lead", "source_work_item_id")
    op.drop_index("ix_sast_run_completion_status", table_name="sast_run")
    op.drop_column("sast_run", "completion_status")
