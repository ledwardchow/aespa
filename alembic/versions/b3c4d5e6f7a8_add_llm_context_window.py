"""add per-model context window setting"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, None] = "e5b7c9d1f3a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "llm_config" not in inspector.get_table_names():
        return
    columns = {item["name"] for item in inspector.get_columns("llm_config")}
    missing = {"max_context_tokens", "context_limit_source"} - columns
    if missing:
        with op.batch_alter_table("llm_config") as batch:
            if "max_context_tokens" in missing:
                batch.add_column(sa.Column("max_context_tokens", sa.Integer(), nullable=False, server_default="200000"))
            if "context_limit_source" in missing:
                batch.add_column(sa.Column("context_limit_source", sa.String(length=32), nullable=False, server_default="fallback"))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "llm_config" not in inspector.get_table_names():
        return
    columns = {item["name"] for item in inspector.get_columns("llm_config")}
    if "context_limit_source" in columns or "max_context_tokens" in columns:
        with op.batch_alter_table("llm_config") as batch:
            if "context_limit_source" in columns:
                batch.drop_column("context_limit_source")
            if "max_context_tokens" in columns:
                batch.drop_column("max_context_tokens")
