"""Move built-in Burp settings to the bundled extension.

Revision ID: c902a9f7fa25
Revises: 465996cd1ec3
Create Date: 2026-09-23
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "c902a9f7fa25"
down_revision: Union[str, Sequence[str], None] = "465996cd1ec3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_EXTENSION_ID = "burp.suite"
_FIELDS = (
    "api_url",
    "scan_configuration_name",
    "scan_sqli",
    "scan_xss",
    "scan_command_injection",
    "scan_path_traversal",
    "scan_ssrf",
    "scan_xxe",
    "scan_ssti",
)


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = set(inspector.get_table_names())
    legacy = None
    if "burp_rest_api_config" in tables:
        legacy = (
            connection.execute(
                sa.text("SELECT * FROM burp_rest_api_config WHERE id = 1")
            )
            .mappings()
            .first()
        )
    specialist = None
    specialist_columns = (
        {column["name"] for column in inspector.get_columns("specialist_agent_config")}
        if "specialist_agent_config" in tables
        else set()
    )
    if "trigger_specialist_on_burp" in specialist_columns:
        specialist = connection.execute(
            sa.text(
                "SELECT trigger_specialist_on_burp FROM specialist_agent_config WHERE id = 1"
            )
        ).scalar_one_or_none()

    existing = (
        connection.execute(
            sa.text(
                "SELECT settings_json, enabled FROM extension_setting WHERE extension_id = :id"
            ),
            {"id": _EXTENSION_ID},
        )
        .mappings()
        .first()
    )
    settings = json.loads(existing["settings_json"] or "{}") if existing else {}
    if not isinstance(settings, dict):
        settings = {}
    if legacy:
        for key in _FIELDS:
            if key not in legacy or key in settings:
                continue
            value = legacy[key]
            settings[key] = (
                bool(value)
                if key.startswith("scan_") and key != "scan_configuration_name"
                else value
            )
    settings.setdefault("trigger_specialist", bool(specialist))
    enabled = (
        bool(existing["enabled"])
        if existing
        else bool(legacy["enabled"])
        if legacy
        else False
    )
    now = datetime.now(timezone.utc)
    if existing:
        connection.execute(
            sa.text(
                "UPDATE extension_setting SET enabled = :enabled, settings_json = :settings, "
                "schema_version = 1, updated_at = :updated WHERE extension_id = :id"
            ),
            {
                "id": _EXTENSION_ID,
                "enabled": enabled,
                "settings": json.dumps(settings),
                "updated": now,
            },
        )
    else:
        connection.execute(
            sa.text(
                "INSERT INTO extension_setting (extension_id, enabled, schema_version, settings_json, updated_at) "
                "VALUES (:id, :enabled, 1, :settings, :updated)"
            ),
            {
                "id": _EXTENSION_ID,
                "enabled": enabled,
                "settings": json.dumps(settings),
                "updated": now,
            },
        )
    if legacy and legacy["api_key"]:
        existing_secret = connection.execute(
            sa.text(
                "SELECT 1 FROM extension_secret WHERE namespace = :namespace AND key = 'api_key'"
            ),
            {"namespace": _EXTENSION_ID},
        ).first()
        if existing_secret is None:
            connection.execute(
                sa.text(
                    "INSERT INTO extension_secret (namespace, key, value, updated_at) "
                    "VALUES (:namespace, 'api_key', :value, :updated)"
                ),
                {
                    "namespace": _EXTENSION_ID,
                    "value": legacy["api_key"],
                    "updated": now,
                },
            )
    if "burp_rest_api_config" in tables:
        op.drop_table("burp_rest_api_config")
    if "trigger_specialist_on_burp" in specialist_columns:
        with op.batch_alter_table("specialist_agent_config") as batch:
            batch.drop_column("trigger_specialist_on_burp")


def downgrade() -> None:
    connection = op.get_bind()
    op.create_table(
        "burp_rest_api_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "api_url",
            sa.String(),
            nullable=False,
            server_default="http://127.0.0.1:1337",
        ),
        sa.Column("api_key", sa.String()),
        sa.Column("scan_configuration_name", sa.String()),
        *[
            sa.Column(key, sa.Boolean(), nullable=False, server_default=sa.text("1"))
            for key in _FIELDS
            if key.startswith("scan_") and key != "scan_configuration_name"
        ],
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    with op.batch_alter_table("specialist_agent_config") as batch:
        batch.add_column(
            sa.Column(
                "trigger_specialist_on_burp",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )
    row = (
        connection.execute(
            sa.text(
                "SELECT settings_json, enabled FROM extension_setting WHERE extension_id = :id"
            ),
            {"id": _EXTENSION_ID},
        )
        .mappings()
        .first()
    )
    if row:
        settings = json.loads(row["settings_json"] or "{}")
        secret = connection.execute(
            sa.text(
                "SELECT value FROM extension_secret WHERE namespace = :id AND key = 'api_key'"
            ),
            {"id": _EXTENSION_ID},
        ).scalar_one_or_none()
        columns = [
            "id",
            "enabled",
            "api_url",
            "api_key",
            "scan_configuration_name",
            *[
                key
                for key in _FIELDS
                if key.startswith("scan_") and key != "scan_configuration_name"
            ],
            "updated_at",
        ]
        values = {
            "id": 1,
            "enabled": bool(row["enabled"]),
            "api_url": settings.get("api_url") or "http://127.0.0.1:1337",
            "api_key": secret,
            "scan_configuration_name": settings.get("scan_configuration_name"),
            "updated_at": datetime.now(timezone.utc),
        }
        values.update(
            {
                key: bool(settings.get(key, True))
                for key in _FIELDS
                if key.startswith("scan_") and key != "scan_configuration_name"
            }
        )
        connection.execute(
            sa.text(
                f"INSERT INTO burp_rest_api_config ({', '.join(columns)}) "
                f"VALUES ({', '.join(':' + column for column in columns)})"
            ),
            values,
        )
        connection.execute(
            sa.text(
                "UPDATE specialist_agent_config SET trigger_specialist_on_burp = :enabled WHERE id = 1"
            ),
            {"enabled": bool(settings.get("trigger_specialist", False))},
        )
