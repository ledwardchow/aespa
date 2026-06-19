"""Service layer for ScanLead CRUD and context formatting."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import SastRun, ScanFinding, ScanLead

log = logging.getLogger(__name__)

_UTC = timezone.utc

# Confidence threshold — only leads at or above this are kept.
CONFIDENCE_THRESHOLD = 0.7

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
    """Return the *original* ScanLead rows created by a specific SAST run.

    Copies imported into a dynamic run (``imported_into_run_id`` set) are
    excluded so the SAST tab only ever shows the pristine originals.
    """
    with Session(get_engine(), expire_on_commit=False) as s:
        return list(s.exec(
            select(ScanLead)
            .where(ScanLead.producer_run_id == producer_run_id)
            .where(ScanLead.imported_into_run_id == None)  # noqa: E711
            .order_by(ScanLead.id)
        ).all())


def copy_leads_to_run(
    sast_run_id: int,
    target_run_type: str,
    target_run_id: int,
) -> int:
    """Copy a SAST run's original leads into a dynamic run as independent rows.

    Each copy is a fresh ScanLead owned by ``(target_run_type, target_run_id)``
    via ``imported_into_*`` and reset to status ``open``. The copy keeps
    ``producer_run_id`` pointing at the source SAST run for provenance. The
    originals are left untouched so the SAST tab keeps showing them as open.

    Idempotent per (target run, source SAST run): if this run already imported
    from this SAST run, nothing new is created. Returns the number of copies made.
    """
    with Session(get_engine()) as s:
        # Already imported from this SAST run into this target? Don't duplicate.
        already = s.exec(
            select(ScanLead)
            .where(ScanLead.imported_into_run_type == target_run_type)
            .where(ScanLead.imported_into_run_id == target_run_id)
            .where(ScanLead.producer_run_id == sast_run_id)
        ).first()
        if already is not None:
            return 0

        originals = list(s.exec(
            select(ScanLead)
            .where(ScanLead.producer_run_id == sast_run_id)
            .where(ScanLead.producer_run_type == "sast")
            .where(ScanLead.imported_into_run_id == None)  # noqa: E711
            .order_by(ScanLead.id)
        ).all())

        made = 0
        now = datetime.now(_UTC)
        for o in originals:
            copy = ScanLead(
                collection_id=o.collection_id,
                producer_run_type=o.producer_run_type,
                producer_run_id=o.producer_run_id,
                source=o.source,
                category=o.category,
                severity=o.severity,
                confidence=o.confidence,
                title=o.title,
                description=o.description,
                location=o.location,
                evidence=o.evidence,
                status="open",
                imported_into_run_type=target_run_type,
                imported_into_run_id=target_run_id,
                created_at=now,
                updated_at=now,
            )
            s.add(copy)
            made += 1
        s.commit()
    return made


def get_leads_for_run(target_run_type: str, target_run_id: int) -> list[ScanLead]:
    """Return open leads imported into a dynamic run (consumed by that scan)."""
    with Session(get_engine(), expire_on_commit=False) as s:
        return list(s.exec(
            select(ScanLead)
            .where(ScanLead.imported_into_run_type == target_run_type)
            .where(ScanLead.imported_into_run_id == target_run_id)
            .where(ScanLead.status == "open")
            .order_by(ScanLead.severity.desc(), ScanLead.confidence.desc())  # type: ignore[attr-defined]
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


def _promote_lead_to_finding(
    s: Session,
    lead: ScanLead,
    run_type: str | None,
    run_id: int | None,
) -> int | None:
    """Synthesise a ScanFinding from a confirmed lead and return its id.

    Called when a lead is confirmed but the caller supplied no finding to link.
    Without this, confirmation silently drops the finding — the lead reads
    "confirmed" but nothing surfaces in the findings list. Returns None if we
    cannot attribute the finding to a run, or links to an existing finding from
    the same run with a matching title to avoid duplicating one the agent
    already recorded.
    """
    if run_id is None:
        log.warning(
            "update_lead: lead %d confirmed without finding and no run_id to "
            "attribute one — cannot auto-promote", lead.id,
        )
        return None

    # API runs key on api_test_run_id; web runs key on test_run_id. The two id
    # spaces overlap, so writing the wrong column leaks the finding into the
    # other run of the same number.
    is_web = (run_type or "").lower() == "web"
    title = lead.title or "Confirmed static-analysis lead"

    # Dedup: if the agent already recorded a finding for this run with the same
    # title (case 2 — finding written but finding_id omitted from update_lead),
    # link to that one instead of creating a second.
    run_col = ScanFinding.test_run_id if is_web else ScanFinding.api_test_run_id
    existing = s.exec(
        select(ScanFinding)
        .where(run_col == run_id)  # type: ignore[arg-type]
        .where(ScanFinding.title == title)
    ).first()
    if existing is not None:
        return existing.id

    cat_raw = (lead.category or "").strip().upper()
    is_api_cat = cat_raw.startswith("API")
    finding = ScanFinding(
        test_run_id=run_id if is_web else None,
        api_test_run_id=None if is_web else run_id,
        owasp_category=(cat_raw if (cat_raw and not is_api_cat) else "A00"),
        owasp_api_category=(cat_raw if is_api_cat else None),
        severity=(lead.severity or "medium").lower(),
        title=title,
        description=lead.description or "",
        affected_url=lead.location or "",
        evidence=lead.evidence or "",
        recommendation=lead.note or "",
        finding_source="sast_lead",
        validation_status="confirmed",
        validation_note=lead.note or None,
    )
    s.add(finding)
    s.flush()  # populate finding.id within this transaction
    log.info(
        "update_lead: auto-promoted confirmed lead %d to finding %s (run_type=%s run_id=%s)",
        lead.id, finding.id, run_type, run_id,
    )
    return finding.id


def _link_promoted_finding_to_coverage(
    *,
    collection_id: int | None,
    run_id: int | None,
    category_raw: str,
    finding_id: int,
    hint_texts: list[str | None],
) -> dict | None:
    """Flip the API work-program cell for an auto-promoted finding.

    Mirrors report_finding's post-finding coverage hook so a confirmed lead also
    shows up on the matrix. Best-effort: a SAST lead's location is a code site
    (file:line), not a URL, so we scan the lead's text for route-path tokens and
    only flip a cell when one strictly matches an in-scope endpoint — never
    fabricating a match. Returns the linked cell, or None when nothing matched.
    """
    if collection_id is None or run_id is None:
        return None

    cat = (category_raw or "").strip().upper()
    try:
        from aespa.services.api_scanner import (
            OWASP_API_CATEGORIES,
            _match_endpoint_for_url,
            update_coverage_cell,
        )
        from aespa.models import ApiCollection, ApiEndpoint
    except Exception as exc:  # pragma: no cover - import guard
        log.debug("coverage link skipped (import failed): %s", exc)
        return None

    if cat not in OWASP_API_CATEGORIES:
        return None  # only API categories live on the work program

    import re

    tokens: list[str] = []
    for text in hint_texts:
        if not text:
            continue
        for raw in re.findall(r"/[A-Za-z0-9_./{}-]+", text):
            tok = raw.rstrip(".,;:)")
            if tok and tok not in tokens:
                tokens.append(tok)
    if not tokens:
        return None

    with Session(get_engine()) as s:
        endpoints = list(s.exec(
            select(ApiEndpoint)
            .where(ApiEndpoint.collection_id == collection_id)
            .where(ApiEndpoint.in_scope == True)  # noqa: E712
        ).all())
        coll = s.get(ApiCollection, collection_id)
        base = (coll.base_url if coll else "").rstrip("/")

    ep = None
    for tok in tokens:
        ep = _match_endpoint_for_url(tok, endpoints, base)
        if ep is not None:
            break
    if ep is None or ep.id is None:
        log.info(
            "update_lead: promoted finding %s not linked to coverage — no endpoint "
            "matched lead path hints %s", finding_id, tokens,
        )
        return None

    update_coverage_cell(run_id, ep.id, cat, "finding", finding_id=finding_id)
    log.info(
        "update_lead: promoted finding %s flipped work-program cell endpoint=%s category=%s",
        finding_id, ep.id, cat,
    )
    return {"endpoint_id": ep.id, "owasp_api_category": cat}


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

        # A confirmed lead must always be backed by a finding. If the caller did
        # not link one (the agent marked it confirmed without recording a
        # finding), synthesise one from the lead so confirmation never silently
        # drops a finding.
        promoted_id = None
        run_type = investigated_by_run_type or lead.investigated_by_run_type
        run_id = investigated_by_run_id or lead.investigated_by_run_id
        if status == "confirmed" and lead.linked_finding_id is None:
            promoted_id = _promote_lead_to_finding(s, lead, run_type, run_id)
            if promoted_id is not None:
                lead.linked_finding_id = promoted_id

        lead.updated_at = datetime.now(_UTC)
        s.add(lead)
        # Snapshot the fields the coverage hook needs before the session closes.
        cov_args = None
        if promoted_id is not None and (run_type or "").lower() != "web":
            cov_args = {
                "collection_id": lead.collection_id,
                "run_id": run_id,
                "category_raw": lead.category,
                "finding_id": promoted_id,
                "hint_texts": [lead.location, lead.title, lead.description, lead.evidence],
            }
        s.commit()
        s.refresh(lead)

    # Flip the API work-program cell for the auto-promoted finding, mirroring
    # report_finding's coverage hook. Done after commit so the coverage write
    # runs in its own transaction. Best-effort — never fails the lead update.
    if cov_args is not None:
        try:
            _link_promoted_finding_to_coverage(**cov_args)
        except Exception as exc:
            log.debug("update_lead: coverage link failed: %s", exc)

    return lead


def format_leads_for_context(collection_id: int, cap: int = 20) -> str:
    """Return a formatted 'Investigation leads' block for the dynamic scan context.

    Used by API scans, keyed on the collection. Returns an empty string if there
    are no open leads.
    """
    return _format_leads_block(get_open_leads_for_collection(collection_id)[:cap])


def format_leads_for_run(
    target_run_type: str, target_run_id: int, cap: int = 20
) -> str:
    """Return the investigation-leads block for a dynamic run's imported leads.

    Used by web scans, keyed on the run that imported the leads. Returns an empty
    string if no open leads have been imported.
    """
    return _format_leads_block(
        get_leads_for_run(target_run_type, target_run_id)[:cap]
    )


def _format_leads_block(leads: list[ScanLead]) -> str:
    """Shared 'STATIC ANALYSIS INVESTIGATION LEADS' renderer for the scan context."""
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
