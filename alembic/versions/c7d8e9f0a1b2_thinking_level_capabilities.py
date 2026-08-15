"""add model thinking level capability metadata"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "c7d8e9f0a1b2"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    provider_columns = {
        item["name"] for item in inspector.get_columns("llm_provider_config")
    }
    profile_columns = {item["name"] for item in inspector.get_columns("llm_config")}
    with op.batch_alter_table("llm_provider_config") as batch:
        if "model_capabilities_json" not in provider_columns:
            batch.add_column(
                sa.Column(
                    "model_capabilities_json",
                    sa.Text(),
                    nullable=False,
                    server_default="{}",
                )
            )
    with op.batch_alter_table("llm_config") as batch:
        if "reasoning_effort" not in profile_columns:
            batch.add_column(
                sa.Column("reasoning_effort", sa.String(length=32), nullable=True)
            )


def downgrade() -> None:
    with op.batch_alter_table("llm_config") as batch:
        batch.drop_column("reasoning_effort")
    with op.batch_alter_table("llm_provider_config") as batch:
        batch.drop_column("model_capabilities_json")
