"""Add opt-in grouped page crawling settings and state.

Revision ID: f1df15dddd52
Revises: 82f9567eec6a
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "f1df15dddd52"
down_revision = "82f9567eec6a"
branch_labels = None
depends_on = None


_TEST_RUN_COLUMNS = (
    ("page_selection", sa.String(), "'each_url'"),
    ("crawl_started_once", sa.Boolean(), "0"),
    ("route_groups_json", sa.String(), "'[]'"),
    ("route_sampling_state_json", sa.String(), "'{}'"),
)


def _columns(table: str) -> set[str] | None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return None
    return {item["name"] for item in inspector.get_columns(table)}


def upgrade() -> None:
    # Plain ADD COLUMN instead of batch mode: SQLite supports adding NOT NULL
    # columns with a constant default in place, and a batch rebuild would
    # DROP TABLE test_run, which fails while foreign-key checks are on.
    # Tables may be missing on pre-Alembic databases; the legacy upgrade
    # creates them afterwards with the current schema.
    saved_crawl = _columns("saved_crawl")
    if saved_crawl is not None and "page_selection" not in saved_crawl:
        op.add_column(
            "saved_crawl",
            sa.Column(
                "page_selection",
                sa.String(),
                server_default=sa.text("'each_url'"),
                nullable=False,
            ),
        )
    test_run = _columns("test_run")
    if test_run is None:
        return
    for name, type_, default in _TEST_RUN_COLUMNS:
        if name not in test_run:
            op.add_column(
                "test_run",
                sa.Column(name, type_, server_default=sa.text(default), nullable=False),
            )
    if {"started_at", "pages_discovered", "status"} <= test_run:
        op.execute(
            "UPDATE test_run SET crawl_started_once = 1 "
            "WHERE started_at IS NOT NULL OR pages_discovered > 0 "
            "OR status != 'pending'"
        )


def downgrade() -> None:
    # Native DROP COLUMN (SQLite 3.35+) avoids a batch table rebuild.
    test_run = _columns("test_run") or set()
    for name, _type, _default in reversed(_TEST_RUN_COLUMNS):
        if name in test_run:
            op.execute(f"ALTER TABLE test_run DROP COLUMN {name}")
    if "page_selection" in (_columns("saved_crawl") or set()):
        op.execute("ALTER TABLE saved_crawl DROP COLUMN page_selection")
