"""Save an AWS profile name on Bedrock providers and model configs.

Revision ID: b5d21b624019
Revises: 47c7f6cf424a
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "b5d21b624019"
down_revision: Union[str, Sequence[str], None] = "47c7f6cf424a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "llm_provider_config", sa.Column("aws_profile", sa.String(), nullable=True)
    )
    op.add_column("llm_config", sa.Column("aws_profile", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("llm_config", "aws_profile")
    op.drop_column("llm_provider_config", "aws_profile")
