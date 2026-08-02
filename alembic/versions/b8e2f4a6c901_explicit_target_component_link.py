"""add optional explicit component ownership to application targets

Revision ID: b8e2f4a6c901
Revises: cc7896879130
Create Date: 2026-08-02

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "b8e2f4a6c901"
down_revision: Union[str, None] = "cc7896879130"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        # SQLite cannot add a foreign-key constraint through Alembic's normal
        # add_column operation.  A batch rebuild also fails here because
        # component_target_hint has an inbound FK to application_target.
        op.execute(
            "ALTER TABLE application_target "
            "ADD COLUMN component_id INTEGER REFERENCES application_component(id)"
        )
        op.create_index(
            "ix_application_target_component_id",
            "application_target",
            ["component_id"],
            unique=False,
        )
        return

    with op.batch_alter_table("application_target", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "component_id",
                sa.Integer(),
                sa.ForeignKey("application_component.id"),
                nullable=True,
            )
        )
        batch_op.create_index(
            batch_op.f("ix_application_target_component_id"),
            ["component_id"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        op.drop_index("ix_application_target_component_id", table_name="application_target")
        op.execute("ALTER TABLE application_target DROP COLUMN component_id")
        return

    with op.batch_alter_table("application_target", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_application_target_component_id"))
        batch_op.drop_column("component_id")
