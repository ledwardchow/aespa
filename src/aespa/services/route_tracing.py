"""Bounded evidence-backed route tracing for campaign SAST leads."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from sqlmodel import Session, select

from aespa.models import ComponentConnection, ComponentFact, ScanLead
from aespa.services.scan_leads import decode_attack_path


@dataclass(frozen=True)
class TracePath:
    """One reverse-resolved path from a browser root to a SAST lead."""

    facts: tuple[ComponentFact, ...]
    edges: tuple[ComponentConnection, ...]
    complete: bool
    confidence: float
    proof_gaps: tuple[str, ...]

    @property
    def components(self) -> frozenset[int]:
        return frozenset(
            int(fact.component_id)
            for fact in self.facts
            if fact.component_id is not None
        )

    @property
    def key(self) -> str:
        material = "|".join(str(fact.fingerprint or fact.id) for fact in self.facts)
        return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _edge_kind(edge: ComponentConnection) -> str:
    return str(getattr(edge, "edge_kind", None) or "calls")


def _is_root(fact: ComponentFact) -> bool:
    return fact.fact_type in {"ui_route", "ui_action"}


def _is_frontend_call(fact: ComponentFact) -> bool:
    if fact.fact_type != "http_call":
        return False
    detail = _decode_detail(fact)
    return bool(
        detail.get("frontend") or detail.get("ui_route") or detail.get("trigger")
    )


def _decode_detail(fact: ComponentFact) -> dict:
    try:
        value = json.loads(fact.detail_json or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _has_valid_frontend_sequence(
    facts: tuple[ComponentFact, ...], edges: tuple[ComponentConnection, ...]
) -> bool:
    """Check that a complete path uses the expected UI-to-sink edge grammar."""
    if len(facts) != len(edges) + 1 or not facts:
        return False
    if facts[0].fact_type not in {"ui_route", "ui_action"}:
        return False
    if facts[-1].fact_type != "lead_anchor":
        return False
    for source, target, edge in zip(facts[:-1], facts[1:], edges, strict=True):
        kind = _edge_kind(edge)
        if "same source file" in str(getattr(edge, "rationale", "") or "").casefold():
            # Co-location is useful as a hint, but it is not proof that one
            # browser action calls one specific request or sink.
            return False
        allowed = (
            (
                kind == "contains"
                and source.fact_type == "ui_route"
                and target.fact_type == "ui_action"
            )
            or (
                kind == "triggers"
                and source.fact_type in {"ui_route", "ui_action"}
                and target.fact_type == "http_call"
            )
            or (
                kind == "calls"
                and source.fact_type == "http_call"
                and target.fact_type == "route"
            )
            or (
                kind == "dispatches"
                and source.fact_type in {"route", "handler"}
                and target.fact_type in {"route", "handler", "http_call"}
            )
            or (
                kind == "reaches"
                and source.fact_type in {"route", "handler"}
                and target.fact_type == "lead_anchor"
            )
        )
        if not allowed:
            return False
    return True


def _lead_anchor_facts(session: Session, lead: ScanLead) -> list[ComponentFact]:
    """Find facts that can anchor a lead without trusting a single file match."""
    facts = list(
        session.exec(
            select(ComponentFact).where(
                ComponentFact.sast_run_id == lead.producer_run_id
            )
        ).all()
    )
    location = (lead.location or "").strip()
    lead_anchors = [
        fact
        for fact in facts
        if fact.fact_type == "lead_anchor"
        and _decode_detail(fact).get("lead_id") == lead.id
    ]
    if lead_anchors:
        return lead_anchors
    exact = [
        fact
        for fact in facts
        if location
        and (
            fact.evidence_location == location
            or fact.evidence_location.split(":", 1)[0] == location.split(":", 1)[0]
        )
        and fact.fact_type in {"route", "handler", "lead_anchor", "http_call"}
    ]
    return exact or [
        fact
        for fact in facts
        if fact.fact_type in {"route", "handler", "lead_anchor"}
        and (
            not location
            or fact.evidence_location.split(":", 1)[0] == location.split(":", 1)[0]
        )
    ]


def trace_lead_paths(
    session: Session,
    campaign_id: int,
    lead: ScanLead,
    *,
    max_edges: int = 8,
    max_components: int = 6,
    max_paths: int = 10,
    min_confidence: float = 0.50,
) -> list[TracePath]:
    """Reverse traverse campaign connections from a lead to UI roots.

    The traversal is deliberately bounded and evidence-only. It also emits
    incomplete paths ending at a frontend HTTP call, allowing a reviewer to
    approve a useful but unresolved browser entrypoint.
    """
    if max_edges < 1 or max_components < 1 or max_paths < 1:
        return []

    connections = list(
        session.exec(
            select(ComponentConnection).where(
                ComponentConnection.campaign_id == campaign_id
            )
        ).all()
    )
    incoming: dict[int, list[ComponentConnection]] = {}
    fact_ids: set[int] = set()
    for edge in connections:
        if edge.source_fact_id is None or edge.target_fact_id is None:
            continue
        incoming.setdefault(edge.target_fact_id, []).append(edge)
        fact_ids.update((edge.source_fact_id, edge.target_fact_id))

    facts_by_id = {
        fact.id: fact
        for fact in session.exec(
            select(ComponentFact).where(ComponentFact.id.in_(fact_ids))
        ).all()
        if fact.id is not None
    }
    anchors = _lead_anchor_facts(session, lead)
    results: list[TracePath] = []
    seen: set[tuple[int, ...]] = set()

    def walk(
        current: ComponentFact,
        facts_reversed: tuple[ComponentFact, ...],
        edges_reversed: tuple[ComponentConnection, ...],
        gaps: tuple[str, ...],
    ) -> None:
        if _is_root(current):
            add_path(facts_reversed, edges_reversed, True, gaps)
            return
        if len(edges_reversed) >= max_edges:
            if _is_frontend_call(current):
                add_path(
                    facts_reversed,
                    edges_reversed,
                    False,
                    gaps + ("UI root not proven",),
                )
            return
        if _is_frontend_call(current) and not incoming.get(current.id or -1):
            add_path(
                facts_reversed, edges_reversed, False, gaps + ("UI root not proven",)
            )

        for edge in incoming.get(current.id or -1, []):
            source = facts_by_id.get(edge.source_fact_id)
            if source is None or source.id in {fact.id for fact in facts_reversed}:
                continue
            components = {
                int(fact.component_id)
                for fact in facts_reversed + (source,)
                if fact.component_id is not None
            }
            if len(components) > max_components:
                continue
            confidence = min(
                [float(edge.confidence or 0.0)]
                + [float(item.confidence or 1.0) for item in edges_reversed]
            )
            if confidence < min_confidence:
                continue
            walk(
                source,
                facts_reversed + (source,),
                edges_reversed + (edge,),
                gaps,
            )

    def add_path(
        facts_reversed: tuple[ComponentFact, ...],
        edges_reversed: tuple[ComponentConnection, ...],
        complete: bool,
        gaps: tuple[str, ...],
    ) -> None:
        facts = tuple(reversed(facts_reversed))
        edges = tuple(reversed(edges_reversed))
        key = tuple(int(fact.id) for fact in facts if fact.id is not None)
        if not key or key in seen:
            return
        if complete and not _has_valid_frontend_sequence(facts, edges):
            return
        seen.add(key)
        confidence = min(
            [float(lead.confidence or 0.0)]
            + [float(edge.confidence or 0.0) for edge in edges]
        )
        if confidence < min_confidence:
            return
        results.append(
            TracePath(
                facts=facts,
                edges=edges,
                complete=complete,
                confidence=confidence,
                proof_gaps=tuple(dict.fromkeys(gaps)),
            )
        )

    for anchor in anchors:
        walk(anchor, (anchor,), (), ())

    results.sort(
        key=lambda path: (
            not path.complete,
            -path.confidence,
            len(path.proof_gaps),
            len(path.edges),
            path.key,
        )
    )
    return results[:max_paths]


def attack_path_for_trace(
    path: TracePath,
    lead: ScanLead,
    *,
    origin_attack_path: dict | None = None,
) -> dict:
    """Convert a trace into the schema consumed by dynamic scan prompts."""
    first = path.facts[0] if path.facts else None
    request = next(
        (fact for fact in path.facts if fact.fact_type == "http_call"),
        None,
    )
    details = _decode_detail(first) if first else {}
    request_details = _decode_detail(request) if request else {}
    nodes = [
        " ".join(
            str(value)
            for value in (
                fact.method,
                fact.path or fact.name or fact.fact_type,
            )
            if value
        )
        for fact in path.facts
    ]
    proof_gaps = list(path.proof_gaps)
    entry = {
        "route": first.path if first and first.fact_type == "ui_route" else None,
        "action": details.get("label") or details.get("action"),
        "trigger": details.get("trigger") or details.get("action_kind"),
        "source_location": first.evidence_location if first else "",
    }
    dynamic_test = (
        f"From {entry['route'] or 'the frontend entrypoint'}, "
        f"{entry['action'] or 'reproduce the observed request'}, then verify "
        f"the vulnerable behavior through the traced request chain."
    )
    if request is not None:
        dynamic_test = (
            f"From {entry['route'] or 'the frontend entrypoint'}, "
            f"{entry['action'] or 'trigger the request'}, observe "
            f"{request.method or ''} {request.path or ''}, and safely vary only "
            "the evidence-backed input relevant to this lead."
        )
    pre_crawl = {
        "entry": entry["route"],
        "frontend_entrypoint": entry,
        "request_transition": {
            "method": request.method if request else None,
            "path": request.path if request else None,
            "mutation_points": request_details.get("body_fields", [])
            or request_details.get("query_fields", []),
        },
        "nodes": nodes[:20],
        "hops": [
            {
                "edge_kind": _edge_kind(edge),
                "source_fact_id": edge.source_fact_id,
                "target_fact_id": edge.target_fact_id,
                "confidence": edge.confidence,
            }
            for edge in path.edges
        ],
        "prerequisites": details.get("prerequisites", []),
        "mutation_points": request_details.get("body_fields", [])
        or request_details.get("query_fields", []),
        "proof_gaps": proof_gaps,
        "dynamic_test": dynamic_test,
    }
    return {
        "schema_version": 2,
        "perspective": "frontend",
        "path_status": "complete" if path.complete else "incomplete",
        "confidence": path.confidence,
        "live_frontend_context": {
            "resolution_status": "unresolved",
            "crawl_status": "not_started",
            "route": entry["route"],
            "action": entry["action"],
            "trigger": entry["trigger"],
            "evidence_ids": [],
        },
        "approved_pre_crawl_path": pre_crawl,
        "entry": entry["route"],
        "frontend_entrypoint": entry,
        "request_transition": pre_crawl["request_transition"],
        "nodes": pre_crawl["nodes"],
        "hops": pre_crawl["hops"],
        "prerequisites": pre_crawl["prerequisites"],
        "mutation_points": pre_crawl["mutation_points"],
        "proof_gaps": pre_crawl["proof_gaps"],
        "dynamic_test": pre_crawl["dynamic_test"],
        "origin_attack_path": origin_attack_path
        or decode_attack_path(lead.attack_path_json),
    }
