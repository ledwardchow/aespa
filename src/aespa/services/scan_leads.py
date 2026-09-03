"""Service layer for ScanLead CRUD and context formatting."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone

from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import ScanFinding, ScanLead
from aespa.services.references import (
    ensure_lead_reference,
    inherit_lead_reference,
)

log = logging.getLogger(__name__)

_UTC = timezone.utc

# Confidence threshold — only leads at or above this are kept.
CONFIDENCE_THRESHOLD = 0.7


def decode_attack_path(value: str | None) -> dict:
    """Decode a persisted SAST attack path without trusting its shape."""
    try:
        parsed = json.loads(value or "{}")
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _decode_structured_json(value: str | None, default: object) -> object:
    """Decode a persisted structured lead field without failing the context tool."""
    try:
        parsed = json.loads(value or json.dumps(default))
    except (TypeError, ValueError, json.JSONDecodeError):
        return default
    if isinstance(default, dict) and not isinstance(parsed, dict):
        return default
    if isinstance(default, list) and not isinstance(parsed, list):
        return default
    return parsed


def _prompt_text(value: object, limit: int = 600) -> str:
    """Return bounded, readable text for an agent context block."""
    text = str(value or "").strip()
    return text[:limit] + ("…" if len(text) > limit else "")


def format_attack_path_for_prompt(
    attack_path: dict, *, _nested: bool = False
) -> list[str]:
    """Render SAST attack-path fields as bounded dynamic-test guidance."""
    if not isinstance(attack_path, dict):
        return []

    lines: list[str] = []
    live = attack_path.get("live_frontend_context")
    if isinstance(live, dict):
        resolution = _prompt_text(live.get("resolution_status"))
        if resolution:
            lines.append(f"  Live frontend resolution: {resolution}")
        for key, label in (
            ("url", "Frontend URL"),
            ("route", "Frontend route"),
            ("action", "Frontend action"),
            ("trigger", "Frontend trigger"),
        ):
            value = _prompt_text(live.get(key))
            if value:
                lines.append(f"  {label}: {value}")
        request = live.get("request")
        if isinstance(request, dict):
            method = _prompt_text(request.get("method"))
            path = _prompt_text(request.get("path"))
            if method or path:
                lines.append(f"  Live request: {(method + ' ' + path).strip()}")
            mutations = request.get("mutation_points")
            if isinstance(mutations, list) and mutations:
                lines.append(
                    "  Live mutation points: "
                    + ", ".join(_prompt_text(item, 160) for item in mutations[:12])
                )

    if not _nested:
        final_objective = _prompt_text(attack_path.get("dynamic_test"))
        if final_objective:
            lines.append(f"  Final frontend dynamic test: {final_objective}")

    approved = attack_path.get("approved_pre_crawl_path")
    if isinstance(approved, dict):
        lines.append("  Approved pre-crawl path:")
        lines.extend(format_attack_path_for_prompt(approved, _nested=True))

    prerequisites = attack_path.get("prerequisites")
    if not isinstance(prerequisites, list) and isinstance(approved, dict):
        prerequisites = approved.get("prerequisites")
    if isinstance(prerequisites, list):
        values = [
            _prompt_text(item, 180) for item in prerequisites if str(item or "").strip()
        ]
        if values:
            lines.append("  Prerequisites: " + "; ".join(values[:12]))

    mutation_points = attack_path.get("mutation_points")
    if not isinstance(mutation_points, list) and isinstance(approved, dict):
        mutation_points = approved.get("mutation_points")
    if isinstance(mutation_points, list):
        values = [
            _prompt_text(item, 180)
            for item in mutation_points
            if str(item or "").strip()
        ]
        if values:
            lines.append("  Mutation points: " + ", ".join(values[:12]))

    nodes = attack_path.get("nodes")
    if isinstance(nodes, list):
        node_text = " → ".join(
            _prompt_text(node, 220) for node in nodes if str(node or "").strip()
        )
        if node_text:
            lines.append(f"  Reachability: {node_text[:1000]}")
    hops = attack_path.get("hops")
    if not isinstance(hops, list) and isinstance(approved, dict):
        hops = approved.get("hops")
    if isinstance(hops, list) and hops:
        lines.append(
            "  Ordered component hops: "
            + _prompt_text(json.dumps(hops[:12], separators=(",", ":")), 1600)
        )
    for key, label in (
        ("impact", "Impact"),
        ("severity_reasoning", "Severity reasoning"),
        ("dynamic_test", "Dynamic test objective"),
    ):
        if not _nested and key == "dynamic_test":
            continue
        value = _prompt_text(attack_path.get(key))
        if value:
            lines.append(f"  {label}: {value}")
    gaps = attack_path.get("proof_gaps")
    if isinstance(gaps, list):
        values = [_prompt_text(item, 180) for item in gaps if str(item or "").strip()]
        if values:
            lines.append("  Proof gaps: " + "; ".join(values[:12]))
    origin = attack_path.get("origin_attack_path")
    if isinstance(origin, dict) and origin:
        lines.append(
            "  Original backend SAST path retained for evidence: "
            + _prompt_text(json.dumps(origin, separators=(",", ":")), 1200)
        )
    return lines


def lead_fingerprint(*, category: str, title: str, location: str) -> str:
    """Return a stable, run-independent identity for a static candidate."""
    canonical = "|".join(part.strip().lower() for part in (category, title, location))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def upsert_lead(
    session: Session,
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
    fingerprint: str = "",
    suggested_endpoint: str = "",
    source_trace: dict | None = None,
    controls: list | None = None,
    sink_trace: dict | None = None,
    counterevidence: list | None = None,
    proof_gaps: list | None = None,
    validation_status: str = "pending",
    validation_reasoning: str = "",
    attack_path: dict | None = None,
    reportable: bool = True,
) -> ScanLead:
    """Upsert one original static candidate by stable fingerprint, within an
    already-open ``session``.

    Session-aware core of ``create_lead``: adds/flushes the row but never
    commits or opens its own ``Session`` — callers that are already inside a
    transaction (e.g. ``services.correlation``) can write a lead alongside
    their other changes and commit exactly once, atomically. ``create_lead``
    below is the standalone convenience wrapper every other caller keeps
    using unchanged.
    """
    fingerprint = fingerprint or lead_fingerprint(
        category=category, title=title, location=location
    )
    now = datetime.now(_UTC)
    lead = session.exec(
        select(ScanLead)
        .where(ScanLead.producer_run_id == producer_run_id)
        .where(ScanLead.producer_run_type == producer_run_type)
        .where(ScanLead.imported_into_run_id == None)  # noqa: E711
        .where(ScanLead.fingerprint == fingerprint)
    ).first()
    if lead is None:
        lead = session.exec(
            select(ScanLead)
            .where(ScanLead.producer_run_id == producer_run_id)
            .where(ScanLead.producer_run_type == producer_run_type)
            .where(ScanLead.imported_into_run_id == None)  # noqa: E711
            .where(ScanLead.category == category)
            .where(ScanLead.title == title)
            .where(ScanLead.location == location)
        ).first()
    if lead is None:
        lead = ScanLead(
            producer_run_id=producer_run_id,
            producer_run_type=producer_run_type,
            collection_id=collection_id,
            fingerprint=fingerprint,
            created_at=now,
        )
    lead.title = title
    lead.description = description
    lead.category = category
    lead.severity = severity
    lead.confidence = confidence
    lead.location = location
    lead.evidence = evidence
    lead.source = source
    lead.suggested_endpoint = suggested_endpoint
    lead.source_trace_json = json.dumps(source_trace or {}, ensure_ascii=False)
    lead.control_trace_json = json.dumps(controls or [], ensure_ascii=False)
    lead.sink_trace_json = json.dumps(sink_trace or {}, ensure_ascii=False)
    lead.counterevidence_json = json.dumps(counterevidence or [], ensure_ascii=False)
    lead.proof_gaps_json = json.dumps(proof_gaps or [], ensure_ascii=False)
    lead.validation_status = validation_status
    lead.validation_reasoning = validation_reasoning
    lead.attack_path_json = json.dumps(attack_path or {}, ensure_ascii=False)
    lead.reportable = reportable
    lead.status = (
        "open"
        if reportable
        else ("dismissed" if validation_status == "dismissed" else "inconclusive")
    )
    lead.updated_at = now
    session.add(lead)
    session.flush()
    ensure_lead_reference(session, lead)
    session.flush()
    return lead


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
    fingerprint: str = "",
    suggested_endpoint: str = "",
    source_trace: dict | None = None,
    controls: list | None = None,
    sink_trace: dict | None = None,
    counterevidence: list | None = None,
    proof_gaps: list | None = None,
    validation_status: str = "pending",
    validation_reasoning: str = "",
    attack_path: dict | None = None,
    reportable: bool = True,
) -> ScanLead:
    """Upsert one original static candidate by stable fingerprint.

    Standalone convenience wrapper: opens its own ``Session``, commits, and
    returns a detached instance. Use ``upsert_lead`` instead when the write
    must happen inside a transaction the caller already owns.
    """
    with Session(get_engine()) as s:
        lead = upsert_lead(
            s,
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
            fingerprint=fingerprint,
            suggested_endpoint=suggested_endpoint,
            source_trace=source_trace,
            controls=controls,
            sink_trace=sink_trace,
            counterevidence=counterevidence,
            proof_gaps=proof_gaps,
            validation_status=validation_status,
            validation_reasoning=validation_reasoning,
            attack_path=attack_path,
            reportable=reportable,
        )
        s.commit()
        s.refresh(lead)
        s.expunge(lead)
    return lead


def list_leads_for_run(producer_run_id: int) -> list[ScanLead]:
    """Return the *original* ScanLead rows created by a specific SAST run.

    Copies imported into a dynamic run (``imported_into_run_id`` set) are
    excluded so the SAST tab only ever shows the pristine originals.
    """
    with Session(get_engine(), expire_on_commit=False) as s:
        return list(
            s.exec(
                select(ScanLead)
                .where(ScanLead.producer_run_id == producer_run_id)
                .where(ScanLead.imported_into_run_id == None)  # noqa: E711
                .order_by(ScanLead.id)
            ).all()
        )


def _copy_path_metadata(source: ScanLead, target: ScanLead) -> None:
    for name in (
        "origin_component_id",
        "origin_sast_run_id",
        "origin_path_json",
        "origin_lead_id",
        "trace_path_key",
        "trace_status",
        "trace_confidence",
    ):
        if hasattr(source, name) and hasattr(target, name):
            setattr(target, name, getattr(source, name))


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
        originals = list(
            s.exec(
                select(ScanLead)
                .where(ScanLead.producer_run_id == sast_run_id)
                .where(ScanLead.producer_run_type == "sast")
                .where(ScanLead.imported_into_run_id == None)  # noqa: E711
                .where(ScanLead.reportable == True)  # noqa: E712
                .order_by(ScanLead.id)
            ).all()
        )

        made = 0
        now = datetime.now(_UTC)
        for o in originals:
            ensure_lead_reference(s, o)
            if not o.fingerprint:
                o.fingerprint = lead_fingerprint(
                    category=o.category, title=o.title, location=o.location
                )
                s.add(o)
            already = s.exec(
                select(ScanLead)
                .where(ScanLead.imported_into_run_type == target_run_type)
                .where(ScanLead.imported_into_run_id == target_run_id)
                .where(ScanLead.producer_run_id == sast_run_id)
                .where(ScanLead.fingerprint == o.fingerprint)
            ).first()
            if already is not None:
                continue
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
                fingerprint=o.fingerprint,
                suggested_endpoint=o.suggested_endpoint,
                source_trace_json=o.source_trace_json,
                control_trace_json=o.control_trace_json,
                sink_trace_json=o.sink_trace_json,
                counterevidence_json=o.counterevidence_json,
                proof_gaps_json=o.proof_gaps_json,
                validation_status=o.validation_status,
                validation_reasoning=o.validation_reasoning,
                attack_path_json=o.attack_path_json,
                reportable=o.reportable,
                status="open",
                imported_into_run_type=target_run_type,
                imported_into_run_id=target_run_id,
                origin_lead_id=o.id,
                origin_reference=o.public_reference,
                created_at=now,
                updated_at=now,
            )
            _copy_path_metadata(o, copy)
            s.add(copy)
            ensure_lead_reference(s, copy)
            made += 1
        s.commit()
    return made


def copy_lead_to_run(
    lead_id: int, target_run_type: str, target_run_id: int
) -> ScanLead:
    """Idempotently copy one reportable original lead into a dynamic run."""
    with Session(get_engine()) as s:
        original = s.get(ScanLead, lead_id)
        if (
            original is None
            or original.imported_into_run_id is not None
            or not original.reportable
        ):
            raise ValueError("Lead is not eligible for dynamic handoff")
        existing = s.exec(
            select(ScanLead)
            .where(ScanLead.imported_into_run_type == target_run_type)
            .where(ScanLead.imported_into_run_id == target_run_id)
            .where(ScanLead.producer_run_id == original.producer_run_id)
            .where(ScanLead.fingerprint == original.fingerprint)
        ).first()
        if existing is not None:
            s.expunge(existing)
            return existing
        ensure_lead_reference(s, original)
        copied = ScanLead(
            collection_id=original.collection_id,
            producer_run_type=original.producer_run_type,
            producer_run_id=original.producer_run_id,
            source=original.source,
            category=original.category,
            severity=original.severity,
            confidence=original.confidence,
            title=original.title,
            description=original.description,
            location=original.location,
            evidence=original.evidence,
            fingerprint=original.fingerprint,
            suggested_endpoint=original.suggested_endpoint,
            source_trace_json=original.source_trace_json,
            control_trace_json=original.control_trace_json,
            sink_trace_json=original.sink_trace_json,
            counterevidence_json=original.counterevidence_json,
            proof_gaps_json=original.proof_gaps_json,
            validation_status=original.validation_status,
            validation_reasoning=original.validation_reasoning,
            attack_path_json=original.attack_path_json,
            reportable=True,
            status="open",
            imported_into_run_type=target_run_type,
            imported_into_run_id=target_run_id,
            origin_lead_id=original.id,
            origin_reference=original.public_reference,
            created_at=datetime.now(_UTC),
            updated_at=datetime.now(_UTC),
        )
        _copy_path_metadata(original, copied)
        s.add(copied)
        ensure_lead_reference(s, copied)
        s.commit()
        s.refresh(copied)
        s.expunge(copied)
        return copied


def prepend_frontend_context_to_copied_lead(
    lead_id: int,
    *,
    context: dict | None,
    warning: str | None = None,
) -> ScanLead | None:
    """Prepend target-specific crawl context without changing the source lead."""
    with Session(get_engine()) as session:
        lead = session.get(ScanLead, lead_id)
        if lead is None or lead.imported_into_run_id is None:
            return None
        path = decode_attack_path(lead.attack_path_json)
        if not path:
            path = {"schema_version": 2, "perspective": "frontend"}
        if (
            path.get("perspective") == "frontend"
            and "approved_pre_crawl_path" not in path
        ):
            path["approved_pre_crawl_path"] = dict(path)
        live = dict(context or {})
        if warning:
            live.setdefault("warnings", []).append(warning)
            live.setdefault("resolution_status", "unavailable")
            gaps = path.setdefault("proof_gaps", [])
            if warning not in gaps:
                gaps.append(warning)
        path["live_frontend_context"] = live
        path["post_crawl_changes"] = live.get("post_crawl_changes", [])
        path["schema_version"] = max(int(path.get("schema_version", 1)), 2)
        lead.attack_path_json = json.dumps(path, ensure_ascii=False)
        if hasattr(lead, "trace_status") and live.get("resolution_status"):
            lead.trace_status = str(live["resolution_status"])
        lead.updated_at = datetime.now(_UTC)
        session.add(lead)
        session.commit()
        session.refresh(lead)
        session.expunge(lead)
        return lead


def set_final_frontend_path(
    lead_id: int,
    *,
    final_path: dict,
    warning: str | None = None,
) -> ScanLead | None:
    """Persist a resolved frontend path on one copied lead."""
    with Session(get_engine()) as session:
        lead = session.get(ScanLead, lead_id)
        if lead is None or lead.imported_into_run_id is None:
            return None
        path = dict(final_path)
        if warning:
            path.setdefault("warnings", []).append(warning)
        if "approved_pre_crawl_path" not in path:
            path["approved_pre_crawl_path"] = decode_attack_path(
                getattr(lead, "origin_path_json", "") or lead.attack_path_json
            )
        lead.attack_path_json = json.dumps(path, separators=(",", ":"))
        if hasattr(lead, "trace_status") and path.get("live_frontend_context", {}).get(
            "resolution_status"
        ) in {"matched", "partial"}:
            lead.trace_status = "live_resolved"
        lead.updated_at = datetime.now(_UTC)
        session.add(lead)
        session.commit()
        session.refresh(lead)
        session.expunge(lead)
        return lead


def get_leads_for_run(target_run_type: str, target_run_id: int) -> list[ScanLead]:
    """Return open leads imported into a dynamic run (consumed by that scan)."""
    with Session(get_engine(), expire_on_commit=False) as s:
        leads = list(
            s.exec(
                select(ScanLead)
                .where(ScanLead.imported_into_run_type == target_run_type)
                .where(ScanLead.imported_into_run_id == target_run_id)
                .where(ScanLead.status == "open")
                .order_by(ScanLead.severity.desc(), ScanLead.confidence.desc())  # type: ignore[attr-defined]
            ).all()
        )
        for lead in leads:
            ensure_lead_reference(s, lead)
        s.commit()
        return leads


def get_all_leads_for_run(target_run_type: str, target_run_id: int) -> list[ScanLead]:
    """Return ALL leads imported into a dynamic run, regardless of status."""
    with Session(get_engine(), expire_on_commit=False) as s:
        leads = list(
            s.exec(
                select(ScanLead)
                .where(ScanLead.imported_into_run_type == target_run_type)
                .where(ScanLead.imported_into_run_id == target_run_id)
                .order_by(ScanLead.id)
            ).all()
        )
        for lead in leads:
            ensure_lead_reference(s, lead)
        s.commit()
        return leads


def get_lead_detail_for_run(
    target_run_type: str,
    target_run_id: int,
    lead_id: int | None = None,
    lead_reference: str | None = None,
) -> dict | None:
    """Return complete actionable detail only for a lead owned by this run."""
    normalized_type = (target_run_type or "").strip().lower()
    with Session(get_engine(), expire_on_commit=False) as s:
        query = (
            select(ScanLead)
            .where(ScanLead.imported_into_run_type == normalized_type)
            .where(ScanLead.imported_into_run_id == target_run_id)
        )
        if lead_reference:
            query = query.where(ScanLead.public_reference == lead_reference)
        else:
            query = query.where(ScanLead.id == lead_id)
        lead = s.exec(query).first()
        if lead is None:
            return None
        return {
            "id": lead.id,
            "reference": lead.reference,
            "source_sast_run_id": lead.producer_run_id,
            "source": lead.source,
            "fingerprint": lead.fingerprint,
            "category": lead.category,
            "severity": lead.severity,
            "confidence": lead.confidence,
            "title": lead.title,
            "description": lead.description,
            "location": lead.location,
            "status": lead.status or "open",
            "evidence": lead.evidence,
            "suggested_endpoint": lead.suggested_endpoint,
            "source_trace": _decode_structured_json(lead.source_trace_json, {}),
            "control_trace": _decode_structured_json(lead.control_trace_json, []),
            "sink_trace": _decode_structured_json(lead.sink_trace_json, {}),
            "counterevidence": _decode_structured_json(lead.counterevidence_json, []),
            "proof_gaps": _decode_structured_json(lead.proof_gaps_json, []),
            "validation_status": lead.validation_status,
            "validation_reasoning": lead.validation_reasoning,
            "attack_path": decode_attack_path(lead.attack_path_json),
            "note": lead.note,
            "linked_finding_id": lead.linked_finding_id,
            "imported_into_run_type": lead.imported_into_run_type,
            "imported_into_run_id": lead.imported_into_run_id,
        }


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
            "attribute one — cannot auto-promote",
            lead.id,
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
        inherit_lead_reference(s, existing, lead)
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
    inherit_lead_reference(s, finding, lead)
    log.info(
        "update_lead: auto-promoted confirmed lead %d to finding %s (run_type=%s run_id=%s)",
        lead.id,
        finding.id,
        run_type,
        run_id,
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
        from aespa.models import ApiCollection, ApiEndpoint
        from aespa.services.api_scanner import (
            OWASP_API_CATEGORIES,
            _match_endpoint_for_url,
            update_coverage_cell,
        )
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
        endpoints = list(
            s.exec(
                select(ApiEndpoint)
                .where(ApiEndpoint.collection_id == collection_id)
                .where(ApiEndpoint.in_scope == True)  # noqa: E712
            ).all()
        )
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
            "matched lead path hints %s",
            finding_id,
            tokens,
        )
        return None

    update_coverage_cell(run_id, ep.id, cat, "finding", finding_id=finding_id)
    log.info(
        "update_lead: promoted finding %s flipped work-program cell endpoint=%s category=%s",
        finding_id,
        ep.id,
        cat,
    )
    return {"endpoint_id": ep.id, "owasp_api_category": cat}


def update_lead(
    lead_id: int,
    *,
    status: str,
    note: str = "",
    owner_run_type: str | None = None,
    owner_run_id: int | None = None,
    investigated_by_run_type: str | None = None,
    investigated_by_run_id: int | None = None,
    linked_finding_id: int | None = None,
    link_coverage: bool = True,
) -> ScanLead | None:
    """Record the outcome of a dynamic investigation on a lead.

    Dynamic agents must provide the run that owns the imported lead.  The
    ownership check is deliberately optional for backwards-compatible service
    callers that operate on original SAST rows, but every scanner/ALICE call
    supplies it.  The kind is retained because this is a soft link across
    different run surfaces, so both dimensions are required for the protected path.
    """
    allowed_statuses = {"investigating", "confirmed", "dismissed", "inconclusive"}
    if status not in allowed_statuses:
        log.warning("update_lead: invalid status %r for lead %d", status, lead_id)
        return None
    with Session(get_engine()) as s:
        lead = s.get(ScanLead, lead_id)
        if lead is None:
            log.warning("update_lead: lead %d not found", lead_id)
            return None
        if (owner_run_type is None) != (owner_run_id is None):
            log.warning(
                "update_lead: incomplete owner for lead %d (type=%r id=%r)",
                lead_id,
                owner_run_type,
                owner_run_id,
            )
            return None
        if owner_run_type is not None and owner_run_id is not None:
            normalized_owner = owner_run_type.lower()
            if (
                lead.imported_into_run_type != normalized_owner
                or lead.imported_into_run_id != owner_run_id
            ):
                log.warning(
                    "update_lead: lead %d is not owned by %s run %d",
                    lead_id,
                    normalized_owner,
                    owner_run_id,
                )
                return None
            if linked_finding_id is not None:
                finding = s.get(ScanFinding, linked_finding_id)
                if finding is None:
                    log.warning(
                        "update_lead: linked finding %d not found for lead %d",
                        linked_finding_id,
                        lead_id,
                    )
                    return None
                finding_run_id = (
                    finding.test_run_id
                    if normalized_owner == "web"
                    else finding.api_test_run_id
                )
                if finding_run_id != owner_run_id:
                    log.warning(
                        "update_lead: finding %d does not belong to %s run %d",
                        linked_finding_id,
                        normalized_owner,
                        owner_run_id,
                    )
                    return None
                inherit_lead_reference(s, finding, lead)
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
        run_type = (
            investigated_by_run_type
            if investigated_by_run_type is not None
            else lead.investigated_by_run_type
        )
        run_id = (
            investigated_by_run_id
            if investigated_by_run_id is not None
            else lead.investigated_by_run_id
        )
        if status == "confirmed" and lead.linked_finding_id is None:
            promoted_id = _promote_lead_to_finding(s, lead, run_type, run_id)
            if promoted_id is not None:
                lead.linked_finding_id = promoted_id

        lead.updated_at = datetime.now(_UTC)
        s.add(lead)
        # Snapshot the fields the coverage hook needs before the session closes.
        cov_args = None
        if (
            link_coverage
            and promoted_id is not None
            and (run_type or "").lower() != "web"
        ):
            cov_args = {
                "collection_id": lead.collection_id,
                "run_id": run_id,
                "category_raw": lead.category,
                "finding_id": promoted_id,
                "hint_texts": [
                    lead.location,
                    lead.title,
                    lead.description,
                    lead.evidence,
                ],
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


def format_leads_for_run(
    target_run_type: str, target_run_id: int, cap: int = 20
) -> str:
    """Return the investigation-leads block for a dynamic run's imported leads.

    Used by web scans, keyed on the run that imported the leads. Returns an empty
    string if no open leads have been imported.
    """
    return _format_leads_block(get_leads_for_run(target_run_type, target_run_id)[:cap])


def format_leads_for_scan_context(
    target_run_type: str,
    target_run_id: int,
    coverage_mode: str,
) -> str:
    """Return the lead context appropriate for a dynamic scan mode.

    Quick and Standard scans must resolve every imported lead, so they receive
    the complete compact index and fetch full lead details as they work. Full
    scans retain the detailed, capped context used by the general coverage workflow.
    """
    if coverage_mode in {"track", "standard", "sast_validate"}:
        return format_lead_index_for_validation(target_run_type, target_run_id)
    return format_leads_for_run(target_run_type, target_run_id)


def format_lead_index_for_validation(
    target_run_type: str,
    target_run_id: int,
) -> str:
    """Render every open imported lead as a compact SAST Validate work list."""
    leads = get_leads_for_run(target_run_type, target_run_id)
    if not leads:
        return ""

    lines = [
        "=== SAST VALIDATION LEAD INDEX ===",
        "Every entry below is an unproven static-analysis hypothesis. "
        "Before investigating a lead, call context_tool with "
        'tool=lead_detail and args={"lead_reference": "<reference>"} to retrieve its complete '
        "evidence, traces, proof gaps, reasoning, and attack path.",
        "",
    ]
    for lead in leads:
        attack_path = decode_attack_path(lead.attack_path_json)
        objective = _prompt_text(attack_path.get("dynamic_test"), 240)
        lines.append(
            f"[Lead {lead.reference or f'#{lead.id}'}] [{(lead.severity or 'medium').upper()}] "
            f"[{int((lead.confidence or 0) * 100)}% confidence] {lead.title}"
        )
        lines.append(
            f"  Category: {lead.category or 'unknown'}  "
            f"Location: {lead.location or 'unknown'}"
        )
        lines.append(f"  Suggested endpoint: {lead.suggested_endpoint or 'none'}")
        lines.append(f"  Dynamic-test objective: {objective or 'retrieve lead_detail'}")
        lines.append(
            f"  Required first action: context_tool(tool=lead_detail, "
            f'args={{"lead_reference": "{lead.reference}"}})'
        )
        lines.append("")
    return "\n".join(lines)


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
        lines.append(f"[Lead {lead.reference or f'#{lead.id}'}] [{sev}] {lead.title}")
        lines.append(
            f"  Category: {lead.category or 'unknown'}  Confidence: {conf_pct}%"
        )
        lines.append(f"  Location: {lead.location or 'unknown'}")
        lines.append(f"  Description: {lead.description}")
        if lead.evidence:
            # Trim evidence to keep context size reasonable
            evidence_preview = lead.evidence[:400] + (
                "…" if len(lead.evidence) > 400 else ""
            )
            lines.append(f"  Evidence: {evidence_preview}")
        attack_path_lines = format_attack_path_for_prompt(
            decode_attack_path(lead.attack_path_json)
        )
        if attack_path_lines:
            lines.append(
                "  Static attack path (a hypothesis, not runtime proof; verify every hop):"
            )
            lines.extend(attack_path_lines)
        lines.append("")

    return "\n".join(lines)
