from __future__ import annotations

import json
import re
from collections.abc import Callable
from urllib.parse import parse_qsl, urlsplit

import sqlalchemy as sa

from alembic import op

revision = "45623834b15e"
down_revision = "91c4b6e7a205"
branch_labels = None
depends_on = None


def _pattern(url: str) -> str:
    parts = urlsplit(url)
    path = re.sub(r"(?<=/)\d+(?=/|$)", "{id}", parts.path or "/")
    query = parse_qsl(parts.query, keep_blank_values=True)
    return path + (
        "?"
        + "&".join(f"{key}={{{key}}}" if value else f"{key}=" for key, value in query)
        if query
        else ""
    )


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def _ensure_column(table: str, column: sa.Column) -> None:
    if column.name not in _columns(table):
        op.add_column(table, column)


def _ensure_index(name: str, table: str, columns: list[str], **kwargs: object) -> None:
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table)}
    if name not in indexes:
        op.create_index(name, table, columns, **kwargs)


def _recover_batch_table(table: str) -> None:
    temporary = f"_alembic_tmp_{table}"
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if temporary not in tables:
        return
    if table in tables:
        op.drop_table(temporary)
    else:
        op.rename_table(temporary, table)


_BASE_INDEX_COLUMNS = {
    "scan_obligation": (
        "owasp_category",
        "route_template",
        "run_id",
        "run_kind",
        "status",
        "vulnerability_technique",
    ),
    "scan_finding": (
        "api_test_run_id",
        "finding_source",
        "origin_lead_id",
        "origin_reference",
        "origin_run_id",
        "origin_run_type",
        "origin_type",
        "owasp_api_category",
        "owasp_category",
        "page_id",
        "public_reference",
        "test_run_id",
    ),
    "probe_execution": ("obligation_id", "run_id", "run_kind", "traffic_id"),
    "specialist_handoff": (
        "agent_id",
        "attack_class",
        "canonical_url",
        "finding_id",
        "fingerprint",
        "page_id",
        "run_id",
        "run_kind",
        "status",
    ),
}


def _ensure_constraints(
    table: str,
    *,
    foreign_keys: tuple[tuple[str, str, str, str, str | None], ...] = (),
    unique: tuple[tuple[str, list[str]], ...] = (),
    checks: tuple[tuple[str, str], ...] = (),
) -> None:
    inspector = sa.inspect(op.get_bind())
    existing_foreign_keys = {key["name"] for key in inspector.get_foreign_keys(table)}
    existing_unique = {key["name"] for key in inspector.get_unique_constraints(table)}
    existing_checks = {
        check["name"] for check in inspector.get_check_constraints(table)
    }
    missing_foreign_keys = [
        key for key in foreign_keys if key[0] not in existing_foreign_keys
    ]
    missing_unique = [key for key in unique if key[0] not in existing_unique]
    missing_checks = [check for check in checks if check[0] not in existing_checks]
    if not (missing_foreign_keys or missing_unique or missing_checks):
        return
    with op.batch_alter_table(table) as batch:
        for name, target, column, target_column, ondelete in missing_foreign_keys:
            batch.create_foreign_key(
                name, target, [column], [target_column], ondelete=ondelete
            )
        for name, columns in missing_unique:
            batch.create_unique_constraint(name, columns)
        for name, condition in missing_checks:
            batch.create_check_constraint(name, condition)


