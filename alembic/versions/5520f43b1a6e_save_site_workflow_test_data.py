"""Save site workflow test data.

Revision ID: 5520f43b1a6e
Revises: f1df15dddd52
Create Date: 2026-10-14
"""

import sqlalchemy as sa

from alembic import op

revision = "5520f43b1a6e"
down_revision = "f1df15dddd52"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "site",
        sa.Column(
            "workflow_data_json",
            sa.String(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("site", "workflow_data_json")
