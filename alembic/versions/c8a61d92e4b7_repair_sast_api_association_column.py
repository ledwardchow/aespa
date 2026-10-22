"""Add the API association column if an earlier SAST migration missed it.

Revision ID: c8a61d92e4b7
Revises: d22ae8ebc55f
"""

import sqlalchemy as sa

from alembic import op

revision = "c8a61d92e4b7"
down_revision = "d22ae8ebc55f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "sast_run" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("sast_run")}
    if "associated_collection_id" not in columns:
        op.execute(
            "ALTER TABLE sast_run ADD COLUMN associated_collection_id "
            "INTEGER REFERENCES api_collection(id)"
        )
    indexes = {index["name"] for index in inspector.get_indexes("sast_run")}
    if "ix_sast_run_associated_collection_id" not in indexes:
        op.create_index(
            "ix_sast_run_associated_collection_id",
            "sast_run",
            ["associated_collection_id"],
        )


def downgrade() -> None:
    # The preceding revision also defines this column, so keep it in place.
    pass
