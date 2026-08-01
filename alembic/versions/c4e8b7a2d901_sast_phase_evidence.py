"""persist SAST phases, coverage, and structured candidate evidence

Revision ID: c4e8b7a2d901
Revises: a7c8e9f0b1d2
Create Date: 2026-08-01

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "c4e8b7a2d901"
down_revision: Union[str, None] = "a7c8e9f0b1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sast_run", sa.Column("phase_state_json", sa.String(), nullable=True))
    op.add_column("sast_run", sa.Column("coverage_json", sa.String(), nullable=True))
    op.add_column("sast_run", sa.Column("report_json", sa.String(), nullable=True))

    op.add_column("scan_lead", sa.Column("fingerprint", sa.String(), nullable=False, server_default=""))
    op.add_column("scan_lead", sa.Column("suggested_endpoint", sa.String(), nullable=False, server_default=""))
    op.add_column("scan_lead", sa.Column("source_trace_json", sa.String(), nullable=False, server_default="{}"))
    op.add_column("scan_lead", sa.Column("control_trace_json", sa.String(), nullable=False, server_default="[]"))
    op.add_column("scan_lead", sa.Column("sink_trace_json", sa.String(), nullable=False, server_default="{}"))
    op.add_column("scan_lead", sa.Column("counterevidence_json", sa.String(), nullable=False, server_default="[]"))
    op.add_column("scan_lead", sa.Column("proof_gaps_json", sa.String(), nullable=False, server_default="[]"))
    op.add_column("scan_lead", sa.Column("validation_status", sa.String(), nullable=False, server_default="pending"))
    op.add_column("scan_lead", sa.Column("validation_reasoning", sa.String(), nullable=False, server_default=""))
    op.add_column("scan_lead", sa.Column("attack_path_json", sa.String(), nullable=False, server_default="{}"))
    op.add_column("scan_lead", sa.Column("reportable", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_index("ix_scan_lead_fingerprint", "scan_lead", ["fingerprint"], unique=False)
    op.create_index("ix_scan_lead_validation_status", "scan_lead", ["validation_status"], unique=False)
    op.create_index("ix_scan_lead_reportable", "scan_lead", ["reportable"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_scan_lead_reportable", table_name="scan_lead")
    op.drop_index("ix_scan_lead_validation_status", table_name="scan_lead")
    op.drop_index("ix_scan_lead_fingerprint", table_name="scan_lead")
    for column in (
        "reportable",
        "attack_path_json",
        "validation_reasoning",
        "validation_status",
        "proof_gaps_json",
        "counterevidence_json",
        "sink_trace_json",
        "control_trace_json",
        "source_trace_json",
        "suggested_endpoint",
        "fingerprint",
    ):
        op.drop_column("scan_lead", column)
    op.drop_column("sast_run", "report_json")
    op.drop_column("sast_run", "coverage_json")
    op.drop_column("sast_run", "phase_state_json")
