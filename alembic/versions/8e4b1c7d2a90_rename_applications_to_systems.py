"""rename applications to systems

Revision ID: 8e4b1c7d2a90
Revises: 3b5d7f9a1c24
Create Date: 2026-09-12
"""

from typing import Sequence, Union

from alembic import op

revision: str = "8e4b1c7d2a90"
down_revision: Union[str, None] = "3b5d7f9a1c24"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _rename_indexes(old_to_new: tuple[tuple[str, str, str, tuple[str, ...], bool], ...]) -> None:
    for table, old_name, new_name, columns, unique in old_to_new:
        op.drop_index(old_name, table_name=table)
        op.create_index(new_name, table, list(columns), unique=unique)


def upgrade() -> None:
    op.rename_table("application", "system")
    op.rename_table("application_component", "system_component")
    op.rename_table("application_target", "system_target")

    op.alter_column("system_component", "application_id", new_column_name="system_id")
    op.alter_column("system_target", "application_id", new_column_name="system_id")
    op.alter_column("component_target_hint", "application_id", new_column_name="system_id")
    op.alter_column("assessment_campaign", "application_id", new_column_name="system_id")

    _rename_indexes(
        (
            ("system", "ix_application_name", "ix_system_name", ("name",), True),
            (
                "system_component",
                "ix_application_component_application_id",
                "ix_system_component_system_id",
                ("system_id",),
                False,
            ),
            (
                "system_target",
                "ix_application_target_application_id",
                "ix_system_target_system_id",
                ("system_id",),
                False,
            ),
            (
                "system_target",
                "ix_application_target_target_id",
                "ix_system_target_target_id",
                ("target_id",),
                False,
            ),
            (
                "system_target",
                "ix_application_target_target_type",
                "ix_system_target_target_type",
                ("target_type",),
                False,
            ),
            (
                "system_target",
                "ix_application_target_component_id",
                "ix_system_target_component_id",
                ("component_id",),
                False,
            ),
            (
                "component_target_hint",
                "ix_component_target_hint_application_id",
                "ix_component_target_hint_system_id",
                ("system_id",),
                False,
            ),
            (
                "assessment_campaign",
                "ix_assessment_campaign_application_id",
                "ix_assessment_campaign_system_id",
                ("system_id",),
                False,
            ),
        )
    )


def downgrade() -> None:
    _rename_indexes(
        (
            ("system", "ix_system_name", "ix_application_name", ("name",), True),
            (
                "system_component",
                "ix_system_component_system_id",
                "ix_application_component_application_id",
                ("system_id",),
                False,
            ),
            (
                "system_target",
                "ix_system_target_system_id",
                "ix_application_target_application_id",
                ("system_id",),
                False,
            ),
            (
                "system_target",
                "ix_system_target_target_id",
                "ix_application_target_target_id",
                ("target_id",),
                False,
            ),
            (
                "system_target",
                "ix_system_target_target_type",
                "ix_application_target_target_type",
                ("target_type",),
                False,
            ),
            (
                "system_target",
                "ix_system_target_component_id",
                "ix_application_target_component_id",
                ("component_id",),
                False,
            ),
            (
                "component_target_hint",
                "ix_component_target_hint_system_id",
                "ix_component_target_hint_application_id",
                ("system_id",),
                False,
            ),
            (
                "assessment_campaign",
                "ix_assessment_campaign_system_id",
                "ix_assessment_campaign_application_id",
                ("system_id",),
                False,
            ),
        )
    )

    op.alter_column("assessment_campaign", "system_id", new_column_name="application_id")
    op.alter_column("component_target_hint", "system_id", new_column_name="application_id")
    op.alter_column("system_target", "system_id", new_column_name="application_id")
    op.alter_column("system_component", "system_id", new_column_name="application_id")

    op.rename_table("system_target", "application_target")
    op.rename_table("system_component", "application_component")
    op.rename_table("system", "application")
