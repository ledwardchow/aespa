"""Associate SAST scans with Sites and API collections.

Revision ID: d22ae8ebc55f
Revises: 4a7c1e9d2b60
"""

import sqlalchemy as sa

from alembic import op

revision = "d22ae8ebc55f"
down_revision = "4a7c1e9d2b60"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "sast_run" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("sast_run")}
    # Both fields are nullable, so SQLite can add them with their foreign keys
    # in place. Rebuilding sast_run here can fail on older data with dangling
    # run identities and on some prior column orderings.
    if "site_id" not in columns:
        op.execute(
            "ALTER TABLE sast_run ADD COLUMN site_id INTEGER REFERENCES site(id)"
        )
    if "associated_collection_id" not in columns:
        op.execute(
            "ALTER TABLE sast_run ADD COLUMN associated_collection_id "
            "INTEGER REFERENCES api_collection(id)"
        )
    indexes = {index["name"] for index in inspector.get_indexes("sast_run")}
    if "ix_sast_run_site_id" not in indexes:
        op.create_index("ix_sast_run_site_id", "sast_run", ["site_id"])
    if "ix_sast_run_associated_collection_id" not in indexes:
        op.create_index(
            "ix_sast_run_associated_collection_id",
            "sast_run",
            ["associated_collection_id"],
        )
    op.execute(
        "UPDATE sast_run SET site_id = ("
        "SELECT site_id FROM test_run WHERE test_run.id = sast_run.triggered_by_run_id"
        ") WHERE triggered_by_run_type = 'web' AND collection_id IS NULL"
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "sast_run" not in inspector.get_table_names():
        return
    indexes = {index["name"] for index in inspector.get_indexes("sast_run")}
    for name in ("ix_sast_run_site_id", "ix_sast_run_associated_collection_id"):
        if name in indexes:
            op.drop_index(name, table_name="sast_run")
    columns = {column["name"] for column in inspector.get_columns("sast_run")}
    # A batch rebuild drops the original table. With foreign keys enabled,
    # SQLite cascades that drop into every saved SAST child table.
    if "site_id" in columns:
        op.drop_column("sast_run", "site_id")
    if "associated_collection_id" in columns:
        op.drop_column("sast_run", "associated_collection_id")
