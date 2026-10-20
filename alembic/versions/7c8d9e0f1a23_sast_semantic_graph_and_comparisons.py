"""persist SAST semantic graph, policy, telemetry, and benchmark comparisons

Revision ID: 7c8d9e0f1a23
Revises: 6b7c8d9e0f12
Create Date: 2026-09-10
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "7c8d9e0f1a23"
down_revision: Union[str, None] = "6b7c8d9e0f12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _json(name: str, default: str = "[]") -> sa.Column:
    return sa.Column(name, sa.String(), nullable=False, server_default=default)


def upgrade() -> None:
    existing_tables = set(sa.inspect(op.get_bind()).get_table_names())

    # Some pre-Alembic installations contain the shared scanner tables but no
    # SAST tables. They are stamped at the nearest compatible historical
    # revision, so every later SAST-only alteration must remain optional.
    if "scan_lead" in existing_tables:
        op.add_column(
            "scan_lead",
            sa.Column(
                "classification",
                sa.String(),
                nullable=False,
                server_default="exploitable",
            ),
        )
        op.add_column(
            "scan_lead",
            sa.Column(
                "discovery_strategy", sa.String(), nullable=False, server_default=""
            ),
        )
        op.add_column(
            "scan_lead",
            sa.Column(
                "provenance_json", sa.String(), nullable=False, server_default="[]"
            ),
        )
        op.create_index("ix_scan_lead_classification", "scan_lead", ["classification"])
        op.create_index(
            "ix_scan_lead_discovery_strategy", "scan_lead", ["discovery_strategy"]
        )
    for name, type_, default in (
        ("sast_rate_limit_findings", sa.Boolean(), sa.true()),
        ("sast_race_condition_findings", sa.Boolean(), sa.true()),
        ("sast_audit_logging_findings", sa.Boolean(), sa.false()),
        ("sast_defense_in_depth_findings", sa.Boolean(), sa.false()),
        ("sast_dependency_findings", sa.Boolean(), sa.true()),
        ("sast_min_severity", sa.String(), "low"),
        ("sast_min_confidence", sa.Float(), "0.35"),
        ("sast_baseline_budget", sa.Integer(), "80"),
        ("sast_threat_budget", sa.Integer(), "60"),
        ("sast_closure_budget", sa.Integer(), "40"),
        ("sast_validator_budget", sa.Integer(), "50"),
    ):
        op.add_column(
            "scanner_policy",
            sa.Column(name, type_, nullable=False, server_default=default),
        )
    if "sast_surface_item" in existing_tables:
        op.add_column(
            "sast_surface_item",
            sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        )
        op.add_column(
            "sast_surface_item",
            sa.Column(
                "review_status",
                sa.String(),
                nullable=False,
                server_default="unreviewed",
            ),
        )
        op.add_column(
            "sast_surface_item",
            sa.Column("component_key", sa.String(), nullable=False, server_default=""),
        )
        op.create_index(
            "ix_sast_surface_item_review_status",
            "sast_surface_item",
            ["review_status"],
        )
        op.create_index(
            "ix_sast_surface_item_component_key",
            "sast_surface_item",
            ["component_key"],
        )

    op.create_table(
        "sast_surface_edge",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "sast_run_id",
            sa.Integer(),
            sa.ForeignKey("sast_run.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_surface_id",
            sa.Integer(),
            sa.ForeignKey("sast_surface_item.id"),
            nullable=False,
        ),
        sa.Column(
            "target_surface_id",
            sa.Integer(),
            sa.ForeignKey("sast_surface_item.id"),
            nullable=False,
        ),
        sa.Column("edge_kind", sa.String(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column(
            "provenance", sa.String(), nullable=False, server_default="deterministic"
        ),
        _json("evidence_json"),
        sa.Column("fingerprint", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("sast_run_id", "fingerprint", name="uq_sast_surface_edge"),
    )
    op.create_table(
        "sast_threat_model",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "sast_run_id",
            sa.Integer(),
            sa.ForeignKey("sast_run.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("summary", sa.String(), nullable=False, server_default=""),
        _json("assets_json"),
        _json("trust_boundaries_json"),
        _json("attacker_capabilities_json"),
        _json("security_objectives_json"),
        _json("assumptions_json"),
        _json("open_questions_json"),
        sa.Column("model_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "source_snapshot_digest", sa.String(), nullable=False, server_default=""
        ),
        sa.Column(
            "prompt_version",
            sa.String(),
            nullable=False,
            server_default="sast-threat-v1",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "sast_threat_scenario",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "sast_run_id",
            sa.Integer(),
            sa.ForeignKey("sast_run.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scenario_key", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False, server_default=""),
        sa.Column("actor", sa.String(), nullable=False, server_default=""),
        _json("controlled_input_or_state_json"),
        _json("entry_surface_ids_json"),
        _json("boundary_surface_ids_json"),
        _json("asset_surface_ids_json"),
        _json("expected_control_surface_ids_json"),
        _json("sensitive_operation_surface_ids_json"),
        sa.Column("security_objective", sa.String(), nullable=False, server_default=""),
        sa.Column("capability_gain", sa.String(), nullable=False, server_default=""),
        sa.Column("impact", sa.String(), nullable=False, server_default=""),
        _json("prerequisites_json"),
        _json("evidence_json"),
        sa.Column("priority", sa.String(), nullable=False, server_default="medium"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("status", sa.String(), nullable=False, server_default="planned"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "sast_run_id", "scenario_key", name="uq_sast_threat_scenario"
        ),
    )
    op.create_table(
        "sast_coverage_obligation",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "sast_run_id",
            sa.Integer(),
            sa.ForeignKey("sast_run.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("obligation_key", sa.String(), nullable=False),
        sa.Column("obligation_type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False, server_default=""),
        sa.Column("security_question", sa.String(), nullable=False, server_default=""),
        sa.Column("priority", sa.String(), nullable=False, server_default="medium"),
        sa.Column(
            "source_scenario_id",
            sa.Integer(),
            sa.ForeignKey("sast_threat_scenario.id"),
            nullable=True,
        ),
        _json("primary_surface_ids_json"),
        _json("related_surface_ids_json"),
        _json("required_evidence_json"),
        sa.Column(
            "assigned_worker_id",
            sa.Integer(),
            sa.ForeignKey("sast_worker.id"),
            nullable=True,
        ),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("disposition", sa.String(), nullable=False, server_default=""),
        sa.Column("reasoning", sa.String(), nullable=False, server_default=""),
        _json("evidence_json"),
        _json("controls_json"),
        _json("open_questions_json"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "sast_run_id", "obligation_key", name="uq_sast_coverage_obligation"
        ),
    )
    op.create_table(
        "sast_obligation_lead",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "sast_run_id",
            sa.Integer(),
            sa.ForeignKey("sast_run.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "obligation_id",
            sa.Integer(),
            sa.ForeignKey("sast_coverage_obligation.id"),
            nullable=False,
        ),
        sa.Column(
            "lead_id", sa.Integer(), sa.ForeignKey("scan_lead.id"), nullable=False
        ),
        sa.Column(
            "relationship", sa.String(), nullable=False, server_default="primary"
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "obligation_id", "lead_id", "relationship", name="uq_sast_obligation_lead"
        ),
    )
    op.create_table(
        "sast_discovery_telemetry",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "sast_run_id",
            sa.Integer(),
            sa.ForeignKey("sast_run.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("phase", sa.String(), nullable=False),
        sa.Column("strategy", sa.String(), nullable=False, server_default=""),
        *[
            sa.Column(name, sa.Integer(), nullable=False, server_default="0")
            for name in (
                "elapsed_ms",
                "llm_calls",
                "retries",
                "input_tokens",
                "output_tokens",
                "cache_read_tokens",
                "cache_write_tokens",
                "files_read",
                "unique_spans_read",
                "facts_created",
                "obligations_created",
                "obligations_resolved",
                "candidates_emitted",
                "candidates_merged",
                "candidates_split",
                "candidates_confirmed",
                "candidates_dismissed",
                "adjacent_concerns",
                "duplicate_validations_avoided",
            )
        ],
        _json("caps_json"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "benchmark_comparison",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "dataset_id",
            sa.Integer(),
            sa.ForeignKey("benchmark_dataset.id"),
            nullable=False,
        ),
        _json("thresholds_json", "{}"),
        _json("metrics_json", "{}"),
        sa.Column("status", sa.String(), nullable=False, server_default="created"),
        sa.Column(
            "include_contaminated",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "benchmark_comparison_evaluation",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "comparison_id",
            sa.Integer(),
            sa.ForeignKey("benchmark_comparison.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "evaluation_id",
            sa.Integer(),
            sa.ForeignKey("benchmark_evaluation.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "comparison_id", "evaluation_id", name="uq_benchmark_comparison_evaluation"
        ),
    )
    for table, columns in {
        "sast_surface_edge": (
            "sast_run_id",
            "source_surface_id",
            "target_surface_id",
            "edge_kind",
            "provenance",
            "fingerprint",
        ),
        "sast_threat_model": ("sast_run_id",),
        "sast_threat_scenario": ("sast_run_id", "scenario_key", "priority", "status"),
        "sast_coverage_obligation": (
            "sast_run_id",
            "obligation_key",
            "obligation_type",
            "priority",
            "source_scenario_id",
            "assigned_worker_id",
            "status",
        ),
        "sast_obligation_lead": (
            "sast_run_id",
            "obligation_id",
            "lead_id",
            "relationship",
        ),
        "sast_discovery_telemetry": ("sast_run_id", "phase", "strategy"),
        "benchmark_comparison": ("name", "dataset_id", "status"),
        "benchmark_comparison_evaluation": ("comparison_id", "evaluation_id"),
    }.items():
        for column in columns:
            op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade() -> None:
    op.drop_table("benchmark_comparison_evaluation")
    op.drop_table("benchmark_comparison")
    op.drop_table("sast_discovery_telemetry")
    op.drop_table("sast_obligation_lead")
    op.drop_table("sast_coverage_obligation")
    op.drop_table("sast_threat_scenario")
    op.drop_table("sast_threat_model")
    op.drop_table("sast_surface_edge")
    op.drop_index("ix_scan_lead_discovery_strategy", table_name="scan_lead")
    op.drop_index("ix_scan_lead_classification", table_name="scan_lead")
    op.drop_column("scan_lead", "provenance_json")
    op.drop_column("scan_lead", "discovery_strategy")
    op.drop_column("scan_lead", "classification")
    for name in ("component_key", "review_status", "confidence"):
        op.drop_column("sast_surface_item", name)
    for name in (
        "sast_validator_budget",
        "sast_closure_budget",
        "sast_threat_budget",
        "sast_baseline_budget",
        "sast_min_confidence",
        "sast_min_severity",
        "sast_dependency_findings",
        "sast_defense_in_depth_findings",
        "sast_audit_logging_findings",
        "sast_race_condition_findings",
        "sast_rate_limit_findings",
    ):
        op.drop_column("scanner_policy", name)
