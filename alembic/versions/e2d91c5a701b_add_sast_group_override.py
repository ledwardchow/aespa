"""Allow SAST scan grouping to differ from its source API collection.

Revision ID: e2d91c5a701b
Revises: c8a61d92e4b7
"""

import sqlalchemy as sa

from alembic import op

revision = "e2d91c5a701b"
down_revision = "c8a61d92e4b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "sast_run" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("sast_run")}
    if "group_override" not in columns:
        op.add_column(
            "sast_run",
            sa.Column(
                "group_override",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "sast_run" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("sast_run")}
    if "group_override" in columns:
        op.drop_column("sast_run", "group_override")
