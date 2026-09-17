"""separate upstream proxy URLs

Revision ID: 3e7a9c1d5f20
Revises: 8f0b3d5e7a92
Create Date: 2026-09-17

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel

from alembic import op

revision: str = "3e7a9c1d5f20"
down_revision: Union[str, None] = "8f0b3d5e7a92"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("upstream_proxy_config"):
        return

    columns = {item["name"] for item in inspector.get_columns("upstream_proxy_config")}
    with op.batch_alter_table("upstream_proxy_config", schema=None) as batch_op:
        if "scanner_proxy_url" not in columns:
            batch_op.add_column(
                sa.Column(
                    "scanner_proxy_url",
                    sqlmodel.sql.sqltypes.AutoString(),
                    nullable=True,
                )
            )
        if "llm_proxy_url" not in columns:
            batch_op.add_column(
                sa.Column(
                    "llm_proxy_url",
                    sqlmodel.sql.sqltypes.AutoString(),
                    nullable=True,
                )
            )

    if "proxy_url" in columns:
        op.execute(
            sa.text(
                "UPDATE upstream_proxy_config "
                "SET scanner_proxy_url = COALESCE(scanner_proxy_url, proxy_url), "
                "llm_proxy_url = COALESCE(llm_proxy_url, proxy_url)"
            )
        )
        with op.batch_alter_table("upstream_proxy_config", schema=None) as batch_op:
            batch_op.drop_column("proxy_url")


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("upstream_proxy_config"):
        return

    columns = {item["name"] for item in inspector.get_columns("upstream_proxy_config")}
    if "proxy_url" not in columns:
        with op.batch_alter_table("upstream_proxy_config", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "proxy_url",
                    sqlmodel.sql.sqltypes.AutoString(),
                    nullable=True,
                )
            )

    op.execute(
        sa.text(
            "UPDATE upstream_proxy_config "
            "SET proxy_url = COALESCE(scanner_proxy_url, llm_proxy_url)"
        )
    )
    with op.batch_alter_table("upstream_proxy_config", schema=None) as batch_op:
        if "llm_proxy_url" in columns:
            batch_op.drop_column("llm_proxy_url")
        if "scanner_proxy_url" in columns:
            batch_op.drop_column("scanner_proxy_url")
