"""Cross-repository correlation for multi-repository campaigns.

Builds the campaign's "application map" (``ComponentConnection`` rows) from
the compact ``ComponentFact`` rows each source SAST run recorded, proposes
which live target should receive each SAST lead (``LeadTargetMapping``), and
— only when the evidence genuinely spans two components — creates a bounded
campaign-owned cross-repository ``ScanLead``.

Matching is deterministic first (hosts, HTTP method/path, auth markers, queue
identifiers, application hints). ``llm_match`` is an explicit, optional seam
for a bounded LLM pass over ambiguous cases; it defaults to ``None`` (no-op)
so tests never need network access, and production code can pass a bounded
callable later without touching this module's matching logic.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from datetime import datetime, timezone
from urllib.parse import urlparse

from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import (
    ApiCollection,
    ApiEndpoint,
    ApplicationTarget,
    CampaignSourceMember,
    CampaignTargetMember,
    ComponentConnection,
    ComponentFact,
    ComponentTargetHint,
    LeadTargetMapping,
    ScanLead,
    ScanLeadComponentProvenance,
    Site,
)
from aespa.services.scan_leads import copy_lead_to_run, lead_fingerprint, upsert_lead

_UTC = timezone.utc

# A connection needs at least a path match to be worth persisting.
_MIN_CONNECTION_SCORE = 0.5
# Only a well-evidenced connection can seed a new cross-repository lead.
_MIN_CROSS_LEAD_CONNECTION_SCORE = 0.7

LlmMatchFn = Callable[[list[dict]], list[dict]]


def _normalize_path(path: str) -> str:
    """Return a comparable request path.

    An outbound HTTP call fact may record an absolute URL
    (``https://api.acme.test/orders``) rather than a bare path
    (``/orders``); ``urlparse`` strips the scheme/host so the same path
    still matches a route fact regardless of which form was captured. Host
    evidence itself is never discarded here — callers keep it in the
    fact's/lead's separate ``host`` field for their own scoring.
    """
    raw = path or ""
    if "://" in raw:
        raw = urlparse(raw).path
    raw = raw.split("?", 1)[0].rstrip("/") or "/"
    raw = re.sub(r"\{[^}]+\}", "{}", raw)  # OpenAPI-style {id}
    raw = re.sub(r"/:[\w-]+", "/{}", raw)  # Express-style :id
    return raw.lower()


def _paths_match(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    return _normalize_path(a) == _normalize_path(b)


def _host_of(value: str | None) -> str | None:
    if not value:
        return None
    if "://" in value:
        return (urlparse(value).hostname or "").lower() or None
    return None


def _extract_method_path(text: str) -> tuple[str | None, str | None]:
    """Best-effort ``METHOD /path`` extraction from a lead's endpoint/location."""
    match = re.search(
        r"\b(GET|POST|PUT|PATCH|DELETE)\b\s+(/[^\s\"']*)", text or "", re.IGNORECASE
    )
    if match:
        return match.group(1).upper(), match.group(2)
    path_match = re.search(r"(/[\w\-/{}.:]+)", text or "")
    return None, path_match.group(1) if path_match else None


def _score_call_to_route(
    call: ComponentFact, route: ComponentFact
) -> tuple[float, str, dict]:
    score = 0.0
    parts: list[str] = []
    if call.method and route.method and call.method.upper() == route.method.upper():
        score += 0.3
        parts.append("HTTP method matches")
    if _paths_match(call.path, route.path):
        score += 0.5
        parts.append("route path matches the outbound call")
    if score <= 0:
        return 0.0, "", {}
    return (
        min(score, 1.0),
        "; ".join(parts),
        {
            "call": {"method": call.method, "path": call.path, "host": call.host},
            "route": {"method": route.method, "path": route.path},
        },
    )


def _build_component_connections(
    session: Session,
    campaign_id: int,
    members: list[CampaignSourceMember],
    llm_match: LlmMatchFn | None,
) -> list[ComponentConnection]:
    """Persist deterministic (and optionally LLM-assisted) component edges.

    Facts are scoped to each member's own ``sast_run_id`` — the exact SastRun
    this campaign spawned for that component's frozen snapshot — never to
    every historical ``ComponentFact`` a component has ever produced across
    other campaigns/snapshots.
    """
    facts_by_component: dict[int, list[ComponentFact]] = {}
    for member in members:
        if member.sast_run_id is None:
            facts_by_component.setdefault(member.component_id, [])
            continue
        facts_by_component[member.component_id] = list(
            session.exec(
                select(ComponentFact).where(
                    ComponentFact.sast_run_id == member.sast_run_id
                )
            ).all()
        )

    # Replace any previously computed connections for this campaign so a
    # rerun of correlation reflects the current fact set rather than
    # accumulating stale edges.
    for existing in session.exec(
        select(ComponentConnection).where(
            ComponentConnection.campaign_id == campaign_id
        )
    ).all():
        session.delete(existing)
    session.flush()

    connections: list[ComponentConnection] = []
    component_ids = list(facts_by_component.keys())
    for source_component_id in component_ids:
        calls = [
            f
            for f in facts_by_component[source_component_id]
            if f.fact_type == "http_call"
        ]
        if not calls:
            continue
        for target_component_id in component_ids:
            if target_component_id == source_component_id:
                continue
            routes = [
                f
                for f in facts_by_component[target_component_id]
                if f.fact_type == "route"
            ]
            unmatched_calls: list[ComponentFact] = []
            for call in calls:
                best: tuple[float, str, dict, ComponentFact] | None = None
                for route in routes:
                    score, rationale, evidence = _score_call_to_route(call, route)
                    if score < _MIN_CONNECTION_SCORE:
                        continue
                    if best is None or score > best[0]:
                        best = (score, rationale, evidence, route)
                if best is not None:
                    score, rationale, evidence, route = best
                    connection = ComponentConnection(
                        campaign_id=campaign_id,
                        source_component_id=source_component_id,
                        source_fact_id=call.id,
                        target_component_id=target_component_id,
                        target_fact_id=route.id,
                        match_kind="deterministic",
                        confidence=score,
                        rationale=rationale,
                        evidence_json=json.dumps(evidence),
                    )
                    session.add(connection)
                    connections.append(connection)
                else:
                    unmatched_calls.append(call)

            if llm_match is not None and unmatched_calls:
                # Bounded, explicit LLM-assisted seam: only invoked for calls a
                # deterministic pass could not resolve, and only receives the
                # short fact summaries (never source code).
                ambiguous = [
                    {
                        "call": {
                            "id": c.id,
                            "method": c.method,
                            "path": c.path,
                            "host": c.host,
                        },
                        "candidate_routes": [
                            {"id": r.id, "method": r.method, "path": r.path}
                            for r in routes
                        ],
                    }
                    for c in unmatched_calls
                ]
                for result in llm_match(ambiguous) or []:
                    call_id = result.get("call_id")
                    route_id = result.get("route_id")
                    confidence = float(result.get("confidence", 0.0))
                    if not call_id or not route_id or confidence <= 0:
                        continue
                    connection = ComponentConnection(
                        campaign_id=campaign_id,
                        source_component_id=source_component_id,
                        source_fact_id=call_id,
                        target_component_id=target_component_id,
                        target_fact_id=route_id,
                        match_kind="llm_assisted",
                        confidence=min(confidence, 1.0),
                        rationale=str(result.get("rationale", "")),
                        evidence_json=json.dumps(result.get("evidence", {})),
                    )
                    session.add(connection)
                    connections.append(connection)

    session.flush()
    return connections


def _same_file(location_a: str, location_b: str) -> bool:
    return (location_a or "").split(":")[0] == (location_b or "").split(":")[0]


def _generate_cross_component_leads(
    session: Session, campaign_id: int, connections: list[ComponentConnection]
) -> list[ScanLead]:
    """Create a campaign-owned lead only when two components' evidence
    genuinely combines into a new hypothesis: a reportable lead at the exact
    outbound-call site, reaching a route with no recorded auth boundary."""
    created: list[ScanLead] = []
    for connection in connections:
        if connection.confidence < _MIN_CROSS_LEAD_CONNECTION_SCORE:
            continue
        source_fact = session.get(ComponentFact, connection.source_fact_id)
        target_fact = session.get(ComponentFact, connection.target_fact_id)
        if source_fact is None or target_fact is None:
            continue

        source_lead = session.exec(
            select(ScanLead)
            .where(ScanLead.producer_run_id == source_fact.sast_run_id)
            .where(ScanLead.producer_run_type == "sast")
            .where(ScanLead.imported_into_run_id == None)  # noqa: E711
            .where(ScanLead.reportable == True)  # noqa: E712
            .where(ScanLead.location == source_fact.evidence_location)
        ).first()
        if source_lead is None:
            continue

        target_auth_facts = session.exec(
            select(ComponentFact)
            .where(ComponentFact.sast_run_id == target_fact.sast_run_id)
            .where(ComponentFact.fact_type == "auth_boundary")
        ).all()
        if any(
            _same_file(fact.evidence_location, target_fact.evidence_location)
            for fact in target_auth_facts
        ):
            continue  # the receiving route already has a recorded auth boundary

        fingerprint = lead_fingerprint(
            category=source_lead.category,
            title=f"cross-repo:{source_lead.title}",
            location=f"{source_fact.evidence_location}->{target_fact.evidence_location}",
        )
        lead = upsert_lead(
            session,
            producer_run_id=campaign_id,
            producer_run_type="campaign",
            title=(
                f"Cross-repository: {source_lead.title} reaches an "
                f"unauthenticated {target_fact.method or ''} {target_fact.path or target_fact.name or ''}".strip()
            ),
            description=(
                f"{source_lead.description}\n\nThis call site is connected "
                "(deterministic route/method match) to a route in another "
                "repository that has no recorded authentication boundary."
            ),
            category=source_lead.category,
            severity=source_lead.severity,
            confidence=min(source_lead.confidence, connection.confidence),
            location=f"{source_fact.evidence_location} -> {target_fact.evidence_location}",
            evidence=(
                f"Outbound call: {source_fact.method} {source_fact.path} "
                f"({source_fact.evidence_location})\n"
                f"Matched route: {target_fact.method} {target_fact.path} "
                f"({target_fact.evidence_location})\n{source_lead.evidence}"
            ),
            source="campaign",
            fingerprint=fingerprint,
            # The receiving route is the live endpoint that would actually
            # be probed — set it so lead-target scoring can match it against
            # a campaign target's parsed ApiEndpoint rows, same as any other
            # lead.
            suggested_endpoint=f"{target_fact.method or ''} {target_fact.path or ''}".strip(),
            validation_status="pending",
            reportable=True,
        )
        created.append(lead)

        for component_id, role, fact_id in (
            (connection.source_component_id, "primary", source_fact.id),
            (connection.target_component_id, "contributing", target_fact.id),
        ):
            existing = session.exec(
                select(ScanLeadComponentProvenance)
                .where(ScanLeadComponentProvenance.scan_lead_id == lead.id)
                .where(ScanLeadComponentProvenance.component_id == component_id)
            ).first()
            if existing is not None:
                continue
            session.add(
                ScanLeadComponentProvenance(
                    scan_lead_id=lead.id,
                    component_id=component_id,
                    role=role,
                    fact_id=fact_id,
                )
            )
    session.flush()
    return created


def _target_host(session: Session, target: ApplicationTarget) -> str | None:
    if target.target_type == "site":
        site = session.get(Site, target.target_id)
        return _host_of(site.base_url) if site else None
    collection = session.get(ApiCollection, target.target_id)
    return _host_of(collection.base_url) if collection else None


def _score_lead_target(
    session: Session, lead: ScanLead, component_id: int, target: ApplicationTarget
) -> tuple[float, str, dict]:
    score = 0.0
    parts: list[str] = []
    evidence: dict = {}

    hint = session.exec(
        select(ComponentTargetHint)
        .where(ComponentTargetHint.component_id == component_id)
        .where(ComponentTargetHint.target_id == target.id)
    ).first()
    if hint is not None:
        score += 0.6
        parts.append("Direct hint linking this component to this target")
        evidence["hint"] = hint.note or "component-target hint"

    lead_host = _host_of(lead.suggested_endpoint) or _host_of(lead.location)
    target_host = _target_host(session, target)
    if lead_host and target_host and lead_host == target_host:
        score += 0.2
        parts.append("Host matches the target's base URL")
        evidence["host"] = target_host

    method, path = _extract_method_path(lead.suggested_endpoint or lead.location)
    if target.target_type == "api_collection" and path:
        endpoints = session.exec(
            select(ApiEndpoint).where(ApiEndpoint.collection_id == target.target_id)
        ).all()
        for endpoint in endpoints:
            if _paths_match(endpoint.path, path) and (
                not method or endpoint.method.upper() == method.upper()
            ):
                score += 0.3
                parts.append(
                    "Exact method/path match against the target's parsed endpoints"
                )
                evidence["endpoint"] = f"{endpoint.method} {endpoint.path}"
                break

    if score <= 0:
        return 0.0, "", {}
    return min(score, 1.0), "; ".join(parts), evidence


def _best_score_across_components(
    session: Session,
    lead: ScanLead,
    component_ids: set[int],
    target: ApplicationTarget,
) -> tuple[float, str, dict]:
    """Score a lead against a target once per candidate component and keep
    the strongest match (a cross-repo lead has more than one contributing
    component; a single-component lead has exactly one)."""
    best: tuple[float, str, dict] = (0.0, "", {})
    for component_id in component_ids:
        score, rationale, evidence = _score_lead_target(
            session, lead, component_id, target
        )
        if score > best[0]:
            best = (score, rationale, evidence)
    return best


def _propose_mappings_for_lead(
    session: Session,
    campaign_id: int,
    lead: ScanLead,
    component_ids: set[int],
    targets: list[ApplicationTarget],
    mappings: list[LeadTargetMapping],
) -> None:
    for target in targets:
        score, rationale, evidence = _best_score_across_components(
            session, lead, component_ids, target
        )
        if score <= 0:
            continue
        already = session.exec(
            select(LeadTargetMapping)
            .where(LeadTargetMapping.campaign_id == campaign_id)
            .where(LeadTargetMapping.lead_id == lead.id)
            .where(LeadTargetMapping.target_id == target.id)
        ).first()
        if already is not None:
            continue  # a reviewed mapping already exists — keep it
        mapping = LeadTargetMapping(
            campaign_id=campaign_id,
            lead_id=lead.id,
            target_id=target.id,
            target_type=target.target_type,
            score=score,
            rationale=rationale,
            evidence_json=json.dumps(evidence),
            status="proposed",
        )
        session.add(mapping)
        mappings.append(mapping)


def _propose_lead_target_mappings(
    session: Session,
    campaign_id: int,
    source_members: list[CampaignSourceMember],
    target_members: list[CampaignTargetMember],
) -> list[LeadTargetMapping]:
    targets = [session.get(ApplicationTarget, tm.target_id) for tm in target_members]
    targets = [t for t in targets if t is not None]

    # Replace stale proposals for leads that are still only "proposed" so a
    # rerun of correlation does not duplicate rows; already-reviewed mappings
    # (approved/rejected) are left untouched.
    for existing in session.exec(
        select(LeadTargetMapping)
        .where(LeadTargetMapping.campaign_id == campaign_id)
        .where(LeadTargetMapping.status == "proposed")
    ).all():
        session.delete(existing)
    session.flush()

    mappings: list[LeadTargetMapping] = []
    for member in source_members:
        if not member.sast_run_id:
            continue
        leads = session.exec(
            select(ScanLead)
            .where(ScanLead.producer_run_id == member.sast_run_id)
            .where(ScanLead.producer_run_type == "sast")
            .where(ScanLead.imported_into_run_id == None)  # noqa: E711
            .where(ScanLead.reportable == True)  # noqa: E712
        ).all()
        for lead in leads:
            _propose_mappings_for_lead(
                session, campaign_id, lead, {member.component_id}, targets, mappings
            )

    # Campaign-owned cross-repository leads are eligible for the exact same
    # review/approve/copy pipeline as any other lead — score them against
    # every contributing component's evidence (primary + contributing from
    # ScanLeadComponentProvenance) and keep the strongest match per target.
    cross_leads = session.exec(
        select(ScanLead)
        .where(ScanLead.producer_run_type == "campaign")
        .where(ScanLead.producer_run_id == campaign_id)
        .where(ScanLead.imported_into_run_id == None)  # noqa: E711
        .where(ScanLead.reportable == True)  # noqa: E712
    ).all()
    for lead in cross_leads:
        provenance_rows = session.exec(
            select(ScanLeadComponentProvenance).where(
                ScanLeadComponentProvenance.scan_lead_id == lead.id
            )
        ).all()
        component_ids = {row.component_id for row in provenance_rows}
        if not component_ids:
            continue
        _propose_mappings_for_lead(
            session, campaign_id, lead, component_ids, targets, mappings
        )

    session.flush()
    return mappings


def correlate_campaign(
    campaign_id: int, *, llm_match: LlmMatchFn | None = None
) -> dict:
    """Build the application map and lead-target proposals for one campaign.

    Deterministic only unless ``llm_match`` is supplied — tests never pass it,
    so this function never performs network I/O.
    """
    with Session(get_engine()) as session:
        source_members = list(
            session.exec(
                select(CampaignSourceMember).where(
                    CampaignSourceMember.campaign_id == campaign_id
                )
            ).all()
        )
        target_members = list(
            session.exec(
                select(CampaignTargetMember).where(
                    CampaignTargetMember.campaign_id == campaign_id
                )
            ).all()
        )
        connections = _build_component_connections(
            session, campaign_id, source_members, llm_match
        )
        cross_leads = _generate_cross_component_leads(session, campaign_id, connections)
        mappings = _propose_lead_target_mappings(
            session, campaign_id, source_members, target_members
        )
        session.commit()
        return {
            "connections": len(connections),
            "cross_component_leads": len(cross_leads),
            "lead_target_mappings": len(mappings),
        }


def count_pending_mappings(campaign_id: int) -> int:
    """Return how many of a campaign's lead-target proposals are undecided."""
    with Session(get_engine()) as session:
        return len(
            session.exec(
                select(LeadTargetMapping.id)
                .where(LeadTargetMapping.campaign_id == campaign_id)
                .where(LeadTargetMapping.status == "proposed")
            ).all()
        )


class UnknownMappingError(Exception):
    """Raised when a review decision references a mapping id that does not
    exist, or belongs to a different campaign."""


def apply_review_decisions(campaign_id: int, decisions: list[tuple[int, bool]]) -> dict:
    """Idempotently approve/reject lead-target mappings.

    Every ``mapping_id`` must already belong to this campaign — an unknown or
    foreign id raises ``UnknownMappingError`` and applies *none* of the
    decisions in the batch (validated up front, before any row is touched).

    Approving never copies a lead here — copying happens once the exact child
    dynamic run exists, in ``copy_approved_mappings_for_target``. Rejecting a
    mapping that was previously copied clears the recorded copy id, but the
    already-copied ``ScanLead`` row itself is left for the child run's own
    cascade-delete to clean up (avoids racing a scan that may be reading it).
    """
    approved = 0
    rejected = 0
    now = datetime.now(_UTC)
    with Session(get_engine()) as session:
        resolved: list[tuple[LeadTargetMapping, bool]] = []
        for mapping_id, approve in decisions:
            mapping = session.get(LeadTargetMapping, mapping_id)
            if mapping is None or mapping.campaign_id != campaign_id:
                raise UnknownMappingError(
                    f"Mapping id={mapping_id} does not belong to this campaign"
                )
            resolved.append((mapping, approve))

        for mapping, approve in resolved:
            new_status = "approved" if approve else "rejected"
            if mapping.status != new_status:
                mapping.status = new_status
                if approve:
                    approved += 1
                else:
                    rejected += 1
            mapping.reviewed_at = now
            mapping.updated_at = now
            session.add(mapping)
        session.commit()
    return {"approved": approved, "rejected": rejected}


def copy_approved_mappings_for_target(
    campaign_id: int, target_id: int, run_type: str, run_id: int
) -> int:
    """Copy every approved mapping for one target into its exact child run.

    Idempotent: ``copy_lead_to_run`` itself dedupes by fingerprint, and this
    only ever (re)writes ``copied_lead_id`` — safe to call more than once.
    """
    copied = 0
    with Session(get_engine()) as session:
        mappings = session.exec(
            select(LeadTargetMapping)
            .where(LeadTargetMapping.campaign_id == campaign_id)
            .where(LeadTargetMapping.target_id == target_id)
            .where(LeadTargetMapping.status == "approved")
        ).all()
        pending = [(m.id, m.lead_id) for m in mappings]
    for mapping_id, lead_id in pending:
        try:
            copy = copy_lead_to_run(lead_id, run_type, run_id)
        except ValueError:
            continue  # lead no longer eligible (e.g. dismissed) — skip it
        with Session(get_engine()) as session:
            mapping = session.get(LeadTargetMapping, mapping_id)
            if mapping is not None:
                mapping.copied_lead_id = copy.id
                mapping.updated_at = datetime.now(_UTC)
                session.add(mapping)
                session.commit()
        copied += 1
    return copied
