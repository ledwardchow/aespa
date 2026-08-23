"""add specialist handoff ownership and dispatch controls

Revision ID: e5b7c9d1f3a2
Revises: d4e5f6a7b8c9
Create Date: 2026-08-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e5b7c9d1f3a2"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "specialist_agent_config" in tables:
        columns = {
            column["name"]
            for column in inspector.get_columns("specialist_agent_config")
        }
        with op.batch_alter_table("specialist_agent_config") as batch_op:
            if "auto_dispatch_enabled" not in columns:
                batch_op.add_column(
                    sa.Column(
                        "auto_dispatch_enabled",
                        sa.Boolean(),
                        nullable=False,
                        server_default=sa.true(),
                    )
                )
            if "max_queued" not in columns:
                batch_op.add_column(
                    sa.Column(
                        "max_queued",
                        sa.Integer(),
                        nullable=False,
                        server_default="20",
                    )
                )

    if (
        "specialist_handoff" in tables
        or not {
            "run_identity",
            "scan_finding",
        }
        <= tables
    ):
        return

    op.create_table(
        "specialist_handoff",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_kind", sa.String(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("fingerprint", sa.String(), nullable=False),
        sa.Column("attack_class", sa.String(), nullable=False),
        sa.Column("target_url", sa.String(), nullable=False),
        sa.Column("canonical_url", sa.String(), nullable=False),
        sa.Column("parameter", sa.String(), nullable=True),
        sa.Column("session_label", sa.String(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("rationale", sa.String(), nullable=False, server_default=""),
        sa.Column(
            "dispatch_source", sa.String(), nullable=False, server_default="test_lead"
        ),
        sa.Column("status", sa.String(), nullable=False, server_default="queued"),
        sa.Column("agent_id", sa.String(), nullable=True),
        sa.Column("finding_id", sa.Integer(), nullable=True),
        sa.Column("outcome", sa.String(), nullable=True),
        sa.Column(
            "feedback_delivered",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["run_identity.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["finding_id"], ["scan_finding.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint(
            "run_kind", "run_id", "fingerprint", name="uq_specialist_handoff_scope"
        ),
    )
    for column in (
        "run_kind",
        "run_id",
        "fingerprint",
        "attack_class",
        "canonical_url",
        "status",
        "agent_id",
        "finding_id",
    ):
        op.create_index(
            f"ix_specialist_handoff_{column}", "specialist_handoff", [column]
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "specialist_handoff" in tables:
        op.drop_table("specialist_handoff")
    if "specialist_agent_config" in tables:
        columns = {
            column["name"]
            for column in inspector.get_columns("specialist_agent_config")
        }
        with op.batch_alter_table("specialist_agent_config") as batch_op:
            if "max_queued" in columns:
                batch_op.drop_column("max_queued")
            if "auto_dispatch_enabled" in columns:
                batch_op.drop_column("auto_dispatch_enabled")
