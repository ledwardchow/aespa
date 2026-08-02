"""multi_repository_applications_and_campaigns

Revision ID: 00c6c82b48b7
Revises: 3d4e5f6a7b8c
Create Date: 2026-08-02 17:05:23.958276

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "00c6c82b48b7"
down_revision: Union[str, None] = "3d4e5f6a7b8c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "application",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("application", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_application_name"), ["name"], unique=True
        )

    op.create_table(
        "application_component",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("role", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["application.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "application_id", "name", name="uq_component_app_name"
        ),
    )
    with op.batch_alter_table("application_component", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_application_component_application_id"),
            ["application_id"],
            unique=False,
        )

    op.create_table(
        "component_snapshot",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("component_id", sa.Integer(), nullable=False),
        sa.Column("filename", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("stored_path", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["component_id"], ["application_component.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("component_snapshot", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_component_snapshot_component_id"),
            ["component_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_component_snapshot_sha256"), ["sha256"], unique=False
        )

    op.create_table(
        "application_target",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("target_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["application.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "application_id", "target_type", "target_id", name="uq_app_target"
        ),
    )
    with op.batch_alter_table("application_target", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_application_target_application_id"),
            ["application_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_application_target_target_id"),
            ["target_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_application_target_target_type"),
            ["target_type"],
            unique=False,
        )

    op.create_table(
        "component_target_hint",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("component_id", sa.Integer(), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("note", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["application.id"]),
        sa.ForeignKeyConstraint(["component_id"], ["application_component.id"]),
        sa.ForeignKeyConstraint(["target_id"], ["application_target.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "component_id", "target_id", name="uq_component_target_hint"
        ),
    )
    with op.batch_alter_table("component_target_hint", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_component_target_hint_application_id"),
            ["application_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_component_target_hint_component_id"),
            ["component_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_component_target_hint_target_id"),
            ["target_id"],
            unique=False,
        )

    op.create_table(
        "component_fact",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sast_run_id", sa.Integer(), nullable=False),
        sa.Column("component_id", sa.Integer(), nullable=True),
        sa.Column("fact_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("method", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("path", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("host", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("detail_json", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "evidence_location", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column("fingerprint", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["component_id"], ["application_component.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("component_fact", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_component_fact_component_id"),
            ["component_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_component_fact_fact_type"), ["fact_type"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_component_fact_fingerprint"),
            ["fingerprint"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_component_fact_sast_run_id"),
            ["sast_run_id"],
            unique=False,
        )

    op.create_table(
        "assessment_campaign",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("max_parallel_sast", sa.Integer(), nullable=False),
        sa.Column("llm_config_id", sa.Integer(), nullable=True),
        sa.Column("llm_profile_id", sa.Integer(), nullable=True),
        sa.Column("warnings_json", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("review_submitted_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["application.id"]),
        sa.ForeignKeyConstraint(["id"], ["run_identity.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["llm_config_id"], ["llm_config.id"]),
        sa.ForeignKeyConstraint(["llm_profile_id"], ["llm_profile.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("assessment_campaign", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_assessment_campaign_application_id"),
            ["application_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_assessment_campaign_status"), ["status"], unique=False
        )

    op.create_table(
        "campaign_source_member",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("component_id", sa.Integer(), nullable=False),
        sa.Column("snapshot_id", sa.Integer(), nullable=False),
        sa.Column("sast_run_id", sa.Integer(), nullable=True),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["run_identity.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["component_id"], ["application_component.id"]),
        sa.ForeignKeyConstraint(["snapshot_id"], ["component_snapshot.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "campaign_id", "component_id", name="uq_campaign_component"
        ),
    )
    with op.batch_alter_table("campaign_source_member", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_campaign_source_member_campaign_id"),
            ["campaign_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_campaign_source_member_component_id"),
            ["component_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_campaign_source_member_sast_run_id"),
            ["sast_run_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_campaign_source_member_snapshot_id"),
            ["snapshot_id"],
            unique=False,
        )

    op.create_table(
        "campaign_target_member",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("target_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("test_run_id", sa.Integer(), nullable=True),
        sa.Column("api_test_run_id", sa.Integer(), nullable=True),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["run_identity.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["target_id"], ["application_target.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campaign_id", "target_id", name="uq_campaign_target"),
    )
    with op.batch_alter_table("campaign_target_member", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_campaign_target_member_api_test_run_id"),
            ["api_test_run_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_campaign_target_member_campaign_id"),
            ["campaign_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_campaign_target_member_target_id"),
            ["target_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_campaign_target_member_target_type"),
            ["target_type"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_campaign_target_member_test_run_id"),
            ["test_run_id"],
            unique=False,
        )

    op.create_table(
        "component_connection",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("source_component_id", sa.Integer(), nullable=False),
        sa.Column("source_fact_id", sa.Integer(), nullable=False),
        sa.Column("target_component_id", sa.Integer(), nullable=False),
        sa.Column("target_fact_id", sa.Integer(), nullable=False),
        sa.Column("match_kind", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("rationale", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("evidence_json", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["run_identity.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["source_component_id"], ["application_component.id"]
        ),
        sa.ForeignKeyConstraint(["source_fact_id"], ["component_fact.id"]),
        sa.ForeignKeyConstraint(
            ["target_component_id"], ["application_component.id"]
        ),
        sa.ForeignKeyConstraint(["target_fact_id"], ["component_fact.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("component_connection", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_component_connection_campaign_id"),
            ["campaign_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_component_connection_source_component_id"),
            ["source_component_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_component_connection_source_fact_id"),
            ["source_fact_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_component_connection_target_component_id"),
            ["target_component_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_component_connection_target_fact_id"),
            ["target_fact_id"],
            unique=False,
        )

    op.create_table(
        "lead_target_mapping",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("target_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("rationale", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("evidence_json", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("copied_lead_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["run_identity.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["lead_id"], ["scan_lead.id"]),
        sa.ForeignKeyConstraint(["target_id"], ["application_target.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "campaign_id", "lead_id", "target_id", name="uq_lead_target"
        ),
    )
    with op.batch_alter_table("lead_target_mapping", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_lead_target_mapping_campaign_id"),
            ["campaign_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_lead_target_mapping_lead_id"), ["lead_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_lead_target_mapping_status"), ["status"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_lead_target_mapping_target_id"),
            ["target_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_lead_target_mapping_target_type"),
            ["target_type"],
            unique=False,
        )

    op.create_table(
        "scan_lead_component_provenance",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scan_lead_id", sa.Integer(), nullable=False),
        sa.Column("component_id", sa.Integer(), nullable=False),
        sa.Column("role", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("fact_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["component_id"], ["application_component.id"]),
        sa.ForeignKeyConstraint(["fact_id"], ["component_fact.id"]),
        sa.ForeignKeyConstraint(["scan_lead_id"], ["scan_lead.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "scan_lead_id", "component_id", name="uq_lead_component_provenance"
        ),
    )
    with op.batch_alter_table(
        "scan_lead_component_provenance", schema=None
    ) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_scan_lead_component_provenance_component_id"),
            ["component_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_scan_lead_component_provenance_scan_lead_id"),
            ["scan_lead_id"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_table("scan_lead_component_provenance")
    op.drop_table("lead_target_mapping")
    op.drop_table("component_connection")
    op.drop_table("campaign_target_member")
    op.drop_table("campaign_source_member")
    op.drop_table("assessment_campaign")
    op.drop_table("component_fact")
    op.drop_table("component_target_hint")
    op.drop_table("application_target")
    op.drop_table("component_snapshot")
    op.drop_table("application_component")
    op.drop_table("application")
