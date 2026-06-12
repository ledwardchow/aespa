"""Service layer for ScanLead CRUD and context formatting."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import SastRun, ScanLead

log = logging.getLogger(__name__)

_UTC = timezone.utc

# Confidence threshold — only leads at or above this are kept.
CONFIDENCE_THRESHOLD = 0.8

# How far back (in seconds) a SAST run is considered "fresh" enough to skip
# auto-creation of a new one.
_FRESH_WINDOW_S = 24 * 3600  # 24 hours


def create_lead(
    *,
    producer_run_id: int,
    producer_run_type: str = "sast",
    collection_id: int | None = None,
    title: str,
    description: str,
    category: str = "",
    severity: str = "medium",
    confidence: float,
    location: str = "",
    evidence: str = "",
    source: str = "sast",
) -> ScanLead:
    """Persist a single high-confidence ScanLead and return it."""
    lead = ScanLead(
        producer_run_id=producer_run_id,
        producer_run_type=producer_run_type,
        collection_id=collection_id,
        title=title,
        description=description,
        category=category,
        severity=severity,
        confidence=confidence,
        location=location,
        evidence=evidence,
        source=source,
        status="open",
        created_at=datetime.now(_UTC),
        updated_at=datetime.now(_UTC),
    )
    with Session(get_engine()) as s:
        s.add(lead)
        s.commit()
        s.refresh(lead)
    return lead


def list_leads_for_run(producer_run_id: int) -> list[ScanLead]:
    """Return all ScanLead rows created by a specific SAST run."""
    with Session(get_engine(), expire_on_commit=False) as s:
        return list(s.exec(
            select(ScanLead)
            .where(ScanLead.producer_run_id == producer_run_id)
            .order_by(ScanLead.id)
        ).all())


def get_open_leads_for_collection(collection_id: int) -> list[ScanLead]:
    """Return open ScanLead rows for a collection (consumed by dynamic scans)."""
    with Session(get_engine(), expire_on_commit=False) as s:
        return list(s.exec(
            select(ScanLead)
            .where(ScanLead.collection_id == collection_id)
            .where(ScanLead.status == "open")
            .order_by(ScanLead.severity.desc(), ScanLead.confidence.desc())  # type: ignore[attr-defined]
        ).all())


def needs_fresh_sast(collection_id: int) -> bool:
    """Return True if the collection should get an auto-created SAST pre-phase.

    True when there is no recent completed SastRun for this collection.
    """
    import time as _time
    cutoff = datetime.fromtimestamp(_time.time() - _FRESH_WINDOW_S, tz=_UTC)
    with Session(get_engine()) as s:
        recent = s.exec(
            select(SastRun)
            .where(SastRun.collection_id == collection_id)
            .where(SastRun.status == "completed")
            .where(SastRun.completed_at >= cutoff)  # type: ignore[arg-type]
        ).first()
    return recent is None


def update_lead(
    lead_id: int,
    *,
    status: str,
    note: str = "",
    investigated_by_run_type: str | None = None,
    investigated_by_run_id: int | None = None,
    linked_finding_id: int | None = None,
) -> ScanLead | None:
    """Record the outcome of a dynamic investigation on a lead. Returns updated lead."""
    allowed_statuses = {"investigating", "confirmed", "dismissed", "inconclusive"}
    if status not in allowed_statuses:
        log.warning("update_lead: invalid status %r for lead %d", status, lead_id)
        return None
    with Session(get_engine()) as s:
        lead = s.get(ScanLead, lead_id)
        if lead is None:
            log.warning("update_lead: lead %d not found", lead_id)
            return None
        lead.status = status
        if note:
            lead.note = note
        if investigated_by_run_type is not None:
            lead.investigated_by_run_type = investigated_by_run_type
        if investigated_by_run_id is not None:
            lead.investigated_by_run_id = investigated_by_run_id
        if linked_finding_id is not None:
            lead.linked_finding_id = linked_finding_id
        lead.updated_at = datetime.now(_UTC)
        s.add(lead)
        s.commit()
        s.refresh(lead)
        return lead


def format_leads_for_context(collection_id: int, cap: int = 20) -> str:
    """Return a formatted 'Investigation leads' block for the dynamic scan context.

    Returns an empty string if there are no open leads.
    """
    leads = get_open_leads_for_collection(collection_id)[:cap]
    if not leads:
        return ""

    lines = [
        "=== STATIC ANALYSIS INVESTIGATION LEADS ===",
        "The following leads were produced by a prior SAST scan. They are UNPROVEN "
        "static-analysis hypotheses — you MUST reproduce each against the live target "
        "before writing a finding. After investigating each lead, call update_lead with "
        "the outcome and a note explaining what you tested.",
        "",
    ]
    for lead in leads:
        sev = (lead.severity or "medium").upper()
        conf_pct = int((lead.confidence or 0) * 100)
        lines.append(
            f"[Lead #{lead.id}] [{sev}] {lead.title}"
        )
        lines.append(f"  Category: {lead.category or 'unknown'}  Confidence: {conf_pct}%")
        lines.append(f"  Location: {lead.location or 'unknown'}")
        lines.append(f"  Description: {lead.description}")
        if lead.evidence:
            # Trim evidence to keep context size reasonable
            evidence_preview = lead.evidence[:400] + ("…" if len(lead.evidence) > 400 else "")
            lines.append(f"  Evidence: {evidence_preview}")
        lines.append("")

    return "\n".join(lines)
