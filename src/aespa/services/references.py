"""User-facing references for findings and static-analysis leads.

Database primary keys remain the internal identity used by existing APIs. This
module owns the stable references shown in reports, agent context, and links.
"""

from __future__ import annotations

import secrets
import string
from collections.abc import Iterable

from sqlmodel import Session, select

from aespa.models import (
    CampaignFindingReference,
    PublicReferenceNamespace,
    ScanFinding,
    ScanLead,
)

_ALPHABET = string.ascii_uppercase
_OWNER_TYPES = {"web", "api", "sast", "campaign"}


def _normalize_owner_type(owner_type: str) -> str:
    value = (owner_type or "").strip().lower()
    if value not in _OWNER_TYPES:
        raise ValueError(f"Unsupported public-reference owner type: {owner_type!r}")
    return value


def _new_prefix() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(4))


def ensure_namespace(
    session: Session, owner_type: str, owner_id: int
) -> PublicReferenceNamespace:
    """Return or create the namespace for one run/campaign."""

    owner_type = _normalize_owner_type(owner_type)
    existing = session.exec(
        select(PublicReferenceNamespace)
        .where(PublicReferenceNamespace.owner_type == owner_type)
        .where(PublicReferenceNamespace.owner_id == owner_id)
    ).first()
    if existing is not None:
        return existing

    # Prefix collisions are extraordinarily unlikely, but checking the table
    # before insertion keeps normal operation deterministic and the unique
    # constraint remains the final guard for concurrent writers.
    for _ in range(20):
        prefix = _new_prefix()
        used = session.exec(
            select(PublicReferenceNamespace.id).where(
                PublicReferenceNamespace.prefix == prefix
            )
        ).first()
        if used is not None:
            continue
        namespace = PublicReferenceNamespace(
            owner_type=owner_type,
            owner_id=owner_id,
            prefix=prefix,
        )
        session.add(namespace)
        session.flush()
        return namespace
    raise RuntimeError("Could not allocate a unique public-reference prefix")


def allocate_reference(session: Session, owner_type: str, owner_id: int) -> str:
    """Allocate the next never-reused reference in a run namespace."""

    namespace = ensure_namespace(session, owner_type, owner_id)
    number = namespace.next_number
    namespace.next_number += 1
    session.add(namespace)
    session.flush()
    return f"{namespace.prefix}-{number:03d}"


def finding_owner(finding: ScanFinding) -> tuple[str, int] | None:
    if finding.test_run_id is not None:
        return "web", finding.test_run_id
    if finding.api_test_run_id is not None:
        return "api", finding.api_test_run_id
    return None


def lead_owner(lead: ScanLead) -> tuple[str, int] | None:
    if lead.imported_into_run_type and lead.imported_into_run_id is not None:
        return lead.imported_into_run_type, lead.imported_into_run_id
    if lead.producer_run_type and lead.producer_run_id is not None:
        return lead.producer_run_type, lead.producer_run_id
    return None


def ensure_lead_reference(session: Session, lead: ScanLead) -> str:
    if lead.public_reference:
        return lead.public_reference
    owner = lead_owner(lead)
    if owner is None:
        raise ValueError(f"Lead {lead.id} has no reference owner")
    lead.public_reference = allocate_reference(session, *owner)
    session.add(lead)
    return lead.public_reference


def ensure_lead_references(
    session: Session, leads: Iterable[ScanLead]
) -> None:
    """Backfill a batch of leads with bounded database work.

    Read-heavy list endpoints often return many leads from one run. Allocate
    the run namespace once and then number the rows in memory so rendering a
    list does not turn into one namespace query per lead.
    """

    rows = list(leads)
    missing = [lead for lead in rows if not lead.public_reference]
    if not missing:
        return
    owners = {lead_owner(lead) for lead in missing}
    if None in owners:
        raise ValueError("A lead is missing its reference owner")
    owner_values = [(owner_type, owner_id) for owner_type, owner_id in owners if owner_type]
    owner_types = {owner_type for owner_type, _ in owner_values}
    owner_ids = {owner_id for _, owner_id in owner_values}
    namespaces = session.exec(
        select(PublicReferenceNamespace)
        .where(PublicReferenceNamespace.owner_type.in_(owner_types))
        .where(PublicReferenceNamespace.owner_id.in_(owner_ids))
    ).all()
    namespace_by_owner = {
        (namespace.owner_type, namespace.owner_id): namespace
        for namespace in namespaces
    }
    for owner_type, owner_id in owner_values:
        if (owner_type, owner_id) not in namespace_by_owner:
            namespace = PublicReferenceNamespace(
                owner_type=owner_type,
                owner_id=owner_id,
                prefix=_new_prefix(),
            )
            session.add(namespace)
            namespace_by_owner[(owner_type, owner_id)] = namespace
    session.flush()
    for lead in missing:
        owner = lead_owner(lead)
        namespace = namespace_by_owner[owner]
        number = namespace.next_number
        namespace.next_number += 1
        lead.public_reference = f"{namespace.prefix}-{number:03d}"
        session.add(lead)
    session.flush()


