"""Add CA bundle paths for LLM and scanner HTTP traffic.

Revision ID: 82f9567eec6a
Revises: a1d5e7f9b3c2
"""

import sqlalchemy as sa

from alembic import op

revision: str = "82f9567eec6a"
down_revision: str | None = "a1d5e7f9b3c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "upstream_proxy_config",
        sa.Column("scanner_ca_bundle_path", sa.String(), nullable=True),
    )
    op.add_column(
        "upstream_proxy_config",
        sa.Column("llm_ca_bundle_path", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("upstream_proxy_config", "llm_ca_bundle_path")
    op.drop_column("upstream_proxy_config", "scanner_ca_bundle_path")
