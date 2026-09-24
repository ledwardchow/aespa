"""Qualify bundled extension IDs and secret namespaces.

Revision ID: d59e13af467b
Revises: c902a9f7fa25
Create Date: 2026-09-23
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "d59e13af467b"
down_revision: Union[str, Sequence[str], None] = "c902a9f7fa25"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _move_settings(connection, old: str, new: str) -> None:
    connection.execute(
        sa.text(
            "INSERT INTO extension_setting "
            "(extension_id, enabled, schema_version, settings_json, updated_at) "
            "SELECT :new, enabled, schema_version, settings_json, updated_at "
            "FROM extension_setting WHERE extension_id = :old "
            "AND NOT EXISTS (SELECT 1 FROM extension_setting WHERE extension_id = :new)"
        ),
        {"old": old, "new": new},
    )
    connection.execute(
        sa.text("DELETE FROM extension_setting WHERE extension_id = :id"),
        {"id": old},
    )


def _move_secrets(connection, old: str, new: str) -> None:
    connection.execute(
        sa.text(
            "INSERT INTO extension_secret (namespace, key, value, updated_at) "
            "SELECT :new, old.key, old.value, old.updated_at "
            "FROM extension_secret AS old WHERE old.namespace = :old "
            "AND NOT EXISTS (SELECT 1 FROM extension_secret AS current "
            "WHERE current.namespace = :new AND current.key = old.key)"
        ),
        {"old": old, "new": new},
    )
    connection.execute(
        sa.text("DELETE FROM extension_secret WHERE namespace = :namespace"),
        {"namespace": old},
    )


def upgrade() -> None:
    connection = op.get_bind()
    _move_settings(connection, "burp.suite", "aespa.burpsuite")
    _move_settings(connection, "github.repository", "aespa.githubrepository")
    _move_secrets(connection, "burp.suite", "aespa.burpsuite")
    _move_secrets(connection, "aespa.burp.suite", "aespa.burpsuite")
    if sa.inspect(connection).has_table("sast_run"):
        connection.execute(
            sa.text(
                "UPDATE sast_run SET source_provider = 'aespa.githubrepository' "
                "WHERE source_provider = 'github.repository'"
            )
        )


def downgrade() -> None:
    connection = op.get_bind()
    _move_settings(connection, "aespa.burpsuite", "burp.suite")
    _move_settings(connection, "aespa.githubrepository", "github.repository")
    _move_secrets(connection, "aespa.burpsuite", "burp.suite")
    if sa.inspect(connection).has_table("sast_run"):
        connection.execute(
            sa.text(
                "UPDATE sast_run SET source_provider = 'github.repository' "
                "WHERE source_provider = 'aespa.githubrepository'"
            )
        )
