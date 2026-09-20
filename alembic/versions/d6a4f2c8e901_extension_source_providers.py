"""add extension settings and SAST source provenance

Revision ID: d6a4f2c8e901
Revises: a91e3b7c5d20
Create Date: 2026-09-20
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "d6a4f2c8e901"
down_revision: Union[str, Sequence[str], None] = "a91e3b7c5d20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "extension_setting" not in tables:
        op.create_table(
            "extension_setting",
            sa.Column("extension_id", sa.String(), nullable=False),
            sa.Column(
                "schema_version", sa.Integer(), nullable=False, server_default="1"
            ),
            sa.Column(
                "settings_json", sa.String(), nullable=False, server_default="{}"
            ),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("extension_id"),
        )
    if "sast_run" in tables:
        columns = {column["name"] for column in inspector.get_columns("sast_run")}
        additions = [
            ("source_provider", sa.String(), False, "upload"),
            ("source_locator", sa.String(), True, None),
            ("source_requested_ref", sa.String(), True, None),
            ("source_revision", sa.String(), True, None),
            ("source_archive_sha256", sa.String(), True, None),
            ("source_metadata_json", sa.String(), True, None),
        ]
        for name, column_type, nullable, default in additions:
            if name not in columns:
                op.add_column(
                    "sast_run",
                    sa.Column(
                        name,
                        column_type,
                        nullable=nullable,
                        server_default=default,
                    ),
                )
        op.create_index(
            "ix_sast_run_source_provider",
            "sast_run",
            ["source_provider"],
            unique=False,
            if_not_exists=True,
        )
        op.create_index(
            "ix_sast_run_source_revision",
            "sast_run",
            ["source_revision"],
            unique=False,
            if_not_exists=True,
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "sast_run" in tables:
        indexes = {index["name"] for index in inspector.get_indexes("sast_run")}
        if "ix_sast_run_source_revision" in indexes:
            op.drop_index("ix_sast_run_source_revision", table_name="sast_run")
        if "ix_sast_run_source_provider" in indexes:
            op.drop_index("ix_sast_run_source_provider", table_name="sast_run")
        columns = {column["name"] for column in inspector.get_columns("sast_run")}
        for name in (
            "source_metadata_json",
            "source_archive_sha256",
            "source_revision",
            "source_requested_ref",
            "source_locator",
            "source_provider",
        ):
            if name in columns:
                op.drop_column("sast_run", name)
    if "extension_setting" in tables:
        op.drop_table("extension_setting")
