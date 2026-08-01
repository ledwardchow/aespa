"""store interactive replay and request provenance

Revision ID: 1f4e7a2c9b10
Revises: 8c2a4f7d9b31
Create Date: 2026-07-31

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "1f4e7a2c9b10"
down_revision: Union[str, None] = "8c2a4f7d9b31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("test_run") as batch:
        batch.add_column(sa.Column("target_page_ids_json", sa.Text(), nullable=True))
        batch.add_column(sa.Column("target_session_label", sa.String(), nullable=True))
    with op.batch_alter_table("crawled_page") as batch:
        batch.add_column(sa.Column("replay_credential_id", sa.Integer(), nullable=True))
        batch.create_index(
            "ix_crawled_page_replay_credential_id",
            ["replay_credential_id"],
            unique=False,
        )
        batch.create_foreign_key(
            "fk_crawled_page_replay_credential_id_credential",
            "credential",
            ["replay_credential_id"],
            ["id"],
        )
    with op.batch_alter_table("traffic_entry") as batch:
        batch.add_column(sa.Column("page_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("session_label", sa.String(), nullable=True))
        batch.create_index("ix_traffic_entry_page_id", ["page_id"])
        batch.create_index("ix_traffic_entry_session_label", ["session_label"])
        batch.create_foreign_key(
            "fk_traffic_entry_page_id_crawled_page", "crawled_page", ["page_id"], ["id"]
        )
    with op.batch_alter_table("target_intel_item") as batch:
        batch.add_column(sa.Column("page_id", sa.Integer(), nullable=True))
        batch.create_index("ix_target_intel_item_page_id", ["page_id"])
        batch.create_foreign_key(
            "fk_target_intel_item_page_id_crawled_page",
            "crawled_page",
            ["page_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("test_run") as batch:
        batch.drop_column("target_session_label")
        batch.drop_column("target_page_ids_json")
    with op.batch_alter_table("target_intel_item") as batch:
        batch.drop_constraint(
            "fk_target_intel_item_page_id_crawled_page", type_="foreignkey"
        )
        batch.drop_index("ix_target_intel_item_page_id")
        batch.drop_column("page_id")
    with op.batch_alter_table("traffic_entry") as batch:
        batch.drop_constraint(
            "fk_traffic_entry_page_id_crawled_page", type_="foreignkey"
        )
        batch.drop_index("ix_traffic_entry_session_label")
        batch.drop_index("ix_traffic_entry_page_id")
        batch.drop_column("session_label")
        batch.drop_column("page_id")
    with op.batch_alter_table("crawled_page") as batch:
        batch.drop_constraint(
            "fk_crawled_page_replay_credential_id_credential", type_="foreignkey"
        )
        batch.drop_index("ix_crawled_page_replay_credential_id")
        batch.drop_column("replay_credential_id")
