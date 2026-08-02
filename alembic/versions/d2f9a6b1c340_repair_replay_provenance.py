"""repair replay provenance skipped by existing migration histories

Revision ID: d2f9a6b1c340
Revises: c4e8b7a2d901
Create Date: 2026-08-01

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "d2f9a6b1c340"
down_revision: Union[str, None] = "c4e8b7a2d901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def _indexes(table: str) -> set[str]:
    return {
        index["name"]
        for index in sa.inspect(op.get_bind()).get_indexes(table)
        if index.get("name")
    }


def _has_foreign_key(table: str, columns: list[str], referred_table: str) -> bool:
    return any(
        foreign_key.get("constrained_columns") == columns
        and foreign_key.get("referred_table") == referred_table
        for foreign_key in sa.inspect(op.get_bind()).get_foreign_keys(table)
    )


def upgrade() -> None:
    test_run_columns = _columns("test_run")
    if {
        "target_page_ids_json",
        "target_session_label",
    } - test_run_columns:
        with op.batch_alter_table("test_run") as batch:
            if "target_page_ids_json" not in test_run_columns:
                batch.add_column(sa.Column("target_page_ids_json", sa.Text()))
            if "target_session_label" not in test_run_columns:
                batch.add_column(sa.Column("target_session_label", sa.String()))

    crawled_columns = _columns("crawled_page")
    crawled_indexes = _indexes("crawled_page")
    crawled_fk = _has_foreign_key(
        "crawled_page", ["replay_credential_id"], "credential"
    )
    if (
        "replay_credential_id" not in crawled_columns
        or "ix_crawled_page_replay_credential_id" not in crawled_indexes
        or not crawled_fk
    ):
        with op.batch_alter_table("crawled_page") as batch:
            if "replay_credential_id" not in crawled_columns:
                batch.add_column(sa.Column("replay_credential_id", sa.Integer()))
            if "ix_crawled_page_replay_credential_id" not in crawled_indexes:
                batch.create_index(
                    "ix_crawled_page_replay_credential_id",
                    ["replay_credential_id"],
                )
            if not crawled_fk:
                batch.create_foreign_key(
                    "fk_crawled_page_replay_credential_id_credential",
                    "credential",
                    ["replay_credential_id"],
                    ["id"],
                )

    traffic_columns = _columns("traffic_entry")
    traffic_indexes = _indexes("traffic_entry")
    traffic_fk = _has_foreign_key("traffic_entry", ["page_id"], "crawled_page")
    if (
        {"page_id", "session_label"} - traffic_columns
        or {
            "ix_traffic_entry_page_id",
            "ix_traffic_entry_session_label",
        }
        - traffic_indexes
        or not traffic_fk
    ):
        with op.batch_alter_table("traffic_entry") as batch:
            if "page_id" not in traffic_columns:
                batch.add_column(sa.Column("page_id", sa.Integer()))
            if "session_label" not in traffic_columns:
                batch.add_column(sa.Column("session_label", sa.String()))
            if "ix_traffic_entry_page_id" not in traffic_indexes:
                batch.create_index("ix_traffic_entry_page_id", ["page_id"])
            if "ix_traffic_entry_session_label" not in traffic_indexes:
                batch.create_index("ix_traffic_entry_session_label", ["session_label"])
            if not traffic_fk:
                batch.create_foreign_key(
                    "fk_traffic_entry_page_id_crawled_page",
                    "crawled_page",
                    ["page_id"],
                    ["id"],
                )

    intel_columns = _columns("target_intel_item")
    intel_indexes = _indexes("target_intel_item")
    intel_fk = _has_foreign_key("target_intel_item", ["page_id"], "crawled_page")
    if (
        "page_id" not in intel_columns
        or "ix_target_intel_item_page_id" not in intel_indexes
        or not intel_fk
    ):
        with op.batch_alter_table("target_intel_item") as batch:
            if "page_id" not in intel_columns:
                batch.add_column(sa.Column("page_id", sa.Integer()))
            if "ix_target_intel_item_page_id" not in intel_indexes:
                batch.create_index("ix_target_intel_item_page_id", ["page_id"])
            if not intel_fk:
                batch.create_foreign_key(
                    "fk_target_intel_item_page_id_crawled_page",
                    "crawled_page",
                    ["page_id"],
                    ["id"],
                )


def downgrade() -> None:
    # This revision repairs fields whose canonical introduction is the earlier
    # 1f4e7a2c9b10 revision. Downgrading only this repair must not remove them.
    pass
