"""Give every run kind one global id namespace.

Older databases stored web, API, and SAST ids in separate autoincrement
sequences.  This revision creates the shared identity table, remaps old rows,
and replaces run foreign keys with cascading foreign keys to that table.

Rows that cannot be assigned to one owner are removed.  Keeping an uncertain
log or finding is worse than losing it: it can make a later run appear to have
tested the wrong target.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import sqlalchemy as sa

from alembic import op

revision = "e1a7b9c3d5f0"
down_revision = "d2f9a6b1c340"
branch_labels = None
depends_on = None


PARENT_TABLES = {
    "web": "test_run",
    "api": "api_test_run",
    "sast": "sast_run",
}

SHARED_RUN_COLUMNS = {
    "agent_log": ("test_run_id",),
    "scan_log": ("test_run_id",),
    "scanner_session": ("test_run_id",),
    "alice_chat_session": ("test_run_id",),
    "phase_checkpoint": ("run_id",),
    "scan_obligation": ("run_id",),
    "probe_execution": ("run_id",),
}

WEB_RUN_COLUMNS = {
    "crawled_page": ("test_run_id",),
    "page_owasp_test": ("test_run_id",),
    "page_link": ("test_run_id",),
    "page_credential_view": ("test_run_id",),
    "target_intel_item": ("test_run_id",),
    "scan_checkpoint": ("test_run_id",),
}

RUN_FK_COLUMNS = {
    **{
        table: {column: False for column in columns}
        for table, columns in WEB_RUN_COLUMNS.items()
    },
    **{
        table: {column: False for column in columns}
        for table, columns in SHARED_RUN_COLUMNS.items()
    },
    "test_run": {"id": False},
    "api_test_run": {"id": False},
    "sast_run": {"id": False},
    "api_endpoint_test": {"api_test_run_id": False},
    "traffic_entry": {"test_run_id": True, "api_test_run_id": True},
    "scan_finding": {"test_run_id": True, "api_test_run_id": True},
}


def _bind():
    return op.get_bind()


def _tables() -> set[str]:
    return set(sa.inspect(_bind()).get_table_names())


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(_bind()).get_columns(table)}


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _fetch_ids(table: str) -> list[int]:
    if table not in _tables() or "id" not in _columns(table):
        return []
    return [
        int(row[0])
        for row in _bind().execute(
            sa.text(f"SELECT id FROM {_quote(table)} ORDER BY id")
        )
    ]


def _insert_identity(kind: str, legacy_id: int) -> int:
    bind = _bind()
    existing = bind.execute(
        sa.text("SELECT id FROM run_identity WHERE id = :id"), {"id": legacy_id}
    ).scalar()
    if existing is None:
        bind.execute(
            sa.text(
                "INSERT INTO run_identity (id, kind, legacy_id) "
                "VALUES (:id, :kind, :legacy_id)"
            ),
            {"id": legacy_id, "kind": kind, "legacy_id": legacy_id},
        )
        return legacy_id

    result = bind.execute(
        sa.text(
            "INSERT INTO run_identity (kind, legacy_id) VALUES (:kind, :legacy_id)"
        ),
        {"kind": kind, "legacy_id": legacy_id},
    )
    return int(result.lastrowid)


def _backfill_parent_ids() -> dict[tuple[str, int], int]:
    """Create identities and change each type-specific parent id in place."""
    mapping: dict[tuple[str, int], int] = {}
    bind = _bind()
    for kind, table in PARENT_TABLES.items():
        if table not in _tables():
            continue
        for old_id in _fetch_ids(table):
            new_id = _insert_identity(kind, old_id)
            mapping[(kind, old_id)] = new_id
            if new_id != old_id:
                bind.execute(
                    sa.text(
                        f"UPDATE {_quote(table)} SET id = :new_id WHERE id = :old_id"
                    ),
                    {"new_id": new_id, "old_id": old_id},
                )
    return mapping


def _delete_by_ids(table: str, ids: Iterable[int]) -> None:
    ids = list(ids)
    if not ids:
        return
    _bind().execute(
        sa.text(f"DELETE FROM {_quote(table)} WHERE id IN :ids").bindparams(
            sa.bindparam("ids", expanding=True)
        ),
        {"ids": ids},
    )


def _update_web_only(
    table: str, column: str, mapping: dict[tuple[str, int], int]
) -> None:
    if table not in _tables() or column not in _columns(table):
        return
    bind = _bind()
    rows = bind.execute(
        sa.text(f"SELECT id, {_quote(column)} FROM {_quote(table)}")
    ).all()
    delete_ids: list[int] = []
    for row_id, old_run_id in rows:
        if old_run_id is None or ("web", int(old_run_id)) not in mapping:
            delete_ids.append(int(row_id))
            continue
        bind.execute(
            sa.text(
                f"UPDATE {_quote(table)} SET {_quote(column)} = :new_id WHERE id = :row_id"
            ),
            {"new_id": mapping[("web", int(old_run_id))], "row_id": row_id},
        )
    _delete_by_ids(table, delete_ids)


def _resolve_shared_kind(
    marker: str | None,
    old_run_id: int | None,
    mapping: dict[tuple[str, int], int],
) -> str | None:
    if old_run_id is None:
        return None
    old_run_id = int(old_run_id)
    available = [kind for kind in PARENT_TABLES if (kind, old_run_id) in mapping]
    if not available:
        return None
    marker = marker if marker in PARENT_TABLES else None
    # Historical rows defaulted to web.  If only an API/SAST parent exists,
    # infer that owner; when both exist, the default marker is ambiguous.
    if marker == "web" and len(available) > 1:
        return None
    if marker in available:
        return marker
    return available[0] if len(available) == 1 else None


def _update_shared(
    table: str,
    column: str,
    mapping: dict[tuple[str, int], int],
) -> None:
    if table not in _tables() or {column, "run_kind", "id"} - _columns(table):
        return
    bind = _bind()
    rows = bind.execute(
        sa.text(f"SELECT id, run_kind, {_quote(column)} FROM {_quote(table)}")
    ).all()
    delete_ids: list[int] = []
    for row_id, marker, old_run_id in rows:
        kind = _resolve_shared_kind(marker, old_run_id, mapping)
        if kind is None:
            delete_ids.append(int(row_id))
            continue
        bind.execute(
            sa.text(
                f"UPDATE {_quote(table)} SET {_quote(column)} = :new_id, "
                "run_kind = :kind WHERE id = :row_id"
            ),
            {
                "new_id": mapping[(kind, int(old_run_id))],
                "kind": kind,
                "row_id": row_id,
            },
        )
    _delete_by_ids(table, delete_ids)


def _update_dual_attribution(
    table: str,
    mapping: dict[tuple[str, int], int],
) -> None:
    if table not in _tables():
        return
    columns = _columns(table)
    if {"id", "test_run_id", "api_test_run_id"} - columns:
        return
    bind = _bind()
    rows = bind.execute(
        sa.text(f"SELECT id, test_run_id, api_test_run_id FROM {_quote(table)}")
    ).all()
    delete_ids: list[int] = []
    for row_id, old_web_id, old_api_id in rows:
        if old_api_id is not None:
            key = ("api", int(old_api_id))
            if key not in mapping:
                delete_ids.append(int(row_id))
                continue
            # The dedicated API owner is authoritative; clear old sentinel or
            # colliding values in the shared web column.
            bind.execute(
                sa.text(
                    f"UPDATE {_quote(table)} SET test_run_id = :web_id, "
                    "api_test_run_id = :new_id WHERE id = :row_id"
                ),
                {
                    "web_id": 0 if table == "traffic_entry" else None,
                    "new_id": mapping[key],
                    "row_id": row_id,
                },
            )
            continue
        if old_web_id is None:
            delete_ids.append(int(row_id))
            continue
        key = ("web", int(old_web_id))
        # A web-only row whose old id was shared by another run kind cannot be
        # assigned safely.  Drop it according to the migration policy above.
        if (
            key not in mapping
            or sum((kind, int(old_web_id)) in mapping for kind in PARENT_TABLES) > 1
        ):
            delete_ids.append(int(row_id))
            continue
        bind.execute(
            sa.text(
                f"UPDATE {_quote(table)} SET test_run_id = :new_id WHERE id = :row_id"
            ),
            {"new_id": mapping[key], "row_id": row_id},
        )
    _delete_by_ids(table, delete_ids)


def _remap_soft_links(mapping: dict[tuple[str, int], int]) -> None:
    bind = _bind()
    if "api_test_run" in _tables() and "sast_run_id" in _columns("api_test_run"):
        bind.execute(
            sa.text(
                "UPDATE api_test_run SET sast_run_id = NULL "
                "WHERE sast_run_id IS NOT NULL AND sast_run_id NOT IN "
                "(SELECT legacy_id FROM run_identity WHERE kind = 'sast')"
            )
        )
        for old_id, new_id in (
            (old, new) for (kind, old), new in mapping.items() if kind == "sast"
        ):
            bind.execute(
                sa.text(
                    "UPDATE api_test_run SET sast_run_id = :new_id "
                    "WHERE sast_run_id = :old_id"
                ),
                {"new_id": new_id, "old_id": old_id},
            )

    if "sast_run" in _tables():
        columns = _columns("sast_run")
        if {"triggered_by_run_type", "triggered_by_run_id"} <= columns:
            rows = bind.execute(
                sa.text(
                    "SELECT id, triggered_by_run_type, triggered_by_run_id FROM sast_run"
                )
            ).all()
            for row_id, kind, old_id in rows:
                key = (kind, int(old_id)) if kind and old_id is not None else None
                if key not in mapping:
                    bind.execute(
                        sa.text(
                            "UPDATE sast_run SET triggered_by_run_type = NULL, "
                            "triggered_by_run_id = NULL WHERE id = :id"
                        ),
                        {"id": row_id},
                    )
                else:
                    bind.execute(
                        sa.text(
                            "UPDATE sast_run SET triggered_by_run_id = :new_id "
                            "WHERE id = :id"
                        ),
                        {"new_id": mapping[key], "id": row_id},
                    )

    if "scan_lead" not in _tables():
        return
    columns = _columns("scan_lead")
    if {"producer_run_type", "producer_run_id"} <= columns:
        rows = bind.execute(
            sa.text(
                "SELECT id, producer_run_type, producer_run_id, "
                "investigated_by_run_type, investigated_by_run_id, "
                "imported_into_run_type, imported_into_run_id FROM scan_lead"
            )
        ).all()
        delete_ids: list[int] = []
        for (
            row_id,
            producer_kind,
            producer_old_id,
            investigated_kind,
            investigated_old_id,
            imported_kind,
            imported_old_id,
        ) in rows:
            producer_key = (
                (producer_kind, int(producer_old_id))
                if producer_kind and producer_old_id is not None
                else None
            )
            if producer_key not in mapping:
                delete_ids.append(int(row_id))
                continue
            updates: dict[str, Any] = {
                "producer_run_id": mapping[producer_key],
            }
            for kind_col, id_col, kind, old_id in (
                (
                    "investigated_by_run_type",
                    "investigated_by_run_id",
                    investigated_kind,
                    investigated_old_id,
                ),
                (
                    "imported_into_run_type",
                    "imported_into_run_id",
                    imported_kind,
                    imported_old_id,
                ),
            ):
                if old_id is None:
                    continue
                key = (kind, int(old_id)) if kind else None
                if key in mapping:
                    updates[id_col] = mapping[key]
                else:
                    updates[kind_col] = None
                    updates[id_col] = None
            assignments = ", ".join(f"{_quote(key)} = :{key}" for key in updates)
            updates["id"] = row_id
            bind.execute(
                sa.text(f"UPDATE scan_lead SET {assignments} WHERE id = :id"),
                updates,
            )
        _delete_by_ids("scan_lead", delete_ids)


def _add_missing_owner_columns() -> None:
    """Bring very old traffic/finding tables up to the dual-owner shape."""
    bind = _bind()
    for table in ("traffic_entry", "scan_finding"):
        if table in _tables() and "api_test_run_id" not in _columns(table):
            bind.execute(
                sa.text(
                    f"ALTER TABLE {_quote(table)} ADD COLUMN api_test_run_id INTEGER"
                )
            )


def _rebuild_with_run_fks(table: str, run_columns: dict[str, bool]) -> None:
    """Rebuild a SQLite table, replacing only its run-id foreign keys."""
    if table not in _tables():
        return
    existing = _columns(table)
    run_columns = {
        name: nullable for name, nullable in run_columns.items() if name in existing
    }
    if not run_columns:
        return

    bind = _bind()
    metadata = sa.MetaData()
    old = sa.Table(table, metadata, autoload_with=bind)
    index_specs = [
        (index.name, [column.name for column in index.columns], index.unique)
        for index in old.indexes
        if index.name
    ]
    temp_name = f"_run_identity_{table}"
    if temp_name in _tables():
        bind.execute(sa.text(f"DROP TABLE {_quote(temp_name)}"))

    new_metadata = sa.MetaData()
    # ForeignKey resolution happens against this in-memory metadata when the
    # temporary table is compiled; the real table was created above.
    sa.Table(
        "run_identity",
        new_metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
    )
    new_columns = []
    for column in old.columns:
        if column.name in run_columns:
            new_columns.append(
                sa.Column(
                    column.name,
                    column.type,
                    sa.ForeignKey(
                        "run_identity.id",
                        ondelete="CASCADE",
                    ),
                    nullable=run_columns[column.name],
                    primary_key=column.primary_key,
                    autoincrement=column.autoincrement,
                    server_default=column.server_default,
                )
            )
        else:
            new_columns.append(column.copy())

    new = sa.Table(
        temp_name,
        new_metadata,
        *new_columns,
        sqlite_autoincrement=table in PARENT_TABLES.values(),
    )
    for constraint in old.constraints:
        if isinstance(constraint, sa.PrimaryKeyConstraint | sa.ForeignKeyConstraint):
            continue
        if isinstance(constraint, sa.UniqueConstraint):
            sa.UniqueConstraint(
                *(new.c[column.name] for column in constraint.columns),
                name=constraint.name,
                table=new,
            )
        elif isinstance(constraint, sa.CheckConstraint):
            sa.CheckConstraint(str(constraint.sqltext), name=constraint.name, table=new)

    new.create(bind)
    column_names = [column.name for column in old.columns]
    quoted_columns = ", ".join(_quote(name) for name in column_names)
    bind.execute(
        sa.text(
            f"INSERT INTO {_quote(temp_name)} ({quoted_columns}) "
            f"SELECT {quoted_columns} FROM {_quote(table)}"
        )
    )
    bind.execute(sa.text(f"DROP TABLE {_quote(table)}"))
    bind.execute(sa.text(f"ALTER TABLE {_quote(temp_name)} RENAME TO {_quote(table)}"))

    final = sa.Table(table, sa.MetaData(), autoload_with=bind)
    for name, columns, unique in index_specs:
        if name not in {
            row[0]
            for row in bind.execute(
                sa.text(
                    "SELECT name FROM sqlite_master WHERE type = 'index' AND name IS NOT NULL"
                )
            )
        }:
            sa.Index(
                name, *(final.c[column] for column in columns), unique=unique
            ).create(bind)


def upgrade() -> None:
    bind = _bind()
    tables = _tables()
    if "run_identity" in tables:
        # This also makes the revision safe for a database created by the new
        # metadata before it received an Alembic version stamp.
        return

    bind.execute(sa.text("PRAGMA foreign_keys = OFF"))
    op.create_table(
        "run_identity",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("legacy_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sqlite_autoincrement=True,
    )
    op.create_index("ix_run_identity_kind", "run_identity", ["kind"])
    op.create_index("ix_run_identity_legacy_id", "run_identity", ["legacy_id"])

    _add_missing_owner_columns()
    mapping = _backfill_parent_ids()

    # Dedicated owner columns are authoritative.  Ambiguous web-only rows in
    # a reused legacy id are deleted; unambiguous rows are remapped.
    _update_dual_attribution("scan_finding", mapping)
    _update_dual_attribution("traffic_entry", mapping)
    if "api_endpoint_test" in _tables():
        rows = bind.execute(
            sa.text("SELECT id, api_test_run_id FROM api_endpoint_test")
        ).all()
        for row_id, old_id in rows:
            key = ("api", int(old_id)) if old_id is not None else None
            if key in mapping:
                bind.execute(
                    sa.text(
                        "UPDATE api_endpoint_test SET api_test_run_id = :new_id WHERE id = :id"
                    ),
                    {"new_id": mapping[key], "id": row_id},
                )
            else:
                bind.execute(
                    sa.text("DELETE FROM api_endpoint_test WHERE id = :id"),
                    {"id": row_id},
                )

    for table, columns in WEB_RUN_COLUMNS.items():
        _update_web_only(table, columns[0], mapping)
    for table, columns in SHARED_RUN_COLUMNS.items():
        _update_shared(table, columns[0], mapping)
    _remap_soft_links(mapping)

    for table, columns in RUN_FK_COLUMNS.items():
        _rebuild_with_run_fks(table, columns)

    for table in ("traffic_entry", "scan_finding"):
        if table in _tables() and "api_test_run_id" in _columns(table):
            bind.execute(
                sa.text(
                    f"CREATE INDEX IF NOT EXISTS ix_{table}_api_test_run_id "
                    f"ON {_quote(table)} (api_test_run_id)"
                )
            )

    if "traffic_entry" in _tables() and {
        "test_run_id",
        "api_test_run_id",
    } <= _columns("traffic_entry"):
        # The pre-migration column was NOT NULL because API traffic used the
        # sentinel 0.  It is nullable after the table rebuild.
        bind.execute(
            sa.text(
                "UPDATE traffic_entry SET test_run_id = NULL "
                "WHERE api_test_run_id IS NOT NULL"
            )
        )


def downgrade() -> None:
    # A downgrade would reintroduce an ambiguous id namespace and cannot
    # safely reconstruct the old ownership.  Keep the global identity schema.
    pass
