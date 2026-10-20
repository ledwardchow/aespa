"""Keep saved crawls on a site so later runs can skip crawling.

Revision ID: c3e7a9d1f5b2
Revises: 92b81e7007c6
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "c3e7a9d1f5b2"
down_revision: Union[str, Sequence[str], None] = "92b81e7007c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "saved_crawl" in tables:
        return
    op.create_table(
        "saved_crawl",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("source_run_id", sa.Integer(), nullable=True),
        sa.Column("crawler_mode", sa.String(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("archive_gz", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["site.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_saved_crawl_site_id", "saved_crawl", ["site_id"])


def downgrade() -> None:
    op.drop_index("ix_saved_crawl_site_id", table_name="saved_crawl")
    op.drop_table("saved_crawl")
