"""Reference extension-owned LLM profiles from core scans.

Revision ID: 92b81e7007c6
Revises: b5d21b624019
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "92b81e7007c6"
down_revision: Union[str, Sequence[str], None] = "b5d21b624019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("llm_profile", sa.Column("extension_ref", sa.String(), nullable=True))
    op.create_index(
        "ix_llm_profile_extension_ref", "llm_profile", ["extension_ref"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_llm_profile_extension_ref", table_name="llm_profile")
    op.drop_column("llm_profile", "extension_ref")
