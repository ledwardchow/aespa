"""add bounded SAST attack-path and mapper trace settings

Revision ID: f4a6b8c0d2e1
Revises: e1a7b9c3d5f0, 7f9d1cf4e066
Create Date: 2026-08-05

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "f4a6b8c0d2e1"
down_revision: Union[str, tuple[str, str], None] = (
    "e1a7b9c3d5f0",
    "7f9d1cf4e066",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_column(table: str, column: sa.Column) -> None:
    inspector = sa.inspect(op.get_bind())
    existing = (
        {item["name"] for item in inspector.get_columns(table)}
        if inspector.has_table(table)
        else set()
    )
    if inspector.has_table(table) and column.name not in existing:
        op.add_column(table, column)


def _create_index(
    name: str, table: str, columns: list[str], *, unique: bool = False
) -> None:
    inspector = sa.inspect(op.get_bind())
    existing = (
        {item["name"] for item in inspector.get_indexes(table)}
        if inspector.has_table(table)
        else set()
    )
    if inspector.has_table(table) and name not in existing:
        op.create_index(name, table, columns, unique=unique)


def upgrade() -> None:
    _add_column(
        "component_mapper_config",
        sa.Column("max_trace_edges", sa.Integer(), nullable=False, server_default="8"),
    )
    _add_column(
        "component_mapper_config",
        sa.Column(
            "max_trace_components", sa.Integer(), nullable=False, server_default="6"
        ),
    )
    _add_column(
        "component_mapper_config",
        sa.Column(
            "max_paths_per_lead", sa.Integer(), nullable=False, server_default="10"
        ),
    )
    _add_column(
        "component_mapper_config",
        sa.Column(
            "min_trace_confidence",
            sa.Float(),
            nullable=False,
            server_default="0.50",
        ),
    )

    _add_column(
        "scan_lead",
        sa.Column("origin_lead_id", sa.Integer(), nullable=True),
    )
    _add_column(
        "scan_lead",
        sa.Column("trace_path_key", sa.String(), nullable=True),
    )
    _add_column(
        "scan_lead",
        sa.Column("trace_status", sa.String(), nullable=False, server_default="none"),
    )
    _add_column(
        "scan_lead",
        sa.Column("trace_confidence", sa.Float(), nullable=True),
    )
    _create_index(
        "ix_scan_lead_origin_lead_id",
        "scan_lead",
        ["origin_lead_id"],
        unique=False,
    )
    _create_index(
        "ix_scan_lead_trace_path_key",
        "scan_lead",
        ["trace_path_key"],
        unique=False,
    )

    _add_column(
        "assessment_campaign",
        sa.Column("max_trace_edges", sa.Integer(), nullable=True),
    )
    _add_column(
        "assessment_campaign",
        sa.Column("max_trace_components", sa.Integer(), nullable=True),
    )
    _add_column(
        "assessment_campaign",
        sa.Column("max_paths_per_lead", sa.Integer(), nullable=True),
    )
    _add_column(
        "assessment_campaign",
        sa.Column("min_trace_confidence", sa.Float(), nullable=True),
    )

    _add_column(
        "component_connection",
        sa.Column("edge_kind", sa.String(), nullable=False, server_default="calls"),
    )
    _add_column(
        "component_connection",
        sa.Column("source_sast_run_id", sa.Integer(), nullable=True),
    )
    _add_column(
        "component_connection",
        sa.Column("target_sast_run_id", sa.Integer(), nullable=True),
    )
    _add_column(
        "component_connection",
        sa.Column(
            "path_scope", sa.String(), nullable=False, server_default="cross_component"
        ),
    )
    _create_index(
        "ix_component_connection_edge_kind",
        "component_connection",
        ["edge_kind"],
        unique=False,
    )
    _create_index(
        "ix_component_connection_source_sast_run_id",
        "component_connection",
        ["source_sast_run_id"],
        unique=False,
    )
    _create_index(
        "ix_component_connection_target_sast_run_id",
        "component_connection",
        ["target_sast_run_id"],
        unique=False,
    )

    _add_column(
        "lead_target_mapping",
        sa.Column(
            "auto_approved", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    _add_column(
        "lead_target_mapping",
        sa.Column("approved", sa.Boolean(), nullable=True),
    )
    _add_column(
        "lead_target_mapping",
        sa.Column("final_score", sa.Float(), nullable=True),
    )
    _add_column(
        "lead_target_mapping",
        sa.Column("change_reason", sa.String(), nullable=True),
    )
    _add_column(
        "lead_target_mapping",
        sa.Column("path_json", sa.String(), nullable=False, server_default="{}"),
    )
    _add_column(
        "lead_target_mapping",
        sa.Column(
            "approved_attack_path_json",
            sa.String(),
            nullable=False,
            server_default="{}",
        ),
    )
    _add_column(
        "lead_target_mapping",
        sa.Column(
            "final_attack_path_json", sa.String(), nullable=False, server_default="{}"
        ),
    )
    _add_column(
        "lead_target_mapping",
        sa.Column(
            "attack_path_changes_json", sa.String(), nullable=False, server_default="[]"
        ),
    )
    _add_column(
        "lead_target_mapping", sa.Column("path_status", sa.String(), nullable=True)
    )
    _add_column(
        "lead_target_mapping", sa.Column("edited_at", sa.DateTime(), nullable=True)
    )
    _create_index(
        "ix_lead_target_mapping_path_status",
        "lead_target_mapping",
        ["path_status"],
        unique=False,
    )
    _create_index(
        "uq_component_connection_edge",
        "component_connection",
        ["campaign_id", "source_fact_id", "target_fact_id", "edge_kind"],
        unique=True,
    )


def downgrade() -> None:
    for index_name, table_name in (
        ("ix_component_connection_target_sast_run_id", "component_connection"),
        ("ix_component_connection_source_sast_run_id", "component_connection"),
        ("ix_component_connection_edge_kind", "component_connection"),
        ("ix_lead_target_mapping_path_status", "lead_target_mapping"),
        ("ix_scan_lead_trace_path_key", "scan_lead"),
        ("ix_scan_lead_origin_lead_id", "scan_lead"),
    ):
        op.drop_index(index_name, table_name=table_name)

    for column in (
        "edited_at",
        "path_status",
        "attack_path_changes_json",
        "final_attack_path_json",
        "approved_attack_path_json",
        "path_json",
        "change_reason",
        "final_score",
        "approved",
        "auto_approved",
    ):
        op.drop_column("lead_target_mapping", column)

    op.drop_index("uq_component_connection_edge", table_name="component_connection")

    for column in (
        "path_scope",
        "target_sast_run_id",
        "source_sast_run_id",
        "edge_kind",
    ):
        op.drop_column("component_connection", column)

    for column in (
        "min_trace_confidence",
        "max_paths_per_lead",
        "max_trace_components",
        "max_trace_edges",
    ):
        op.drop_column("assessment_campaign", column)

    for column in (
        "trace_confidence",
        "trace_status",
        "trace_path_key",
        "origin_lead_id",
    ):
        op.drop_column("scan_lead", column)

    for column in (
        "min_trace_confidence",
        "max_paths_per_lead",
        "max_trace_components",
        "max_trace_edges",
    ):
        op.drop_column("component_mapper_config", column)
