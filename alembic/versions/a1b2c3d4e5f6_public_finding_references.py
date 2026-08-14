"""add public finding and lead references

Revision ID: a1b2c3d4e5f6
Revises: f6a8c1d3e5b7
Create Date: 2026-08-08 00:00:00.000000
"""

from __future__ import annotations

import secrets
import string
from collections import defaultdict
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f6a8c1d3e5b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _prefix(used: set[str]) -> str:
    while True:
        value = "".join(secrets.choice(string.ascii_uppercase) for _ in range(4))
        if value not in used:
            used.add(value)
            return value


def _reference(prefix: str, number: int) -> str:
    return f"{prefix}-{number:03d}"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "public_reference_namespace" not in tables:
        op.create_table(
            "public_reference_namespace",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("owner_type", sa.String(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=False),
            sa.Column("prefix", sa.String(length=4), nullable=False),
            sa.Column("next_number", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("owner_type", "owner_id", name="uq_public_ref_owner"),
            sa.UniqueConstraint("prefix", name="uq_public_ref_prefix"),
        )
        op.create_index(
            "ix_public_reference_namespace_owner_type",
            "public_reference_namespace",
            ["owner_type"],
        )
        op.create_index(
            "ix_public_reference_namespace_owner_id",
            "public_reference_namespace",
            ["owner_id"],
        )
        op.create_index(
            "ix_public_reference_namespace_prefix",
            "public_reference_namespace",
            ["prefix"],
        )

    for table, columns in {
        "scan_finding": (
            ("public_reference", sa.String(), True),
            ("origin_type", sa.String(), True),
            ("origin_run_type", sa.String(), True),
            ("origin_run_id", sa.Integer(), True),
            ("origin_lead_id", sa.Integer(), True),
            ("origin_reference", sa.String(), True),
        ),
        "scan_lead": (
            ("public_reference", sa.String(), True),
            ("origin_reference", sa.String(), True),
        ),
    }.items():
        if table not in tables:
            continue
        existing = {column["name"] for column in inspector.get_columns(table)}
        with op.batch_alter_table(table, schema=None) as batch_op:
            for name, type_, nullable in columns:
                if name not in existing:
                    batch_op.add_column(sa.Column(name, type_, nullable=nullable))
        indexes = {item["name"] for item in inspector.get_indexes(table)}
        for name, _, _ in columns:
            index_name = f"ix_{table}_{name}"
            if name not in existing and index_name not in indexes:
                op.create_index(index_name, table, [name])

    if "campaign_finding_reference" not in tables:
        op.create_table(
            "campaign_finding_reference",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "campaign_id",
                sa.Integer(),
                sa.ForeignKey("run_identity.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "finding_id",
                sa.Integer(),
                sa.ForeignKey("scan_finding.id"),
                nullable=False,
            ),
            sa.Column(
                "target_member_id",
                sa.Integer(),
                sa.ForeignKey("campaign_target_member.id"),
                nullable=False,
            ),
            sa.Column("public_reference", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint(
                "campaign_id", "finding_id", name="uq_campaign_finding_reference"
            ),
            sa.UniqueConstraint(
                "campaign_id", "public_reference", name="uq_campaign_public_reference"
            ),
        )
        op.create_index(
            "ix_campaign_finding_reference_finding_id",
            "campaign_finding_reference",
            ["finding_id"],
        )
        op.create_index(
            "ix_campaign_finding_reference_target_member_id",
            "campaign_finding_reference",
            ["target_member_id"],
        )
        op.create_index(
            "ix_campaign_finding_reference_public_reference",
            "campaign_finding_reference",
            ["public_reference"],
        )

    used = {
        row[0]
        for row in bind.execute(
            sa.text("SELECT prefix FROM public_reference_namespace")
        )
    }
    next_numbers: dict[tuple[str, int], int] = defaultdict(lambda: 1)

    run_sources = (
        ("web", "test_run"),
        ("api", "api_test_run"),
        ("sast", "sast_run"),
        ("campaign", "assessment_campaign"),
    )
    for owner_type, table in run_sources:
        if table not in tables:
            continue
        for row in bind.execute(sa.text(f"SELECT id FROM {table}")):
            owner_id = int(row[0])
            prefix = _prefix(used)
            bind.execute(
                sa.text(
                    "INSERT INTO public_reference_namespace "
                    "(owner_type, owner_id, prefix, next_number, created_at) "
                    "VALUES (:owner_type, :owner_id, :prefix, 1, CURRENT_TIMESTAMP)"
                ),
                {
                    "owner_type": owner_type,
                    "owner_id": owner_id,
                    "prefix": prefix,
                },
            )
            next_numbers[(owner_type, owner_id)] = 1

    def namespace(owner_type: str, owner_id: int) -> tuple[str, int]:
        key = (owner_type, owner_id)
        if key not in next_numbers:
            prefix = _prefix(used)
            bind.execute(
                sa.text(
                    "INSERT INTO public_reference_namespace "
                    "(owner_type, owner_id, prefix, next_number, created_at) "
                    "VALUES (:owner_type, :owner_id, :prefix, 1, CURRENT_TIMESTAMP)"
                ),
                {"owner_type": owner_type, "owner_id": owner_id, "prefix": prefix},
            )
            next_numbers[key] = 1
        row = bind.execute(
            sa.text(
                "SELECT prefix FROM public_reference_namespace "
                "WHERE owner_type=:owner_type AND owner_id=:owner_id"
            ),
            {"owner_type": owner_type, "owner_id": owner_id},
        ).one()
        number = next_numbers[key]
        next_numbers[key] += 1
        bind.execute(
            sa.text(
                "UPDATE public_reference_namespace SET next_number=:next_number "
                "WHERE owner_type=:owner_type AND owner_id=:owner_id"
            ),
            {
                "next_number": next_numbers[key],
                "owner_type": owner_type,
                "owner_id": owner_id,
            },
        )
        return str(row[0]), number

    lead_rows = (
        bind.execute(
            sa.text(
                "SELECT id, producer_run_type, producer_run_id, imported_into_run_type, "
                "imported_into_run_id, origin_lead_id, public_reference, origin_reference "
                "FROM scan_lead ORDER BY id"
            )
        )
        .mappings()
        .all()
        if "scan_lead" in tables
        else []
    )
    for lead in lead_rows:
        if lead["public_reference"]:
            continue
        owner_type = lead["imported_into_run_type"] or lead["producer_run_type"]
        owner_id = lead["imported_into_run_id"] or lead["producer_run_id"]
        if not owner_type or owner_id is None:
            continue
        prefix, number = namespace(str(owner_type), int(owner_id))
        values = {"reference": _reference(prefix, number), "id": lead["id"]}
        original_id = lead["origin_lead_id"]
        original_reference = lead["origin_reference"]
        if owner_type in {"web", "api"} and not original_reference:
            original = bind.execute(
                sa.text(
                    "SELECT id, public_reference FROM scan_lead "
                    "WHERE imported_into_run_id IS NULL "
                    "AND producer_run_type=:producer_run_type "
                    "AND producer_run_id=:producer_run_id "
                    "AND fingerprint=(SELECT fingerprint FROM scan_lead WHERE id=:id) "
                    "ORDER BY id LIMIT 1"
                ),
                {
                    "producer_run_type": lead["producer_run_type"],
                    "producer_run_id": lead["producer_run_id"],
                    "id": lead["id"],
                },
            ).first()
            if original is not None:
                original_id = original[0]
                original_reference = original[1]
        bind.execute(
            sa.text(
                "UPDATE scan_lead SET public_reference=:reference, "
                "origin_lead_id=:origin_lead_id, origin_reference=:origin_reference "
                "WHERE id=:id"
            ),
            {
                **values,
                "origin_lead_id": original_id,
                "origin_reference": original_reference,
            },
        )

    finding_rows = (
        bind.execute(
            sa.text(
                "SELECT id, test_run_id, api_test_run_id, public_reference "
                "FROM scan_finding ORDER BY id"
            )
        )
        .mappings()
        .all()
        if "scan_finding" in tables
        else []
    )
    for finding in finding_rows:
        if finding["public_reference"]:
            continue
        linked = (
            bind.execute(
                sa.text(
                    "SELECT public_reference, producer_run_type, producer_run_id, "
                    "imported_into_run_type, imported_into_run_id, id, "
                    "origin_lead_id, origin_reference "
                    "FROM scan_lead WHERE linked_finding_id=:finding_id "
                    "ORDER BY imported_into_run_id IS NULL, id LIMIT 1"
                ),
                {"finding_id": finding["id"]},
            ).first()
            if "scan_lead" in tables
            else None
        )
        owner_type = "web" if finding["test_run_id"] is not None else "api"
        owner_id = finding["test_run_id"] or finding["api_test_run_id"]
        if owner_id is None:
            continue
        linked_owner = (
            (linked[3], linked[4])
            if linked is not None and linked[3] and linked[4] is not None
            else (linked[1], linked[2])
            if linked is not None
            else None
        )
        if linked is not None and linked[0] and linked_owner == (owner_type, owner_id):
            reference = linked[0]
            origin_type = linked[1]
            origin_run_id = linked[2]
            origin_lead_id = linked[6] or linked[5]
            origin_reference = linked[7]
        else:
            prefix, number = namespace(owner_type, int(owner_id))
            reference = _reference(prefix, number)
            origin_type = None
            origin_run_id = None
            origin_lead_id = None
            origin_reference = None
        bind.execute(
            sa.text(
                "UPDATE scan_finding SET public_reference=:reference, "
                "origin_type=:origin_type, origin_run_type=:origin_run_type, "
                "origin_run_id=:origin_run_id, origin_lead_id=:origin_lead_id, "
                "origin_reference=:origin_reference WHERE id=:id"
            ),
            {
                "reference": reference,
                "origin_type": origin_type,
                "origin_run_type": origin_type,
                "origin_run_id": origin_run_id,
                "origin_lead_id": origin_lead_id,
                "origin_reference": origin_reference,
                "id": finding["id"],
            },
        )

    if "campaign_target_member" in tables:
        targets = (
            bind.execute(
                sa.text(
                    "SELECT id, campaign_id, target_type, test_run_id, api_test_run_id "
                    "FROM campaign_target_member ORDER BY id"
                )
            )
            .mappings()
            .all()
        )
        for target in targets:
            run_id = target["test_run_id"] or target["api_test_run_id"]
            if run_id is None:
                continue
            owner_column = (
                "test_run_id"
                if target["test_run_id"] is not None
                else "api_test_run_id"
            )
            findings = bind.execute(
                sa.text(
                    f"SELECT id FROM scan_finding WHERE {owner_column}=:run_id "
                    "ORDER BY created_at, id"
                ),
                {"run_id": run_id},
            ).all()
            for finding in findings:
                existing = bind.execute(
                    sa.text(
                        "SELECT id FROM campaign_finding_reference "
                        "WHERE campaign_id=:campaign_id AND finding_id=:finding_id"
                    ),
                    {"campaign_id": target["campaign_id"], "finding_id": finding[0]},
                ).first()
                if existing is not None:
                    continue
                prefix, number = namespace("campaign", int(target["campaign_id"]))
                bind.execute(
                    sa.text(
                        "INSERT INTO campaign_finding_reference "
                        "(campaign_id, finding_id, target_member_id, public_reference, created_at) "
                        "VALUES (:campaign_id, :finding_id, :target_member_id, :reference, CURRENT_TIMESTAMP)"
                    ),
                    {
                        "campaign_id": target["campaign_id"],
                        "finding_id": finding[0],
                        "target_member_id": target["id"],
                        "reference": _reference(prefix, number),
                    },
                )


def downgrade() -> None:
    op.drop_table("campaign_finding_reference")
    for table, columns in {
        "scan_lead": ("origin_reference", "public_reference"),
        "scan_finding": (
            "origin_reference",
            "origin_lead_id",
            "origin_run_id",
            "origin_run_type",
            "origin_type",
            "public_reference",
        ),
    }.items():
        with op.batch_alter_table(table, schema=None) as batch_op:
            for column in columns:
                batch_op.drop_column(column)
    op.drop_table("public_reference_namespace")
