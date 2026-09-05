"""backfill effective ports in saved scope hosts

Revision ID: d4e5f6a7b8c9
Revises: c7d8e9f0a1b2
Create Date: 2026-08-18

"""

from __future__ import annotations

import json
from collections.abc import Sequence
from urllib.parse import urlparse

import sqlalchemy as sa

from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c7d8e9f0a1b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DEFAULT_PORTS = {"http": 80, "https": 443}


def _authority(entry: str, default_url: str) -> str:
    parsed_default = urlparse(default_url)
    try:
        default_port = parsed_default.port or _DEFAULT_PORTS.get(
            parsed_default.scheme.lower()
        )
    except ValueError:
        return ""

    parsed = urlparse(entry if "://" in entry else f"//{entry}")
    hostname = (parsed.hostname or "").lower().rstrip(".")
    if not hostname:
        return ""
    try:
        port = parsed.port
    except ValueError:
        return ""
    if port is None:
        port = (
            default_port
            if not parsed.scheme
            else _DEFAULT_PORTS.get(parsed.scheme.lower())
        )
    display_host = f"[{hostname}]" if ":" in hostname else hostname
    return f"{display_host}:{port}" if port is not None else display_host


def _backfill_table(table: str) -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(f"SELECT id, base_url, scope_hosts FROM {table}")  # noqa: S608
    ).mappings().all()
    for row in rows:
        try:
            entries = json.loads(row["scope_hosts"] or "[]")
        except (TypeError, json.JSONDecodeError):
            continue
        if not isinstance(entries, list):
            continue
        normalized: list[str] = []
        for entry in entries:
            if not isinstance(entry, str):
                continue
            authority = _authority(entry, row["base_url"])
            if authority and authority not in normalized:
                normalized.append(authority)
        bind.execute(
            sa.text(f"UPDATE {table} SET scope_hosts=:scope_hosts WHERE id=:id"),  # noqa: S608
            {"id": row["id"], "scope_hosts": json.dumps(normalized)},
        )


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    for table in ("site", "api_collection"):
        columns = (
            {column["name"] for column in inspector.get_columns(table)}
            if table in tables
            else set()
        )
        if {"id", "base_url", "scope_hosts"} <= columns:
            _backfill_table(table)


def downgrade() -> None:
    pass
