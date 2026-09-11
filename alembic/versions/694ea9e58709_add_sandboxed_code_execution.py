"""add sandboxed code execution

Revision ID: 694ea9e58709
Revises: cb46a763a5b5
Create Date: 2026-09-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

revision: str = "694ea9e58709"
down_revision: str | None = "cb46a763a5b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "code_execution_config",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("backend", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("image_ref", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "allowed_roles_json", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column("timeout_s", sa.Integer(), nullable=False),
        sa.Column("memory_mb", sa.Integer(), nullable=False),
        sa.Column("cpu_cores", sa.Float(), nullable=False),
        sa.Column("pids_limit", sa.Integer(), nullable=False),
        sa.Column("workspace_mb", sa.Integer(), nullable=False),
        sa.Column("output_limit_bytes", sa.Integer(), nullable=False),
        sa.Column("artifact_limit_bytes", sa.Integer(), nullable=False),
        sa.Column("max_requests_per_execution", sa.Integer(), nullable=False),
        sa.Column("max_concurrent_requests", sa.Integer(), nullable=False),
        sa.Column("max_concurrent_executions", sa.Integer(), nullable=False),
        sa.Column("retain_redacted_source", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "code_execution",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_kind", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("agent_role", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("agent_step", sa.Integer(), nullable=True),
        sa.Column("purpose", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("code_redacted", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("code_sha256", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "runtime_backend", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column("runtime_version", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("image_ref", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column(
            "protocol_version", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column("limits_json", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False),
        sa.Column("denied_request_count", sa.Integer(), nullable=False),
        sa.Column("stdout_preview", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("stderr_preview", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("result_json", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("error_message", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["run_identity.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for name in ("agent_id", "run_id", "run_kind", "status"):
        op.create_index(f"ix_code_execution_{name}", "code_execution", [name])
    op.create_table(
        "code_artifact",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("execution_id", sa.Integer(), nullable=False),
        sa.Column("direction", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("logical_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("content_type", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("stored_path", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["execution_id"], ["code_execution.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_code_artifact_execution_id", "code_artifact", ["execution_id"])

    string_columns = (
        "batch_id",
        "agent_id",
        "owasp_category",
        "test_class",
        "request_body_encoding",
        "request_body_sha256",
        "response_body_encoding",
        "response_body_sha256",
    )
    integer_columns = (
        "code_execution_id",
        "batch_index",
        "agent_step",
        "obligation_id",
        "request_body_size",
        "response_body_size",
    )
    indexed = (
        "code_execution_id",
        "batch_id",
        "agent_id",
        "owasp_category",
        "test_class",
        "obligation_id",
    )
    with op.batch_alter_table("traffic_entry") as batch_op:
        for name in string_columns:
            batch_op.add_column(
                sa.Column(name, sqlmodel.sql.sqltypes.AutoString(), nullable=True)
            )
        for name in integer_columns:
            batch_op.add_column(sa.Column(name, sa.Integer(), nullable=True))
        for name in indexed:
            batch_op.create_index(f"ix_traffic_entry_{name}", [name])
        batch_op.create_foreign_key(
            "fk_traffic_entry_code_execution_id",
            "code_execution",
            ["code_execution_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    columns = (
        "response_body_sha256",
        "response_body_size",
        "response_body_encoding",
        "request_body_sha256",
        "request_body_size",
        "request_body_encoding",
        "obligation_id",
        "test_class",
        "owasp_category",
        "agent_step",
        "agent_id",
        "batch_index",
        "batch_id",
        "code_execution_id",
    )
    indexed = (
        "obligation_id",
        "test_class",
        "owasp_category",
        "agent_id",
        "batch_id",
        "code_execution_id",
    )
    with op.batch_alter_table("traffic_entry") as batch_op:
        batch_op.drop_constraint(
            "fk_traffic_entry_code_execution_id", type_="foreignkey"
        )
        for name in indexed:
            batch_op.drop_index(f"ix_traffic_entry_{name}")
        for name in columns:
            batch_op.drop_column(name)
    op.drop_index("ix_code_artifact_execution_id", table_name="code_artifact")
    op.drop_table("code_artifact")
    for name in ("status", "run_kind", "run_id", "agent_id"):
        op.drop_index(f"ix_code_execution_{name}", table_name="code_execution")
    op.drop_table("code_execution")
    op.drop_table("code_execution_config")
