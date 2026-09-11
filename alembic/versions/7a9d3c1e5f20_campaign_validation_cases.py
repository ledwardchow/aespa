"""add executable campaign validation cases

Revision ID: 7a9d3c1e5f20
Revises: 694ea9e58709
Create Date: 2026-09-06
"""

from typing import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

revision: str = "7a9d3c1e5f20"
down_revision: str | None = "91c4e7a2d5b8"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "campaign_validation_case",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("mapping_id", sa.Integer(), nullable=False),
        sa.Column("target_member_id", sa.Integer(), nullable=False),
        sa.Column("origin_lead_id", sa.Integer(), nullable=False),
        sa.Column("assertion_key", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("static_path_json", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("live_binding_json", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("readiness_status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("blocker_codes_json", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("copied_lead_id", sa.Integer(), nullable=True),
        sa.Column("finding_id", sa.Integer(), nullable=True),
        sa.Column("execution_status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("outcome_reason", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("baseline_evidence_json", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("mutated_evidence_json", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["assessment_campaign.id"]),
        sa.ForeignKeyConstraint(["mapping_id"], ["lead_target_mapping.id"]),
        sa.ForeignKeyConstraint(["target_member_id"], ["campaign_target_member.id"]),
        sa.ForeignKeyConstraint(["origin_lead_id"], ["scan_lead.id"]),
        sa.ForeignKeyConstraint(["copied_lead_id"], ["scan_lead.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["finding_id"], ["scan_finding.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "mapping_id", "target_member_id", "assertion_key",
            name="uq_campaign_validation_case_scope",
        ),
    )
    for name, columns in (
        ("ix_campaign_validation_case_campaign_id", ["campaign_id"]),
        ("ix_campaign_validation_case_mapping_id", ["mapping_id"]),
        ("ix_campaign_validation_case_target_member_id", ["target_member_id"]),
        ("ix_campaign_validation_case_origin_lead_id", ["origin_lead_id"]),
        ("ix_campaign_validation_case_assertion_key", ["assertion_key"]),
        ("ix_campaign_validation_case_readiness_status", ["readiness_status"]),
        ("ix_campaign_validation_case_copied_lead_id", ["copied_lead_id"]),
        ("ix_campaign_validation_case_finding_id", ["finding_id"]),
        ("ix_campaign_validation_case_execution_status", ["execution_status"]),
    ):
        op.create_index(name, "campaign_validation_case", columns)


def downgrade() -> None:
    op.drop_table("campaign_validation_case")
