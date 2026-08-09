"""application validation resume metadata

Revision ID: f6a8c1d3e5b7
Revises: f4a6b8c0d2e1
Create Date: 2026-08-08 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel

from alembic import op

revision: str = "f6a8c1d3e5b7"
down_revision: Union[str, None] = "f4a6b8c0d2e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("page_link"):
        columns = {item["name"] for item in inspector.get_columns("page_link")}
        indexes = {item["name"] for item in inspector.get_indexes("page_link")}
        with op.batch_alter_table("page_link", schema=None) as batch_op:
            if "interaction_id" not in columns:
                batch_op.add_column(
                    sa.Column(
                        "interaction_id",
                        sqlmodel.sql.sqltypes.AutoString(),
                        nullable=True,
                    )
                )
            if "ix_page_link_interaction_id" not in indexes:
                batch_op.create_index("ix_page_link_interaction_id", ["interaction_id"])

    if inspector.has_table("traffic_entry"):
        columns = {item["name"] for item in inspector.get_columns("traffic_entry")}
        indexes = {item["name"] for item in inspector.get_indexes("traffic_entry")}
        with op.batch_alter_table("traffic_entry", schema=None) as batch_op:
            if "interaction_id" not in columns:
                batch_op.add_column(
                    sa.Column(
                        "interaction_id",
                        sqlmodel.sql.sqltypes.AutoString(),
                        nullable=True,
                    )
                )
            if "ix_traffic_entry_interaction_id" not in indexes:
                batch_op.create_index(
                    "ix_traffic_entry_interaction_id", ["interaction_id"]
                )

    if inspector.has_table("campaign_target_member"):
        columns = {
            item["name"] for item in inspector.get_columns("campaign_target_member")
        }
        with op.batch_alter_table("campaign_target_member", schema=None) as batch_op:
            if "status_message" not in columns:
                batch_op.add_column(
                    sa.Column(
                        "status_message",
                        sqlmodel.sql.sqltypes.AutoString(),
                        nullable=True,
                    )
                )
            if "validation_summary_json" not in columns:
                batch_op.add_column(
                    sa.Column(
                        "validation_summary_json",
                        sqlmodel.sql.sqltypes.AutoString(),
                        nullable=False,
                        server_default=sa.text("'{}'"),
                    )
                )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("campaign_target_member"):
        columns = {
            item["name"] for item in inspector.get_columns("campaign_target_member")
        }
        with op.batch_alter_table("campaign_target_member", schema=None) as batch_op:
            if "validation_summary_json" in columns:
                batch_op.drop_column("validation_summary_json")
            if "status_message" in columns:
                batch_op.drop_column("status_message")

    if inspector.has_table("traffic_entry"):
        columns = {item["name"] for item in inspector.get_columns("traffic_entry")}
        indexes = {item["name"] for item in inspector.get_indexes("traffic_entry")}
        with op.batch_alter_table("traffic_entry", schema=None) as batch_op:
            if "ix_traffic_entry_interaction_id" in indexes:
                batch_op.drop_index("ix_traffic_entry_interaction_id")
            if "interaction_id" in columns:
                batch_op.drop_column("interaction_id")

    if inspector.has_table("page_link"):
        columns = {item["name"] for item in inspector.get_columns("page_link")}
        indexes = {item["name"] for item in inspector.get_indexes("page_link")}
        with op.batch_alter_table("page_link", schema=None) as batch_op:
            if "ix_page_link_interaction_id" in indexes:
                batch_op.drop_index("ix_page_link_interaction_id")
            if "interaction_id" in columns:
                batch_op.drop_column("interaction_id")