def ensure_finding_reference(session: Session, finding: ScanFinding) -> str:
    if finding.public_reference:
        return finding.public_reference
    owner = finding_owner(finding)
    if owner is None:
        raise ValueError(f"Finding {finding.id} has no reference owner")
    finding.public_reference = allocate_reference(session, *owner)
    session.add(finding)
    return finding.public_reference


def inherit_lead_reference(
    session: Session, finding: ScanFinding, lead: ScanLead
) -> str:
    """Make a finding created from a run-owned lead use the lead reference."""

    lead_reference = ensure_lead_reference(session, lead)
    destination_owner = finding_owner(finding)
    if destination_owner is None:
        raise ValueError(f"Finding {finding.id} has no reference owner")
    # Imported leads are owned by the destination run, so the lead and promoted
    # finding naturally share one reference. A direct promotion of an original
    # SAST row is the exception: keep the SAST reference as provenance and give
    # the destination finding a reference in its own run namespace.
    reference = (
        lead_reference
        if lead_owner(lead) == destination_owner
        else allocate_reference(session, *destination_owner)
    )
    finding.public_reference = reference
    finding.origin_type = lead.producer_run_type or lead.source or "sast"
    finding.origin_run_type = lead.producer_run_type
    finding.origin_run_id = lead.producer_run_id
    finding.origin_lead_id = lead.origin_lead_id or lead.id
    finding.origin_reference = lead.origin_reference or lead_reference
    if lead.imported_into_run_id is not None and lead.origin_reference is None:
        original = _find_original_lead(session, lead)
        if original is not None:
            ensure_lead_reference(session, original)
            lead.origin_lead_id = original.id
            lead.origin_reference = original.public_reference
            finding.origin_lead_id = original.id
            finding.origin_reference = original.public_reference
    session.add_all([lead, finding])
    return reference


def _find_original_lead(session: Session, lead: ScanLead) -> ScanLead | None:
    if lead.origin_lead_id:
        original = session.get(ScanLead, lead.origin_lead_id)
        if original is not None:
            return original
    if lead.imported_into_run_id is None:
        return lead
    return session.exec(
        select(ScanLead)
        .where(ScanLead.imported_into_run_id == None)  # noqa: E711
        .where(ScanLead.producer_run_type == lead.producer_run_type)
        .where(ScanLead.producer_run_id == lead.producer_run_id)
        .where(ScanLead.fingerprint == lead.fingerprint)
    ).first()


def ensure_campaign_finding_reference(
    session: Session,
    *,
    campaign_id: int,
    finding_id: int,
    target_member_id: int,
) -> CampaignFindingReference:
    existing = session.exec(
        select(CampaignFindingReference)
        .where(CampaignFindingReference.campaign_id == campaign_id)
        .where(CampaignFindingReference.finding_id == finding_id)
    ).first()
    if existing is not None:
        return existing
    row = CampaignFindingReference(
        campaign_id=campaign_id,
        finding_id=finding_id,
        target_member_id=target_member_id,
        public_reference=allocate_reference(session, "campaign", campaign_id),
    )
    session.add(row)
    session.flush()
    return row


def find_finding_by_reference(
    session: Session,
    owner_type: str,
    owner_id: int,
    reference: str,
) -> ScanFinding | None:
    owner_type = _normalize_owner_type(owner_type)
    query = select(ScanFinding).where(ScanFinding.public_reference == reference)
    if owner_type == "web":
        query = query.where(ScanFinding.test_run_id == owner_id)
    elif owner_type == "api":
        query = query.where(ScanFinding.api_test_run_id == owner_id)
    else:
        return None
    return session.exec(query).first()


def find_lead_by_reference(
    session: Session,
    owner_type: str,
    owner_id: int,
    reference: str,
) -> ScanLead | None:
    owner_type = _normalize_owner_type(owner_type)
    query = select(ScanLead).where(ScanLead.public_reference == reference)
    if owner_type == "sast":
        query = query.where(ScanLead.producer_run_type == "sast").where(
            ScanLead.producer_run_id == owner_id
        )
        query = query.where(ScanLead.imported_into_run_id == None)  # noqa: E711
    elif owner_type in {"web", "api"}:
        query = query.where(ScanLead.imported_into_run_type == owner_type).where(
            ScanLead.imported_into_run_id == owner_id
        )
    elif owner_type == "campaign":
        query = query.where(ScanLead.producer_run_type == "campaign").where(
            ScanLead.producer_run_id == owner_id
        )
        query = query.where(ScanLead.imported_into_run_id == None)  # noqa: E711
    else:
        return None
    return session.exec(query).first()


def ensure_references_for_rows(
    session: Session, rows: Iterable[ScanFinding | ScanLead]
) -> None:
    for row in rows:
        if isinstance(row, ScanFinding):
            ensure_finding_reference(session, row)
        else:
            ensure_lead_reference(session, row)
