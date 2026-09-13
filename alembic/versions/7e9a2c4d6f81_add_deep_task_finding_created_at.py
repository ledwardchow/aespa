"""add the missing Deep task finding timestamp

Revision ID: 7e9a2c4d6f81
Revises: 6d8f1a2b3c40
Create Date: 2026-09-13
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "7e9a2c4d6f81"
down_revision: Union[str, None] = "6d8f1a2b3c40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(name: str) -> bool:
    columns = sa.inspect(op.get_bind()).get_columns("deep_scan_task_finding")
    return any(column["name"] == name for column in columns)


def upgrade() -> None:
    if _has_column("created_at"):
        return

    # Avoid rebuilding this legacy SQLite table. Some older databases contain
    # foreign-key declarations whose target tables were not present at the time.
    op.add_column(
        "deep_scan_task_finding",
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE deep_scan_task_finding "
            "SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"
        )
    )


def downgrade() -> None:
    if _has_column("created_at"):
        op.drop_column("deep_scan_task_finding", "created_at")
