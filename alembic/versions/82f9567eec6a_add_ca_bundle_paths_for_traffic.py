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


_COLUMNS = ("scanner_ca_bundle_path", "llm_ca_bundle_path")


def _existing_columns() -> set[str] | None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("upstream_proxy_config"):
        return None
    return {item["name"] for item in inspector.get_columns("upstream_proxy_config")}


def upgrade() -> None:
    columns = _existing_columns()
    if columns is None:
        return
    for name in _COLUMNS:
        if name not in columns:
            op.add_column(
                "upstream_proxy_config", sa.Column(name, sa.String(), nullable=True)
            )


def downgrade() -> None:
    columns = _existing_columns()
    if columns is None:
        return
    for name in reversed(_COLUMNS):
        if name in columns:
            op.drop_column("upstream_proxy_config", name)
