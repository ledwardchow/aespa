"""Drop the SAST minimum confidence reporting setting.

Revision ID: 47c7f6cf424a
Revises: e3c5a7b9d1f2
Create Date: 2026-09-29
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "47c7f6cf424a"
down_revision: Union[str, Sequence[str], None] = "e3c5a7b9d1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("scanner_policy")
    }
    if "sast_min_confidence" in columns:
        with op.batch_alter_table("scanner_policy") as batch:
            batch.drop_column("sast_min_confidence")


def downgrade() -> None:
    with op.batch_alter_table("scanner_policy") as batch:
        batch.add_column(
            sa.Column(
                "sast_min_confidence",
                sa.Float(),
                nullable=False,
                server_default="0.35",
            )
        )