def _upgrade() -> None:
    for table in (
        "scan_obligation",
        "scan_finding",
        "probe_execution",
        "specialist_handoff",
    ):
        _recover_batch_table(table)
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    _ensure_column(
        "test_run",
        sa.Column(
            "discovery_completeness",
            sa.String(),
            nullable=False,
            server_default="legacy_unknown",
        ),
    )
    if "discovered_target" not in tables:
        op.create_table(
            "discovered_target",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "test_run_id",
                sa.Integer(),
                sa.ForeignKey("run_identity.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("url", sa.String(), nullable=False),
            sa.Column("state_key", sa.String()),
            sa.Column("state_identity", sa.String(), nullable=False),
            sa.Column("route_pattern", sa.String(), nullable=False),
            sa.Column("discovered_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint(
                "test_run_id",
                "url",
                "state_identity",
                name="uq_discovered_target_identity",
            ),
        )
    _ensure_index(
        "ix_discovered_target_test_run_id", "discovered_target", ["test_run_id"]
    )
    _ensure_index(
        "ix_discovered_target_route_pattern", "discovered_target", ["route_pattern"]
    )
    if "target_discovery" not in tables:
        op.create_table(
            "target_discovery",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "test_run_id",
                sa.Integer(),
                sa.ForeignKey("run_identity.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "target_id",
                sa.Integer(),
                sa.ForeignKey("discovered_target.id"),
                nullable=False,
            ),
            sa.Column("source_key", sa.String(), nullable=False),
            sa.Column("source_page_id", sa.Integer(), sa.ForeignKey("crawled_page.id")),
            sa.Column("source_state_key", sa.String()),
            sa.Column("actor_key", sa.String(), nullable=False),
            sa.Column("source_kind", sa.String(), nullable=False),
            sa.Column("source_ref", sa.String()),
            sa.Column("discovered_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint(
                "target_id", "source_key", name="uq_target_discovery_source"
            ),
        )
    _ensure_index(
        "ix_target_discovery_test_run_id", "target_discovery", ["test_run_id"]
    )
    _ensure_index("ix_target_discovery_target_id", "target_discovery", ["target_id"])
    _ensure_index("ix_target_discovery_actor_key", "target_discovery", ["actor_key"])
    if "target_access_observation" not in tables:
        op.create_table(
            "target_access_observation",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "test_run_id",
                sa.Integer(),
                sa.ForeignKey("run_identity.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "target_id",
                sa.Integer(),
                sa.ForeignKey("discovered_target.id"),
                nullable=False,
            ),
            sa.Column("method", sa.String(), nullable=False),
            sa.Column("actor_key", sa.String(), nullable=False),
            sa.Column("source_kind", sa.String(), nullable=False),
            sa.Column("source_id", sa.Integer(), nullable=False),
            sa.Column("result", sa.String(), nullable=False),
            sa.Column("observed_at", sa.DateTime(), nullable=False),
            sa.CheckConstraint(
                "result IN ('reached', 'denied', 'unknown')",
                name="ck_target_access_result",
            ),
            sa.UniqueConstraint(
                "test_run_id",
                "source_kind",
                "source_id",
                name="uq_target_access_source",
            ),
        )
    _ensure_index(
        "ix_target_access_observation_test_run_id",
        "target_access_observation",
        ["test_run_id"],
    )
    _ensure_index(
        "ix_target_access_observation_target_id",
        "target_access_observation",
        ["target_id"],
    )
    _ensure_index(
        "ix_target_access_observation_actor_key",
        "target_access_observation",
        ["actor_key"],
    )
    if "scan_obligation" in tables:
        for column in (
            sa.Column(
                "scope_kind", sa.String(), nullable=False, server_default="route"
            ),
            sa.Column("target_id", sa.Integer()),
            sa.Column("selection_key", sa.String()),
            sa.Column("body_identity", sa.String()),
            sa.Column("baseline_actor_key", sa.String()),
            sa.Column("comparison_actor_key", sa.String()),
            sa.Column("baseline_observation_id", sa.Integer()),
            sa.Column("parent_page_cell_id", sa.Integer()),
            sa.Column("parent_test_class", sa.String()),
        ):
            _ensure_column("scan_obligation", column)
        _ensure_constraints(
            "scan_obligation",
            foreign_keys=(
                (
                    "fk_scan_obligation_target",
                    "discovered_target",
                    "target_id",
                    "id",
                    None,
                ),
                (
                    "fk_scan_obligation_baseline",
                    "target_access_observation",
                    "baseline_observation_id",
                    "id",
                    None,
                ),
                (
                    "fk_scan_obligation_parent_cell",
                    "page_owasp_test",
                    "parent_page_cell_id",
                    "id",
                    None,
                ),
            ),
            unique=(
                ("uq_object_check_selection", ["run_kind", "run_id", "selection_key"]),
            ),
            checks=(
                ("ck_scan_obligation_scope_kind", "scope_kind IN ('route', 'object')"),
            ),
        )
        _ensure_index("ix_scan_obligation_target_id", "scan_obligation", ["target_id"])
    if "scan_finding" in tables:
        _ensure_column("scan_finding", sa.Column("object_check_id", sa.Integer()))
        _ensure_constraints(
            "scan_finding",
            foreign_keys=(
                (
                    "fk_scan_finding_object_check",
                    "scan_obligation",
                    "object_check_id",
                    "id",
                    "SET NULL",
                ),
            ),
        )
        _ensure_index(
            "ix_scan_finding_object_check_id", "scan_finding", ["object_check_id"]
        )
    if "probe_execution" in tables:
        for column in (
            sa.Column("target_id", sa.Integer()),
            sa.Column("request_identity", sa.String()),
            sa.Column("acting_actor_key", sa.String()),
        ):
            _ensure_column("probe_execution", column)
        _ensure_constraints(
            "probe_execution",
            foreign_keys=(
                (
                    "fk_probe_execution_target",
                    "discovered_target",
                    "target_id",
                    "id",
                    None,
                ),
            ),
        )
        _ensure_index("ix_probe_execution_target_id", "probe_execution", ["target_id"])
    if "specialist_handoff" in tables:
        for column in (
            sa.Column("scope_key", sa.String()),
            sa.Column("revision_key", sa.String()),
            sa.Column("method", sa.String(), nullable=False, server_default="GET"),
            sa.Column(
                "state_identity", sa.String(), nullable=False, server_default="[null]"
            ),
            sa.Column("body_identity", sa.String()),
            sa.Column(
                "actor_key",
                sa.String(),
                nullable=False,
                server_default="unknown:unresolved",
            ),
            sa.Column("comparison_actor_key", sa.String()),
        ):
            _ensure_column("specialist_handoff", column)
        _ensure_constraints(
            "specialist_handoff",
            unique=(
                (
                    "uq_specialist_handoff_revision",
                    ["run_kind", "run_id", "scope_key", "revision_key"],
                ),
            ),
        )
        _ensure_index(
            "ix_specialist_handoff_scope_key", "specialist_handoff", ["scope_key"]
        )
        _ensure_index(
            "uq_specialist_handoff_active_scope",
            "specialist_handoff",
            ["run_kind", "run_id", "scope_key"],
            unique=True,
            sqlite_where=sa.text(
                "status IN ('queued', 'running') AND scope_key IS NOT NULL"
            ),
        )

    # An interrupted SQLite batch can leave only the temporary table. Its
    # data and constraints survive the rename above, but indexes are created
    # after that rename and still need to be restored on retry.
    for table, columns in _BASE_INDEX_COLUMNS.items():
        if table in tables:
            for column in columns:
                _ensure_index(f"ix_{table}_{column}", table, [column])

    connection = op.get_bind()
    if "crawled_page" in tables:
        for row in connection.execute(
            sa.text(
                "SELECT test_run_id, url, state_key FROM crawled_page WHERE url IS NOT NULL"
            )
        ):
            connection.execute(
                sa.text(
                    "INSERT OR IGNORE INTO discovered_target (test_run_id,url,state_key,state_identity,route_pattern,discovered_at) VALUES (:run,:url,:state,:identity,:pattern,CURRENT_TIMESTAMP)"
                ),
                {
                    "run": row.test_run_id,
                    "url": row.url,
                    "state": row.state_key,
                    "identity": json.dumps([row.state_key], separators=(",", ":")),
                    "pattern": _pattern(row.url),
                },
            )
    if "target_intel_item" in tables:
        for row in connection.execute(
            sa.text(
                "SELECT test_run_id, value FROM target_intel_item WHERE source='dom_link' AND kind='endpoint' AND value IS NOT NULL"
            )
        ):
            connection.execute(
                sa.text(
                    "INSERT OR IGNORE INTO discovered_target (test_run_id,url,state_key,state_identity,route_pattern,discovered_at) VALUES (:run,:url,NULL,:identity,:pattern,CURRENT_TIMESTAMP)"
                ),
                {
                    "run": row.test_run_id,
                    "url": row.value,
                    "identity": json.dumps([None], separators=(",", ":")),
                    "pattern": _pattern(row.value),
                },
            )


def _with_sqlite_foreign_keys_suspended(action: Callable[[], None]) -> None:
    connection = op.get_bind()
    if connection.dialect.name != "sqlite":
        action()
        return

    # SQLite batch alterations replace tables. Existing scan rows refer to
    # these tables, so the replacement must run with FK checks suspended.
    with op.get_context().autocommit_block():
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
    try:
        action()
    finally:
        with op.get_context().autocommit_block():
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")


def upgrade() -> None:
    _with_sqlite_foreign_keys_suspended(_upgrade)


def _downgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "scan_finding" in tables:
        with op.batch_alter_table("scan_finding") as batch:
            batch.drop_index("ix_scan_finding_object_check_id")
            batch.drop_constraint("fk_scan_finding_object_check", type_="foreignkey")
            batch.drop_column("object_check_id")
    if "specialist_handoff" in tables:
        op.drop_index(
            "uq_specialist_handoff_active_scope", table_name="specialist_handoff"
        )
        with op.batch_alter_table("specialist_handoff") as batch:
            batch.drop_index("ix_specialist_handoff_scope_key")
            batch.drop_constraint("uq_specialist_handoff_revision", type_="unique")
            batch.drop_column("comparison_actor_key")
            batch.drop_column("actor_key")
            batch.drop_column("body_identity")
            batch.drop_column("state_identity")
            batch.drop_column("method")
            batch.drop_column("revision_key")
            batch.drop_column("scope_key")
    if "probe_execution" in tables:
        with op.batch_alter_table("probe_execution") as batch:
            batch.drop_index("ix_probe_execution_target_id")
            batch.drop_constraint("fk_probe_execution_target", type_="foreignkey")
            batch.drop_column("acting_actor_key")
            batch.drop_column("request_identity")
            batch.drop_column("target_id")
    if "scan_obligation" in tables:
        with op.batch_alter_table("scan_obligation") as batch:
            batch.drop_index("ix_scan_obligation_target_id")
            batch.drop_constraint("ck_scan_obligation_scope_kind", type_="check")
            batch.drop_constraint("uq_object_check_selection", type_="unique")
            batch.drop_constraint("fk_scan_obligation_parent_cell", type_="foreignkey")
            batch.drop_constraint("fk_scan_obligation_baseline", type_="foreignkey")
            batch.drop_constraint("fk_scan_obligation_target", type_="foreignkey")
            batch.drop_column("parent_test_class")
            batch.drop_column("parent_page_cell_id")
            batch.drop_column("baseline_observation_id")
            batch.drop_column("comparison_actor_key")
            batch.drop_column("baseline_actor_key")
            batch.drop_column("body_identity")
            batch.drop_column("selection_key")
            batch.drop_column("target_id")
            batch.drop_column("scope_kind")
    op.drop_table("target_access_observation")
    op.drop_table("target_discovery")
    op.drop_table("discovered_target")
    op.drop_column("test_run", "discovery_completeness")


def downgrade() -> None:
    _with_sqlite_foreign_keys_suspended(_downgrade)
