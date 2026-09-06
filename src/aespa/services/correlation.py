"""Cross-repository correlation for multi-repository campaigns.

Builds the campaign's "application map" (``ComponentConnection`` rows) from
the compact ``ComponentFact`` rows each source SAST run recorded, proposes
which live target should receive each SAST lead (``LeadTargetMapping``), and
— only when the evidence genuinely spans two components — creates a bounded
campaign-owned cross-repository ``ScanLead``.

Matching is deterministic first (hosts, HTTP method/path, auth markers, queue
identifiers, application hints). Production correlation then uses a bounded
LLM pass over unresolved, already-extracted facts. The synchronous
``correlate_campaign`` function remains deterministic for unit tests.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse

from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import (
    ApiCollection,
    ApiEndpoint,
    ApplicationComponent,
    ApplicationTarget,
    AssessmentCampaign,
    CampaignSourceMember,
    CampaignTargetMember,
    ComponentConnection,
    ComponentFact,
    ComponentMapperConfig,
    ComponentTargetHint,
    LeadTargetMapping,
    SastRun,
    ScanLead,
    ScanLeadComponentProvenance,
    Site,
)
from aespa.services import events as events_svc
from aespa.services.campaign_mapping_quality import (
    canonical_path_identity,
    complete_path_can_map_to_site,
)
from aespa.services.component_facts import request_role_for_fact
from aespa.services.frontend_path_resolver import (
    is_frontend_path,
    resolve_approved_path,
    revise_path_with_llm,
)
from aespa.services.references import ensure_lead_reference
from aespa.services.route_tracing import attack_path_for_trace, trace_lead_paths
from aespa.services.scan_leads import (
    copy_lead_to_run,
    lead_fingerprint,
    prepend_frontend_context_to_copied_lead,
    set_final_frontend_path,
    upsert_lead,
)

_UTC = timezone.utc

# A connection needs at least a path match to be worth persisting.
_MIN_CONNECTION_SCORE = 0.5
# Only a well-evidenced connection can seed a new cross-repository lead.
_MIN_CROSS_LEAD_CONNECTION_SCORE = 0.7


def _make_connection(
    *,
    campaign_id: int,
    source: ComponentFact,
    target: ComponentFact,
    match_kind: str,
    confidence: float,
    rationale: str,
    evidence: dict,
    edge_kind: str = "calls",
) -> ComponentConnection:
    """Construct a graph edge while tolerating legacy model rows during upgrade."""
    connection = ComponentConnection(
        campaign_id=campaign_id,
        source_component_id=source.component_id or 0,
        source_fact_id=source.id,
        target_component_id=target.component_id or 0,
        target_fact_id=target.id,
        match_kind=match_kind,
        confidence=confidence,
        rationale=rationale,
        evidence_json=json.dumps(evidence),
    )
    for name, value in (
        ("edge_kind", edge_kind),
        ("source_sast_run_id", source.sast_run_id),
        ("target_sast_run_id", target.sast_run_id),
        (
            "path_scope",
            "internal"
            if source.component_id == target.component_id
            else "cross_component",
        ),
    ):
        if hasattr(connection, name):
            setattr(connection, name, value)
    return connection


@dataclass(frozen=True)
class AmbiguousCall:
    call: ComponentFact
    target_component_id: int
    candidate_routes: tuple[ComponentFact, ...]


@dataclass(frozen=True)
class ConnectionProposal:
    call_id: int
    route_id: int
    confidence: float
    rationale: str
    evidence: dict


@dataclass(frozen=True)
class RouteAccess:
    kind: str
    confidence: float
    authentication: dict | None = None


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


def _path_pattern_matches(pattern: str | None, path: str | None) -> bool:
    """Match a small set of common route-prefix patterns."""
    if not pattern or not path:
        return False
    normalized_pattern = _normalize_path(pattern)
    normalized_path = _normalize_path(path)
    if normalized_pattern in {"", "*", "/**"}:
        return True
    if normalized_pattern.endswith("/**"):
        prefix = normalized_pattern[:-3].rstrip("/") or "/"
        return normalized_path == prefix or normalized_path.startswith(prefix + "/")
    if normalized_pattern.endswith("/*"):
        prefix = normalized_pattern[:-2].rstrip("/") or "/"
        return normalized_path == prefix or normalized_path.startswith(prefix + "/")
    return normalized_pattern == normalized_path


def _auth_boundary_state(session: Session, route: ComponentFact) -> str:
    """Return ``public``, ``protected``, or ``unknown`` for one route.

    Older facts only contain a file location. Those remain useful as local
    protection evidence, but absence of a same-file marker is deliberately not
    treated as proof that a route is public.
    """
    facts = session.exec(
        select(ComponentFact)
        .where(ComponentFact.sast_run_id == route.sast_run_id)
        .where(ComponentFact.fact_type == "auth_boundary")
    ).all()
    route_method = (route.method or "").upper()
    has_protected_match = False

    for fact in facts:
        detail = _fact_detail(fact)
        public_paths = detail.get("public_paths")
        if isinstance(public_paths, str):
            public_paths = [public_paths]
        public_methods = detail.get("public_methods")
        if isinstance(public_methods, str):
            public_methods = [public_methods]
        if isinstance(public_paths, list) and any(
            _path_pattern_matches(str(pattern), route.path)
            and (
                not public_methods
                or route_method in {str(method).upper() for method in public_methods}
            )
            for pattern in public_paths
        ):
            return "public"

        protected_paths = detail.get("protected_paths")
        if isinstance(protected_paths, str):
            protected_paths = [protected_paths]
        if detail.get("scope") == "global" and isinstance(protected_paths, list):
            if any(
                _path_pattern_matches(str(pattern), route.path)
                for pattern in protected_paths
            ):
                has_protected_match = True
        elif detail.get("scope") in {None, "local"} and _same_evidence_file(
            fact, route
        ):
            has_protected_match = True

    return "protected" if has_protected_match else "unknown"


def _fact_identity(fact: ComponentFact) -> tuple[str, str, str]:
    """Return a semantic method/path/host identity for a fact."""
    host = _host_of(fact.host) or (fact.host or "").strip().lower()
    return (
        (fact.method or "").upper(),
        _normalize_path(fact.path),
        host,
    )


def _connection_identity(
    source_component_id: int,
    target_component_id: int,
    source: ComponentFact,
    target: ComponentFact,
) -> tuple[int, int, tuple[str, str, str], tuple[str, str, str]]:
    """Identify one semantic cross-component endpoint pair."""
    return (
        source_component_id,
        target_component_id,
        _fact_identity(source),
        _fact_identity(target),
    )


def _cross_repo_lead_fingerprint(
    *,
    category: str,
    origin_fingerprint: str,
    source_component_id: int,
    target_component_id: int,
    backend_case: bool = False,
) -> str:
    """Identify one cross-repo root cause across all matched endpoints."""
    semantic_location = "|".join(
        (
            origin_fingerprint,
            str(source_component_id),
            str(target_component_id),
            "backend" if backend_case else "source",
        )
    )
    return lead_fingerprint(
        category=category,
        title="cross-repository",
        location=semantic_location,
    )


def _cross_repo_attack_path(
    *,
    existing: dict,
    source_fact: ComponentFact,
    target_fact: ComponentFact,
    connection: ComponentConnection,
    source_component_name: str,
    target_component_name: str,
    vulnerability: ScanLead,
    backend_case: bool,
    access: RouteAccess,
) -> dict:
    """Keep one root path while retaining every matched endpoint instance."""
    path = deepcopy(existing) if isinstance(existing, dict) else {}
    path.setdefault(
        "frontend_entrypoint",
        {
            "component_id": connection.source_component_id,
            "component_name": source_component_name,
            "location": source_fact.evidence_location,
            "method": source_fact.method,
            "path": source_fact.path,
            "host": source_fact.host,
        },
    )
    path.setdefault(
        "backend_route",
        {
            "component_id": connection.target_component_id,
            "component_name": target_component_name,
            "location": target_fact.evidence_location,
            "method": target_fact.method,
            "path": target_fact.path,
        },
    )
    path.setdefault(
        "vulnerability",
        {
            "lead_id": vulnerability.id,
            "category": vulnerability.category,
            "severity": vulnerability.severity,
            "title": vulnerability.title,
            "description": vulnerability.description,
            "evidence": vulnerability.evidence,
        },
    )
    instances = path.get("instances")
    if not isinstance(instances, list):
        instances = []
    instance = {
        "case": "backend" if backend_case else "source",
        "source_component_id": connection.source_component_id,
        "source_fact_id": source_fact.id,
        "source_location": source_fact.evidence_location,
        "source_method": source_fact.method,
        "source_path": source_fact.path,
        "source_host": source_fact.host,
        "target_component_id": connection.target_component_id,
        "target_fact_id": target_fact.id,
        "target_location": target_fact.evidence_location,
        "target_method": target_fact.method,
        "target_path": target_fact.path,
        "access": access.kind,
        "confidence": access.confidence,
    }
    if access.authentication is not None:
        instance["authentication"] = deepcopy(access.authentication)
    instance_key = (
        instance["case"],
        instance["source_location"],
        instance["source_method"],
        instance["source_path"],
        instance["target_location"],
        instance["target_method"],
        instance["target_path"],
    )
    existing_index = next(
        (
            index
            for index, item in enumerate(instances)
            if isinstance(item, dict)
            and (
                item.get("case"),
                item.get("source_location"),
                item.get("source_method"),
                item.get("source_path"),
                item.get("target_location"),
                item.get("target_method"),
                item.get("target_path"),
            )
            == instance_key
        ),
        None,
    )
    if existing_index is None:
        instances.append(instance)
    else:
        instances[existing_index] = {**instances[existing_index], **instance}
    path["instances"] = instances[:64]
    return path


def _load_cross_repo_attack_path(
    session: Session,
    *,
    campaign_id: int,
    fingerprint: str,
    base: dict,
    source_fact: ComponentFact,
    target_fact: ComponentFact,
    connection: ComponentConnection,
    source_component_name: str,
    target_component_name: str,
    vulnerability: ScanLead,
    backend_case: bool,
    access: RouteAccess,
) -> dict:
    """Load an existing root path before adding another endpoint instance."""
    existing = session.exec(
        select(ScanLead)
        .where(ScanLead.producer_run_id == campaign_id)
        .where(ScanLead.producer_run_type == "campaign")
        .where(ScanLead.imported_into_run_id == None)  # noqa: E711
        .where(ScanLead.fingerprint == fingerprint)
    ).first()
    current: dict = {}
    if existing is not None:
        try:
            decoded = json.loads(existing.attack_path_json or "{}")
        except (TypeError, json.JSONDecodeError):
            decoded = {}
        if isinstance(decoded, dict):
            current = decoded
    if not current:
        current = deepcopy(base)
    return _cross_repo_attack_path(
        existing=current,
        source_fact=source_fact,
        target_fact=target_fact,
        connection=connection,
        source_component_name=source_component_name,
        target_component_name=target_component_name,
        vulnerability=vulnerability,
        backend_case=backend_case,
        access=access,
    )


def _cross_repo_suggested_endpoint(attack_path: dict) -> str:
    """Return one representative endpoint for target matching and display."""
    instances = attack_path.get("instances")
    if isinstance(instances, list):
        for instance in instances:
            if not isinstance(instance, dict):
                continue
            method = instance.get("target_method") or ""
            path = instance.get("target_path") or ""
            if method or path:
                return f"{method} {path}".strip()
    route = attack_path.get("backend_route")
    if isinstance(route, dict):
        return f"{route.get('method') or ''} {route.get('path') or ''}".strip()
    return ""


def _attack_path_has_authenticated_access(attack_path: dict) -> bool:
    instances = attack_path.get("instances")
    return isinstance(instances, list) and any(
        isinstance(instance, dict) and instance.get("access") == "authenticated"
        for instance in instances
    )


def _route_access_evidence(access: RouteAccess) -> str:
    if access.authentication is None:
        return "Target route is explicitly public"
    acquisition = access.authentication.get("acquisition") or {}
    return (
        "Target route is reachable with a credential acquired through "
        f"{acquisition.get('method') or ''} {acquisition.get('path') or ''} "
        f"({acquisition.get('source_location') or 'unknown source'})"
    ).strip()


def _fact_evidence(fact: ComponentFact) -> dict:
    try:
        detail = json.loads(fact.detail_json or "{}")
    except (TypeError, ValueError):
        detail = {}
    supporting = detail.get("supporting_locations")
    return {
        "evidence_location": fact.evidence_location,
        "supporting_locations": supporting if isinstance(supporting, list) else [],
    }


def _fact_detail(fact: ComponentFact) -> dict:
    try:
        value = json.loads(fact.detail_json or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _request_role(fact: ComponentFact) -> str | None:
    """Resolve the role of a request fact without trusting malformed detail."""
    try:
        return request_role_for_fact(fact.fact_type, _fact_detail(fact))
    except ValueError:
        return None


def _infer_owned_server_egress(
    session: Session,
    call: ComponentFact,
    ingress_routes: list[ComponentFact],
) -> str | None:
    """Infer a missing egress role from an explicit route-to-call relation.

    LLM mapper facts sometimes describe a proxy call in ``supporting_locations``
    without repeating ``request_role``.  A location link from exactly one
    server route to the call is enough to classify it.  The one-owner rule is
    deliberate: a shared helper or a broad file-level summary must not turn
    every request in a component into a proxy hop.
    """
    role = _request_role(call)
    if role is not None or call.fact_type != "http_call":
        return role
    owners = [route for route in ingress_routes if _detail_connects(route, call)]
    if len(owners) != 1:
        return None
    route = owners[0]
    detail = _fact_detail(call)
    detail["request_role"] = "server_egress"
    detail["request_role_inferred"] = True
    detail["role_evidence"] = [route.evidence_location]
    call.detail_json = json.dumps(detail, separators=(",", ":"))
    session.add(call)
    return "server_egress"


def _unique_route_facts(routes: list[ComponentFact]) -> list[ComponentFact]:
    """Drop duplicate route observations while retaining every route shape."""
    seen: set[tuple[str, str, str]] = set()
    unique: list[ComponentFact] = []
    for route in sorted(routes, key=lambda fact: fact.id or 0):
        key = (
            (route.method or "").upper(),
            _normalize_path(route.path or ""),
            route.host or "",
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(route)
    return unique


def _detail_locations(fact: ComponentFact) -> set[str]:
    detail = _fact_detail(fact)
    locations: set[str] = set()
    for key in (
        "supporting_locations",
        "trigger_locations",
        "handler_locations",
        "route_locations",
        "source_locations",
        "related_locations",
        "acquisition_call_locations",
        "credential_use_locations",
    ):
        values = detail.get(key)
        if isinstance(values, str):
            values = [values]
        if isinstance(values, list):
            locations.update(str(value) for value in values if value)
    for key in ("handler_location", "route_location", "source_location"):
        value = detail.get(key)
        if value:
            locations.add(str(value))
    return locations


def _detail_connects(source: ComponentFact, target: ComponentFact) -> bool:
    return bool(
        source.evidence_location in _detail_locations(target)
        or target.evidence_location in _detail_locations(source)
    )


def _semantic_connection(
    source: ComponentFact,
    target: ComponentFact,
    *,
    allowed_source_types: set[str],
    allowed_target_types: set[str],
) -> bool:
    """Return true only when mapper metadata names both constructs.

    A component and a source file are useful scopes for searching, but they
    do not establish a call relationship.  The mapper records the locations
    it used to prove a relationship in the fact detail, so all intra-source
    graph edges go through this check.
    """
    return (
        source.fact_type in allowed_source_types
        and target.fact_type in allowed_target_types
        and bool(source.evidence_location)
        and bool(target.evidence_location)
        and _detail_connects(source, target)
    )


def _ui_route_action_connection(
    route: ComponentFact,
    action: ComponentFact,
    routes: list[ComponentFact],
) -> bool:
    """Require a route/action binding to identify one route unambiguously."""
    route_detail = _fact_detail(route)
    action_detail = _fact_detail(action)
    action_location = action.evidence_location
    explicit_action_locations = set()
    for key in ("action_locations", "trigger_locations"):
        values = route_detail.get(key) or []
        if isinstance(values, str):
            values = [values]
        if isinstance(values, list):
            explicit_action_locations.update(str(value) for value in values)
    if action_location in explicit_action_locations:
        return True

    route_locations = action_detail.get("route_locations") or []
    if isinstance(route_locations, str):
        route_locations = [route_locations]
    if (
        not isinstance(route_locations, list)
        or route.evidence_location not in route_locations
    ):
        return False
    candidates = {
        candidate.evidence_location
        for candidate in routes
        if candidate.evidence_location in route_locations
    }
    # A file-level analyzer may attach every route location to every action.
    # Treat that as context until one route is named explicitly.
    return len(candidates) == 1


def _ui_action_call_connection(
    action: ComponentFact,
    call: ComponentFact,
) -> bool:
    """Require an action to own the browser request it triggers.

    Supporting locations often contain shared helpers used by several UI
    actions.  They are useful context, but cannot identify which action owns a
    request.  Prefer the function locations recorded on both facts, with an
    exact source location as the compatibility path for server-rendered forms.
    """
    if call.fact_type != "http_call" or _request_role(call) != "browser_request":
        return False

    def locations(fact: ComponentFact, *keys: str) -> set[str]:
        detail = _fact_detail(fact)
        result: set[str] = set()
        for key in keys:
            values = detail.get(key)
            if isinstance(values, str):
                values = [values]
            if isinstance(values, list):
                result.update(str(value) for value in values if value)
        return result

    action_handlers = locations(action, "handler_locations", "handler_location")
    call_handlers = locations(call, "handler_locations", "handler_location")
    if action_handlers & call_handlers:
        return True
    if action.evidence_location and action.evidence_location == call.evidence_location:
        return True
    return bool(
        action.evidence_location in call_handlers
        or call.evidence_location in action_handlers
    )


def _detail_location_set(fact: ComponentFact, key: str) -> set[str]:
    values = _fact_detail(fact).get(key)
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list):
        return set()
    return {str(value) for value in values if value}


def _explicit_ownership_locations(fact: ComponentFact) -> set[str]:
    """Return locations that explicitly identify a request owner.

    Supporting locations are deliberately excluded.  They describe context
    used by the mapper, but do not prove that a route dispatches a particular
    server-side request.  The ownership fields are the bounded metadata the
    mapper records for that relationship.
    """
    detail = _fact_detail(fact)
    locations: set[str] = set()
    for key in (
        "handler_locations",
        "handler_location",
        "route_locations",
        "route_location",
        "source_locations",
        "source_location",
    ):
        values = detail.get(key)
        if isinstance(values, str):
            values = [values]
        if isinstance(values, list):
            locations.update(str(value) for value in values if value)
    return locations


def _evidence_line(location: str | None) -> tuple[str, int] | None:
    """Split a ``file:line`` location when its line is usable."""
    if not location or ":" not in location:
        return None
    path, separator, line = location.rpartition(":")
    if not separator or not path or not line.isdigit():
        return None
    return path, int(line)


def _nearest_preceding_route(
    source: ComponentFact,
    owner_location: str,
    routes: list[ComponentFact],
) -> bool:
    """Bind one egress owner line to the nearest preceding route.

    Some framework adapters report a route decorator and the request's
    handler location separately.  In that shape the two facts cannot share a
    location, but source order still identifies the route.  Selecting the
    nearest route keeps adjacent endpoints from becoming a fanout.
    """
    if source.fact_type != "route":
        return False
    owner_position = _evidence_line(owner_location)
    if owner_position is None:
        return False
    exact_routes = [
        route
        for route in routes
        if route.fact_type == "route"
        and route.evidence_location == owner_location
    ]
    if exact_routes:
        return any(route.id == source.id for route in exact_routes)

    source_position = _evidence_line(source.evidence_location)
    if source_position is None:
        return False
    source_file, source_line = source_position
    owner_file, owner_line = owner_position
    if source_file != owner_file or source_line >= owner_line:
        return False
    preceding = [
        route
        for route in routes
        if route.fact_type == "route"
        and (position := _evidence_line(route.evidence_location)) is not None
        and position[0] == owner_file
        and position[1] < owner_line
    ]
    if not preceding:
        return False
    nearest = max(
        preceding,
        key=lambda route: _evidence_line(route.evidence_location)[1],
    )
    return nearest.id == source.id


def _proxy_ownership_connection(
    source: ComponentFact,
    target: ComponentFact,
    *,
    routes: list[ComponentFact] | None = None,
) -> tuple[bool, dict]:
    """Check explicit ownership metadata for a route/handler -> server egress.

    A proxy hop is proven when one fact names the other's evidence location or
    both facts name the same handler/route/source location.  Path similarity
    alone is intentionally not sufficient because a component can issue many
    requests from one handler.
    """
    if source.fact_type not in {"route", "handler"}:
        return False, {}
    if target.fact_type != "http_call" or _request_role(target) != "server_egress":
        return False, {}
    source_locations = _explicit_ownership_locations(source)
    target_locations = _explicit_ownership_locations(target)
    shared = sorted(source_locations & target_locations)
    target_named_source = source.evidence_location in target_locations
    source_named_target = target.evidence_location in source_locations
    nearest_owner_locations = [
        location
        for location in target_locations
        if _nearest_preceding_route(source, location, routes or [source])
    ]
    if (
        not shared
        and not target_named_source
        and not source_named_target
        and not nearest_owner_locations
    ):
        return False, {}
    evidence = {
        "source": _fact_evidence(source),
        "server_egress": _fact_evidence(target),
        "ownership": {
            "shared_locations": shared,
            "target_named_source": target_named_source,
            "source_named_target": source_named_target,
            "nearest_preceding_route": nearest_owner_locations,
        },
    }
    return True, evidence


def _authenticated_route_access(
    session: Session,
    connection: ComponentConnection,
    source_fact: ComponentFact,
    target_fact: ComponentFact,
    connections: list[ComponentConnection],
) -> RouteAccess | None:
    """Prove that a protected cross-repo call can obtain and use credentials."""
    flows = session.exec(
        select(ComponentFact)
        .where(ComponentFact.sast_run_id == source_fact.sast_run_id)
        .where(ComponentFact.fact_type == "auth_flow")
    ).all()
    best: RouteAccess | None = None
    for flow in flows:
        if source_fact.evidence_location not in _detail_location_set(
            flow, "credential_use_locations"
        ):
            continue
        acquisition_locations = _detail_location_set(flow, "acquisition_call_locations")
        if not acquisition_locations:
            continue
        detail = _fact_detail(flow)
        try:
            flow_confidence = float(
                detail.get("confidence") or detail.get("llm_confidence") or 0.75
            )
        except (TypeError, ValueError):
            flow_confidence = 0.75
        flow_confidence = max(0.0, min(flow_confidence, 1.0))

        for acquisition in connections:
            if getattr(acquisition, "edge_kind", "calls") != "calls":
                continue
            if (
                acquisition.source_component_id != connection.source_component_id
                or acquisition.target_component_id != connection.target_component_id
            ):
                continue
            acquisition_call = session.get(ComponentFact, acquisition.source_fact_id)
            acquisition_route = session.get(ComponentFact, acquisition.target_fact_id)
            if acquisition_call is None or acquisition_route is None:
                continue
            if acquisition_call.evidence_location not in acquisition_locations:
                continue
            if flow.method and (
                not acquisition_call.method
                or flow.method.upper() != acquisition_call.method.upper()
            ):
                continue
            if flow.path and not _paths_match(flow.path, acquisition_call.path):
                continue
            if _auth_boundary_state(session, acquisition_route) != "public":
                continue

            confidence = min(
                connection.confidence,
                acquisition.confidence,
                flow_confidence,
            )
            candidate = RouteAccess(
                kind="authenticated",
                confidence=confidence,
                authentication={
                    "flow_fact_id": flow.id,
                    "flow_location": flow.evidence_location,
                    "credential_kind": detail.get("credential_kind"),
                    "acquisition": {
                        "source_fact_id": acquisition_call.id,
                        "source_location": acquisition_call.evidence_location,
                        "method": acquisition_call.method,
                        "path": acquisition_call.path,
                        "target_fact_id": acquisition_route.id,
                        "target_location": acquisition_route.evidence_location,
                    },
                },
            )
            if best is None or candidate.confidence > best.confidence:
                best = candidate
    return best


def _route_access(
    session: Session,
    connection: ComponentConnection,
    source_fact: ComponentFact,
    target_fact: ComponentFact,
    connections: list[ComponentConnection],
) -> RouteAccess | None:
    state = _auth_boundary_state(session, target_fact)
    if state == "public":
        return RouteAccess(kind="public", confidence=connection.confidence)
    if state == "protected":
        return _authenticated_route_access(
            session,
            connection,
            source_fact,
            target_fact,
            connections,
        )
    return None


def _same_evidence_file(left: ComponentFact, right: ComponentFact) -> bool:
    return (
        left.evidence_location.split(":", 1)[0]
        == right.evidence_location.split(":", 1)[0]
    )


def _host_of(value: str | None) -> str | None:
    if not value:
        return None
    first_token = value.strip().split()[0] if value.strip() else ""
    if not first_token:
        return None
    parsed = urlparse(first_token if "://" in first_token else f"//{first_token}")
    return (parsed.hostname or "").lower() or None


def _extract_method_path(text: str) -> tuple[str | None, str | None]:
    """Best-effort ``METHOD /path`` extraction from a lead's endpoint/location."""
    match = re.search(
        r"\b(GET|POST|PUT|PATCH|DELETE)\b\s+(/[^\s\"']*)", text or "", re.IGNORECASE
    )
    if match:
        return match.group(1).upper(), match.group(2)
    path_match = re.search(r"(/[\w\-/{}.:]+)", text or "")
    return None, path_match.group(1) if path_match else None


def _extract_method_paths(text: str) -> list[tuple[str | None, str | None]]:
    """Extract the ordered HTTP endpoints named by a lead."""
    return [
        (match.group(1).upper(), match.group(2))
        for match in re.finditer(
            r"\b(GET|POST|PUT|PATCH|DELETE)\b\s+(/[\w\-/{}.:]+)",
            text or "",
            re.IGNORECASE,
        )
    ]


def _anchor_lead(session: Session, anchor: ComponentFact) -> ScanLead | None:
    """Load the source lead represented by a persisted anchor fact."""
    try:
        lead_id = int(_fact_detail(anchor).get("lead_id"))
    except (TypeError, ValueError):
        return None
    lead = session.get(ScanLead, lead_id)
    if (
        lead is None
        or lead.producer_run_type != "sast"
        or lead.producer_run_id != anchor.sast_run_id
    ):
        return None
    return lead


def _anchor_reachability_connection(
    session: Session,
    source: ComponentFact,
    anchor: ComponentFact,
) -> tuple[bool, str]:
    """Allow only a route that can supply the lead's vulnerable input.

    ``route_locations`` is useful evidence for single-endpoint findings, but
    it can also list a downstream endpoint for a finding whose suggested
    endpoint is a sequence such as ``quote then bind``.  In that case the
    first endpoint is the required entry into the vulnerable flow.  Keeping a
    direct path match still supports findings whose sink route differs from
    the route where the lead was recorded when the lead describes one route.
    """
    lead = _anchor_lead(session, anchor)
    endpoint_paths = _extract_method_paths(lead.suggested_endpoint) if lead else []
    if len(endpoint_paths) > 1:
        first_method, first_path = endpoint_paths[0]
        if (
            source.fact_type != "route"
            or not _paths_match(source.path, first_path)
            or (
                first_method
                and source.method
                and first_method.upper() != source.method.upper()
            )
        ):
            return False, "multi-step lead requires its first endpoint"
        return True, "route path matches the lead's first endpoint"

    detail = _fact_detail(anchor)
    source_location = detail.get("source_location")
    if (
        source.fact_type in {"route", "handler", "http_call"}
        and source_location
        and source.evidence_location == str(source_location)
    ):
        return True, "source location matches the lead anchor"

    if (
        source.fact_type == "route"
        and anchor.path
        and _paths_match(source.path, anchor.path)
        and (
            not anchor.method
            or not source.method
            or anchor.method.upper() == source.method.upper()
        )
    ):
        return True, "route path matches the lead anchor"

    explicit_locations: set[str] = set()
    for key in ("route_locations", "route_location"):
        values = detail.get(key)
        if isinstance(values, str):
            values = [values]
        if isinstance(values, list):
            explicit_locations.update(str(value) for value in values if value)
    if source.fact_type == "route" and source.evidence_location in explicit_locations:
        return True, "explicit route evidence links this route to the lead anchor"

    handler_locations: set[str] = set()
    for key in ("handler_locations", "handler_location"):
        values = detail.get(key)
        if isinstance(values, str):
            values = [values]
        if isinstance(values, list):
            handler_locations.update(str(value) for value in values if value)
    if source.fact_type == "handler" and source.evidence_location in handler_locations:
        return True, "explicit handler evidence links this handler to the lead anchor"

    return False, ""


def _score_call_to_route(
    call: ComponentFact, route: ComponentFact
) -> tuple[float, str, dict]:
    """Score a request against a served route using its method and path."""
    if route.fact_type != "route" or _request_role(route) != "server_ingress":
        return 0.0, "", {}
    call_role = _request_role(call)
    if call_role not in {None, "browser_request", "server_egress"}:
        return 0.0, "", {}
    # A path-only match can connect unrelated operations that happen to share
    # a URL.  Keep the cross-repository edge closed until both dimensions are
    # known and equal.
    if not call.method or not route.method or not _paths_match(call.path, route.path):
        return 0.0, "", {}
    score = 0.0
    parts: list[str] = []
    call_host = _host_of(call.host)
    route_host = _host_of(route.host)
    if call_host and route_host and call_host != route_host:
        return 0.0, "", {}
    if call_host and route_host and call_host == route_host:
        score += 0.15
        parts.append("service host matches")
    if call.method.upper() == route.method.upper():
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
            "call": {
                "method": call.method,
                "path": call.path,
                "host": call.host,
                **_fact_evidence(call),
            },
            "route": {
                "method": route.method,
                "path": route.path,
                **_fact_evidence(route),
            },
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
        facts = list(
            session.exec(
                select(ComponentFact).where(
                    ComponentFact.sast_run_id == member.sast_run_id
                )
            ).all()
        )
        originals = session.exec(
            select(ScanLead)
            .where(ScanLead.producer_run_type == "sast")
            .where(ScanLead.producer_run_id == member.sast_run_id)
            .where(ScanLead.imported_into_run_id == None)  # noqa: E711
            .where(ScanLead.reportable == True)  # noqa: E712
        ).all()
        for original in originals:
            anchor_method, anchor_path = _extract_method_path(
                original.suggested_endpoint or ""
            )
            existing_anchors = [
                fact
                for fact in facts
                if fact.fact_type == "lead_anchor"
                and _fact_detail(fact).get("lead_id") == original.id
            ]
            if existing_anchors:
                for existing_anchor in existing_anchors:
                    changed = False
                    if not existing_anchor.method and anchor_method:
                        existing_anchor.method = anchor_method
                        changed = True
                    if not existing_anchor.path and anchor_path:
                        existing_anchor.path = anchor_path
                        changed = True
                    if changed:
                        session.add(existing_anchor)
                if not anchor_path or any(
                    existing_anchor.path
                    and _paths_match(existing_anchor.path, anchor_path)
                    and (
                        not anchor_method
                        or not existing_anchor.method
                        or existing_anchor.method.upper() == anchor_method.upper()
                    )
                    for existing_anchor in existing_anchors
                ):
                    continue
            fingerprint = f"lead-anchor:{original.id}:{original.fingerprint}"
            anchor = next(
                (fact for fact in facts if fact.fingerprint == fingerprint),
                None,
            )
            if anchor is None:
                anchor = ComponentFact(
                    sast_run_id=member.sast_run_id,
                    component_id=member.component_id,
                    fact_type="lead_anchor",
                    method=anchor_method,
                    path=anchor_path,
                    name=original.title,
                    detail_json=json.dumps(
                        {
                            "lead_id": original.id,
                            "source_location": original.location,
                            "fingerprint": original.fingerprint,
                        },
                        separators=(",", ":"),
                    ),
                    evidence_location=original.location or "",
                    fingerprint=fingerprint,
                )
                session.add(anchor)
                session.flush()
                facts.append(anchor)
        facts_by_component[member.component_id] = facts

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
    seen_cross_call_identities: set[
        tuple[int, int, tuple[str, str, str], tuple[str, str, str]]
    ] = set()
    component_ids = list(facts_by_component.keys())
    # Build the intra-repository portion of the graph first. These edges make
    # a source-code HTTP call reachable from a browser route/action instead of
    # treating the call site as a frontend entrypoint by itself.
    for component_id, facts in facts_by_component.items():
        ui_routes = [fact for fact in facts if fact.fact_type == "ui_route"]
        ui_actions = [fact for fact in facts if fact.fact_type == "ui_action"]
        calls = [fact for fact in facts if fact.fact_type == "http_call"]
        handlers = [fact for fact in facts if fact.fact_type in {"route", "handler"}]
        anchors = [fact for fact in facts if fact.fact_type == "lead_anchor"]
        for route in ui_routes:
            for action in ui_actions:
                if not _ui_route_action_connection(route, action, ui_routes):
                    continue
                evidence = {
                    "route": _fact_evidence(route),
                    "action": _fact_evidence(action),
                }
                edge = _make_connection(
                    campaign_id=campaign_id,
                    source=route,
                    target=action,
                    match_kind="deterministic",
                    confidence=0.65,
                    rationale="Code analysis linked the UI route to this action",
                    evidence=evidence,
                    edge_kind="contains",
                )
                session.add(edge)
                connections.append(edge)
            for call in calls:
                if not _semantic_connection(
                    route,
                    call,
                    allowed_source_types={"ui_route"},
                    allowed_target_types={"handler", "http_call"},
                ):
                    continue
                if (
                    call.fact_type == "http_call"
                    and _request_role(call) != "browser_request"
                ):
                    continue
                edge = _make_connection(
                    campaign_id=campaign_id,
                    source=route,
                    target=call,
                    match_kind="deterministic",
                    confidence=0.55,
                    rationale="Code analysis linked the UI route to this browser request",
                    evidence={
                        "route": _fact_evidence(route),
                        "call": _fact_evidence(call),
                    },
                    edge_kind="triggers",
                )
                session.add(edge)
                connections.append(edge)

        # A frontend and its server route can live in the same component
        # (for example, a Flask app serving both the page and its API).  Keep
        # this hop explicit so route tracing can continue through the ingress
        # route instead of stopping at the browser request.
        ingress_routes = [
            fact
            for fact in handlers
            if fact.fact_type == "route" and _request_role(fact) == "server_ingress"
        ]
        for call in calls:
            _infer_owned_server_egress(session, call, ingress_routes)
        browser_calls = [
            fact for fact in calls if _request_role(fact) == "browser_request"
        ]
        for call in browser_calls:
            candidates = [
                route
                for route in ingress_routes
                if call.method
                and route.method
                and call.method.upper() == route.method.upper()
                and _paths_match(call.path, route.path)
            ]
            if not candidates:
                continue
            # Duplicate route facts can be produced by framework adapters.
            # Select one deterministic route for a semantic method/path pair
            # rather than creating a fanout of equivalent edges.
            route = min(candidates, key=lambda fact: fact.id or 0)
            edge = _make_connection(
                campaign_id=campaign_id,
                source=call,
                target=route,
                match_kind="deterministic",
                confidence=0.85,
                rationale=(
                    "Browser request method and path match this same-component "
                    "server ingress route"
                ),
                evidence={
                    "browser_request": _fact_evidence(call),
                    "server_ingress": _fact_evidence(route),
                },
                edge_kind="calls",
            )
            session.add(edge)
            connections.append(edge)

        for action in ui_actions:
            for call in calls:
                if not _ui_action_call_connection(action, call):
                    continue
                edge = _make_connection(
                    campaign_id=campaign_id,
                    source=action,
                    target=call,
                    match_kind="deterministic",
                    confidence=0.60,
                    rationale="Code analysis linked the UI action to this browser request",
                    evidence={
                        "action": _fact_evidence(action),
                        "call": _fact_evidence(call),
                    },
                    edge_kind="triggers",
                )
                session.add(edge)
                connections.append(edge)
        for source in (*ui_routes, *ui_actions):
            for handler in handlers:
                if not _semantic_connection(
                    source,
                    handler,
                    allowed_source_types={"ui_route", "ui_action"},
                    allowed_target_types={"handler"},
                ):
                    continue
                edge = _make_connection(
                    campaign_id=campaign_id,
                    source=source,
                    target=handler,
                    match_kind="deterministic",
                    confidence=0.75,
                    rationale="Code analysis linked the UI entrypoint to this handler",
                    evidence={
                        "source": _fact_evidence(source),
                        "handler": _fact_evidence(handler),
                    },
                    edge_kind="triggers",
                )
                session.add(edge)
                connections.append(edge)
        for handler in handlers:
            for call in calls:
                semantic_connection = _semantic_connection(
                    handler,
                    call,
                    allowed_source_types={"route", "handler"},
                    allowed_target_types={"handler", "http_call"},
                )
                proxy_connection = False
                proxy_evidence: dict = {}
                if not semantic_connection:
                    proxy_connection, proxy_evidence = _proxy_ownership_connection(
                        handler,
                        call,
                        routes=ingress_routes,
                    )
                if not semantic_connection and not proxy_connection:
                    continue
                target_role = _request_role(call)
                if call.fact_type == "http_call" and target_role not in {
                    "browser_request",
                    "server_egress",
                }:
                    continue
                edge = _make_connection(
                    campaign_id=campaign_id,
                    source=handler,
                    target=call,
                    match_kind="deterministic",
                    confidence=0.78 if proxy_connection else 0.60,
                    rationale=(
                        "Explicit ownership metadata links this route/handler "
                        "to its server egress proxy request"
                        if proxy_connection
                        else "Code analysis linked the handler to this "
                        f"{target_role or 'HTTP'} request"
                    ),
                    evidence=proxy_evidence
                    if proxy_connection
                    else {
                        "handler": _fact_evidence(handler),
                        "call": _fact_evidence(call),
                    },
                    edge_kind="dispatches",
                )
                session.add(edge)
                connections.append(edge)
        for anchor in anchors:
            for source in (
                fact
                for fact in facts
                if fact.fact_type in {"route", "handler", "http_call"}
                and fact.id != anchor.id
            ):
                reaches_anchor, reachability_reason = _anchor_reachability_connection(
                    session, source, anchor
                )
                if not reaches_anchor:
                    continue
                edge = _make_connection(
                    campaign_id=campaign_id,
                    source=source,
                    target=anchor,
                    match_kind="deterministic",
                    confidence=0.60,
                    rationale=(
                        "Code analysis linked this route or handler to the SAST "
                        f"lead anchor: {reachability_reason}"
                    ),
                    evidence={
                        "source": _fact_evidence(source),
                        "lead_anchor": _fact_evidence(anchor),
                    },
                    edge_kind="reaches",
                )
                session.add(edge)
                connections.append(edge)

        # A handler chain can span several files.  Preserve only relationships
        # for which one fact explicitly names the other's evidence location.
        for source in handlers:
            for target in handlers:
                if source.id == target.id or not _semantic_connection(
                    source,
                    target,
                    allowed_source_types={"route", "handler"},
                    allowed_target_types={"handler"},
                ):
                    continue
                edge = _make_connection(
                    campaign_id=campaign_id,
                    source=source,
                    target=target,
                    match_kind="deterministic",
                    confidence=0.75,
                    rationale="Code analysis linked these handler functions",
                    evidence={
                        "source": _fact_evidence(source),
                        "target": _fact_evidence(target),
                    },
                    edge_kind="dispatches",
                )
                session.add(edge)
                connections.append(edge)

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
            routes = _unique_route_facts(
                [
                    f
                    for f in facts_by_component[target_component_id]
                    if f.fact_type == "route"
                ]
            )
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
                    identity = _connection_identity(
                        source_component_id,
                        target_component_id,
                        call,
                        route,
                    )
                    if identity in seen_cross_call_identities:
                        continue
                    seen_cross_call_identities.add(identity)
                    connection = _make_connection(
                        campaign_id=campaign_id,
                        source=call,
                        target=route,
                        match_kind="deterministic",
                        confidence=score,
                        rationale=rationale,
                        evidence=evidence,
                        edge_kind="calls",
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
                    call = next(
                        (item for item in unmatched_calls if item.id == call_id), None
                    )
                    route = next((item for item in routes if item.id == route_id), None)
                    if call is None or route is None:
                        continue
                    identity = _connection_identity(
                        source_component_id,
                        target_component_id,
                        call,
                        route,
                    )
                    if identity in seen_cross_call_identities:
                        continue
                    seen_cross_call_identities.add(identity)
                    connection = _make_connection(
                        campaign_id=campaign_id,
                        source=call,
                        target=route,
                        match_kind="llm_assisted",
                        confidence=min(confidence, 1.0),
                        rationale=str(result.get("rationale", "")),
                        evidence=result.get("evidence", {}),
                        edge_kind="calls",
                    )
                    session.add(connection)
                    connections.append(connection)

    session.flush()
    return connections


def _ambiguous_calls(
    session: Session,
    members: list[CampaignSourceMember],
    deterministic: list[ComponentConnection],
) -> list[AmbiguousCall]:
    """Build a bounded candidate set for calls the exact matcher missed."""
    facts_by_component: dict[int, list[ComponentFact]] = {}
    for member in members:
        if member.sast_run_id is None:
            continue
        facts_by_component[member.component_id] = list(
            session.exec(
                select(ComponentFact).where(
                    ComponentFact.sast_run_id == member.sast_run_id
                )
            ).all()
        )
    matched_call_ids = {
        connection.source_fact_id
        for connection in deterministic
        if getattr(connection, "edge_kind", "calls") == "calls"
    }
    ambiguous: list[AmbiguousCall] = []
    for source_component_id, facts in facts_by_component.items():
        for call in sorted(
            (fact for fact in facts if fact.fact_type == "http_call"),
            key=lambda fact: fact.id or 0,
        ):
            if call.id in matched_call_ids:
                continue
            for target_component_id, target_facts in facts_by_component.items():
                if target_component_id == source_component_id:
                    continue
                routes = _unique_route_facts(
                    [
                        fact
                        for fact in target_facts
                        if fact.fact_type == "route"
                        and (
                            not call.method
                            or not fact.method
                            or call.method.upper() == fact.method.upper()
                        )
                    ]
                )
                routes.sort(
                    key=lambda fact: (
                        0
                        if _normalize_path(call.path) == _normalize_path(fact.path)
                        else 1,
                        fact.id or 0,
                    )
                )
                if routes:
                    ambiguous.append(
                        AmbiguousCall(
                            call=call,
                            target_component_id=target_component_id,
                            candidate_routes=tuple(routes[:20]),
                        )
                    )
    return ambiguous


def _ambiguous_payload(item: AmbiguousCall) -> dict:
    def _fact_payload(fact: ComponentFact) -> dict:
        try:
            detail = json.loads(fact.detail_json or "{}")
        except (TypeError, ValueError):
            detail = {}
        return {
            "id": fact.id,
            "component_id": fact.component_id,
            "fact_type": fact.fact_type,
            "method": fact.method,
            "path": fact.path,
            "host": fact.host,
            "name": fact.name,
            "evidence_location": fact.evidence_location,
            "detail": detail,
        }

    return {
        "call": _fact_payload(item.call),
        "candidate_routes": [_fact_payload(route) for route in item.candidate_routes],
    }


async def match_ambiguous_connections(
    llm_config,
    ambiguous: list[AmbiguousCall],
    *,
    campaign_id: int | None = None,
    stop_check=None,
) -> list[ConnectionProposal]:
    """Ask the LLM to resolve bounded unresolved fact candidates."""
    if not ambiguous:
        return []
    from aespa.services import llm as llm_svc
    from aespa.services.prompts.component_mapper import CONNECTION_MATCHER_SYSTEM_PROMPT

    proposals: list[ConnectionProposal] = []
    total_batches = (len(ambiguous) + 49) // 50
    for offset in range(0, len(ambiguous), 50):
        if stop_check and stop_check():
            raise asyncio.CancelledError
        batch_idx = (offset // 50) + 1
        batch = ambiguous[offset : offset + 50]
        if campaign_id:
            events_svc.emit(
                campaign_id,
                {
                    "type": "agent_status",
                    "agent_id": "connection-matcher",
                    "role": "Connection Matcher",
                    "status": "active",
                    "current_task": f"Turn {batch_idx}/{total_batches}: Disambiguating {len(batch)} candidate pair(s)",
                    "outcome": None,
                    "_persist": True,
                },
            )
            events_svc.emit(
                campaign_id,
                {
                    "type": "scanner_phase",
                    "phase": "component_mapping",
                    "status": "running",
                    "message": f"[Connection Matcher] Turn {batch_idx}/{total_batches}: Evaluating LLM disambiguation for {len(batch)} candidate pair(s)",
                    "data": {
                        "batch": batch_idx,
                        "total_batches": total_batches,
                        "candidates": len(batch),
                    },
                },
            )
        prompt = (
            "Resolve only pairs from this JSON input. Return a JSON array with "
            "call_id, route_id, confidence, rationale, and evidence. Do not "
            "invent IDs.\n\n" + json.dumps([_ambiguous_payload(item) for item in batch])
        )
        raw = await llm_svc.plain_completion(
            llm_config,
            prompt,
            system_prompt=CONNECTION_MATCHER_SYSTEM_PROMPT,
        )
        try:
            decoded = llm_svc.extract_json_response(raw, expect=list)
        except (TypeError, ValueError) as exc:
            raise RuntimeError(
                f"Connection matcher returned invalid JSON: {exc}"
            ) from exc
        if not isinstance(decoded, list):
            raise RuntimeError("Connection matcher response must be a JSON array")
        for item in decoded:
            if not isinstance(item, dict):
                continue
            try:
                confidence = float(item.get("confidence", 0.0))
            except (TypeError, ValueError):
                continue
            if confidence < 0.7:
                continue
            try:
                call_id = int(item["call_id"])
                route_id = int(item["route_id"])
            except (KeyError, TypeError, ValueError):
                continue
            allowed_calls = {entry.call.id for entry in batch}
            allowed_routes = {
                route.id for entry in batch for route in entry.candidate_routes
            }
            allowed_pairs = {
                (entry.call.id, route.id)
                for entry in batch
                for route in entry.candidate_routes
            }
            if (
                call_id not in allowed_calls
                or route_id not in allowed_routes
                or (call_id, route_id) not in allowed_pairs
            ):
                continue
            proposals.append(
                ConnectionProposal(
                    call_id=call_id,
                    route_id=route_id,
                    confidence=min(confidence, 1.0),
                    rationale=str(item.get("rationale") or "")[:2000],
                    evidence=item.get("evidence")
                    if isinstance(item.get("evidence"), dict)
                    else {},
                )
            )
    return proposals


def _same_file(location_a: str, location_b: str) -> bool:
    return (location_a or "").split(":")[0] == (location_b or "").split(":")[0]


def _target_leads_for_route(
    session: Session,
    target_fact: ComponentFact,
    connections: list[ComponentConnection],
) -> list[ScanLead]:
    """Resolve backend leads through route→lead-anchor graph evidence."""
    anchor_ids = {
        connection.target_fact_id
        for connection in connections
        if getattr(connection, "edge_kind", "") == "reaches"
        and connection.source_fact_id == target_fact.id
    }
    lead_ids: set[int] = set()
    for anchor_id in anchor_ids:
        anchor = session.get(ComponentFact, anchor_id)
        if anchor is None or anchor.fact_type != "lead_anchor":
            continue
        try:
            lead_ids.add(int(_fact_detail(anchor).get("lead_id")))
        except (TypeError, ValueError):
            continue

    # A lead's file location is an anchor candidate, not proof that its
    # vulnerability is reached by this route.  Only an explicit lead_anchor
    # edge is sufficient here.
    return [
        lead
        for lead in session.exec(
            select(ScanLead)
            .where(ScanLead.producer_run_id == target_fact.sast_run_id)
            .where(ScanLead.producer_run_type == "sast")
            .where(ScanLead.imported_into_run_id == None)  # noqa: E711
            .where(ScanLead.reportable == True)  # noqa: E712
        ).all()
        if lead.id in lead_ids
    ]


def _upsert_lead_provenance(
    session: Session,
    *,
    lead_id: int,
    component_id: int,
    role: str,
    fact_id: int,
) -> None:
    provenance = session.exec(
        select(ScanLeadComponentProvenance)
        .where(ScanLeadComponentProvenance.scan_lead_id == lead_id)
        .where(ScanLeadComponentProvenance.component_id == component_id)
    ).first()
    if provenance is None:
        provenance = ScanLeadComponentProvenance(
            scan_lead_id=lead_id,
            component_id=component_id,
            role=role,
            fact_id=fact_id,
        )
    else:
        provenance.role = role
        provenance.fact_id = fact_id
    session.add(provenance)


def _generate_cross_component_leads(
    session: Session, campaign_id: int, connections: list[ComponentConnection]
) -> list[ScanLead]:
    """Create campaign-owned leads when two components' evidence combines into
    a new hypothesis:
    1. A reportable SAST lead at the outbound-call site (Repo A) reaching an
       explicitly public route or an evidence-backed authenticated route
       (Repo B).
    2. A reportable SAST lead reached by the target route graph (Repo B), where
       the route is public or the caller has a proven credential flow.
    """
    created_by_id: dict[int, ScanLead] = {}
    for connection in connections:
        if getattr(connection, "edge_kind", "calls") != "calls":
            continue
        if connection.confidence < _MIN_CROSS_LEAD_CONNECTION_SCORE:
            continue
        source_fact = session.get(ComponentFact, connection.source_fact_id)
        target_fact = session.get(ComponentFact, connection.target_fact_id)
        if source_fact is None or target_fact is None:
            continue
        if source_fact.fact_type != "http_call" or target_fact.fact_type != "route":
            continue

        source_comp = session.get(ApplicationComponent, connection.source_component_id)
        target_comp = session.get(ApplicationComponent, connection.target_component_id)
        source_comp_name = (
            source_comp.name if source_comp else f"#{connection.source_component_id}"
        )
        target_comp_name = (
            target_comp.name if target_comp else f"#{connection.target_component_id}"
        )
        access = _route_access(
            session,
            connection,
            source_fact,
            target_fact,
            connections,
        )
        if access is None:
            continue

        # ── Case 1: SAST lead on the calling component (source_fact) ─────────
        source_leads = [
            source_lead
            for source_lead in session.exec(
                select(ScanLead)
                .where(ScanLead.producer_run_id == source_fact.sast_run_id)
                .where(ScanLead.producer_run_type == "sast")
                .where(ScanLead.imported_into_run_id == None)  # noqa: E711
                .where(ScanLead.reportable == True)  # noqa: E712
            ).all()
            if _same_file(source_lead.location, source_fact.evidence_location)
        ]

        for source_lead in source_leads:
            fingerprint = _cross_repo_lead_fingerprint(
                category=source_lead.category,
                origin_fingerprint=source_lead.fingerprint,
                source_component_id=connection.source_component_id,
                target_component_id=connection.target_component_id,
            )
            attack_path = _load_cross_repo_attack_path(
                session,
                campaign_id=campaign_id,
                fingerprint=fingerprint,
                base={
                    "frontend_entrypoint": {
                        "component_id": connection.source_component_id,
                        "component_name": source_comp_name,
                        "location": source_fact.evidence_location,
                        "method": source_fact.method,
                        "path": source_fact.path,
                        "host": source_fact.host,
                    },
                    "backend_route": {
                        "component_id": connection.target_component_id,
                        "component_name": target_comp_name,
                        "location": target_fact.evidence_location,
                        "method": target_fact.method,
                        "path": target_fact.path,
                    },
                    "vulnerability": {
                        "lead_id": source_lead.id,
                        "category": source_lead.category,
                        "severity": source_lead.severity,
                        "title": source_lead.title,
                        "description": source_lead.description,
                        "evidence": source_lead.evidence,
                    },
                },
                source_fact=source_fact,
                target_fact=target_fact,
                connection=connection,
                source_component_name=source_comp_name,
                target_component_name=target_comp_name,
                vulnerability=source_lead,
                backend_case=False,
                access=access,
            )
            authenticated_access = _attack_path_has_authenticated_access(attack_path)
            lead = upsert_lead(
                session,
                producer_run_id=campaign_id,
                producer_run_type="campaign",
                title=(
                    f"Cross-repository: {source_lead.title} can reach "
                    f"{'authenticated routes' if authenticated_access else 'an explicitly public route'} "
                    f"in {target_comp_name}"
                ),
                description=(
                    f"{source_lead.description}\n\nThis call site is connected "
                    "(deterministic route/method match) to another repository. "
                    + (
                        "The caller has an evidence-backed credential acquisition "
                        "and reuse path for protected routes. "
                        if authenticated_access
                        else "The matched route is explicitly public. "
                    )
                    + "Matched endpoint instances are retained in the attack path."
                ),
                category=source_lead.category,
                severity=source_lead.severity,
                confidence=min(source_lead.confidence, access.confidence),
                location=source_lead.location,
                evidence=(
                    f"Source SAST lead: {source_lead.location}\n"
                    f"Matched endpoint: {target_fact.method} {target_fact.path} "
                    f"({target_fact.evidence_location})\n"
                    f"{_route_access_evidence(access)}\n{source_lead.evidence}"
                ),
                source="campaign",
                fingerprint=fingerprint,
                suggested_endpoint=_cross_repo_suggested_endpoint(attack_path),
                attack_path=attack_path,
                validation_status="pending",
                reportable=True,
            )
            if lead.id is not None:
                created_by_id[lead.id] = lead

            for component_id, role, fact_id in (
                (connection.source_component_id, "primary", source_fact.id),
                (connection.target_component_id, "contributing", target_fact.id),
            ):
                _upsert_lead_provenance(
                    session,
                    lead_id=lead.id,
                    component_id=component_id,
                    role=role,
                    fact_id=fact_id,
                )

        # ── Case 2: SAST lead on the receiving target route (target_fact) ────
        target_leads = _target_leads_for_route(session, target_fact, connections)

        for target_lead in target_leads:
            fingerprint = _cross_repo_lead_fingerprint(
                category=target_lead.category,
                origin_fingerprint=target_lead.fingerprint,
                source_component_id=connection.source_component_id,
                target_component_id=connection.target_component_id,
                backend_case=True,
            )
            attack_path = _load_cross_repo_attack_path(
                session,
                campaign_id=campaign_id,
                fingerprint=fingerprint,
                base={
                    "frontend_entrypoint": {
                        "component_id": connection.source_component_id,
                        "component_name": source_comp_name,
                        "location": source_fact.evidence_location,
                        "method": source_fact.method,
                        "path": source_fact.path,
                        "host": source_fact.host,
                    },
                    "backend_route": {
                        "component_id": connection.target_component_id,
                        "component_name": target_comp_name,
                        "location": target_fact.evidence_location,
                        "method": target_fact.method,
                        "path": target_fact.path,
                    },
                    "vulnerability": {
                        "lead_id": target_lead.id,
                        "category": target_lead.category,
                        "severity": target_lead.severity,
                        "title": target_lead.title,
                        "description": target_lead.description,
                        "evidence": target_lead.evidence,
                    },
                },
                source_fact=source_fact,
                target_fact=target_fact,
                connection=connection,
                source_component_name=source_comp_name,
                target_component_name=target_comp_name,
                vulnerability=target_lead,
                backend_case=True,
                access=access,
            )
            lead = upsert_lead(
                session,
                producer_run_id=campaign_id,
                producer_run_type="campaign",
                title=(
                    f"Cross-repository: Backend lead '{target_lead.title}' reachable "
                    f"from {source_comp_name}"
                ),
                description=(
                    f"Backend vulnerability '{target_lead.title}' in {target_comp_name} "
                    f"is reachable through {source_comp_name}. Matched endpoint "
                    "instances are retained in the attack path.\n\n"
                    f"Vulnerability Description: {target_lead.description}"
                ),
                category=target_lead.category,
                severity=target_lead.severity,
                confidence=min(target_lead.confidence, access.confidence),
                location=target_lead.location,
                evidence=(
                    f"Frontend entrypoint: {source_fact.evidence_location} ({source_fact.method or ''} {source_fact.path or ''})\n"
                    f"Backend route: {target_fact.evidence_location} ({target_fact.method or ''} {target_fact.path or ''})\n"
                    f"{_route_access_evidence(access)}\n"
                    f"Backend SAST lead: {target_lead.evidence}"
                ),
                source="campaign",
                fingerprint=fingerprint,
                suggested_endpoint=_cross_repo_suggested_endpoint(attack_path),
                attack_path=attack_path,
                validation_status="pending",
                reportable=True,
            )
            if lead.id is not None:
                created_by_id[lead.id] = lead

            for component_id, role, fact_id in (
                (connection.source_component_id, "primary", source_fact.id),
                (connection.target_component_id, "contributing", target_fact.id),
            ):
                _upsert_lead_provenance(
                    session,
                    lead_id=lead.id,
                    component_id=component_id,
                    role=role,
                    fact_id=fact_id,
                )

    session.flush()
    return list(created_by_id.values())


def _generate_frontend_path_leads(
    session: Session,
    campaign_id: int,
    source_members: list[CampaignSourceMember],
) -> list[ScanLead]:
    """Create one campaign lead for each bounded UI-rooted path."""
    created: list[ScanLead] = []
    max_edges = 8
    max_components = 6
    max_paths = 10
    min_confidence = 0.50
    mapper_config = session.get(ComponentMapperConfig, 1)
    if mapper_config is not None:
        max_edges = mapper_config.max_trace_edges
        max_components = mapper_config.max_trace_components
        max_paths = mapper_config.max_paths_per_lead
        min_confidence = mapper_config.min_trace_confidence
    campaign = session.get(AssessmentCampaign, campaign_id)
    if campaign is not None:
        max_edges = int(getattr(campaign, "max_trace_edges", None) or max_edges)
        max_components = int(
            getattr(campaign, "max_trace_components", None) or max_components
        )
        max_paths = int(getattr(campaign, "max_paths_per_lead", None) or max_paths)
        min_confidence = float(
            getattr(campaign, "min_trace_confidence", None) or min_confidence
        )

    for member in source_members:
        if member.sast_run_id is None:
            continue
        originals = session.exec(
            select(ScanLead)
            .where(ScanLead.producer_run_type == "sast")
            .where(ScanLead.producer_run_id == member.sast_run_id)
            .where(ScanLead.imported_into_run_id == None)  # noqa: E711
            .where(ScanLead.reportable == True)  # noqa: E712
        ).all()
        for original in originals:
            paths = trace_lead_paths(
                session,
                campaign_id,
                original,
                max_edges=max_edges,
                max_components=max_components,
                max_paths=max_paths,
                min_confidence=min_confidence,
            )
            for path in paths:
                attack_path = attack_path_for_trace(path, original)
                path_identity = canonical_path_identity(original.id, attack_path)
                title = f"Frontend path: {original.title}"
                location = " -> ".join(
                    fact.evidence_location
                    for fact in path.facts
                    if fact.evidence_location
                )
                fingerprint = lead_fingerprint(
                    category=original.category,
                    title=f"{title}:{path_identity}",
                    # Path evidence lines remain in the derived lead's
                    # location, but the database identity must survive an
                    # equivalent mapper path choosing a different anchor.
                    location=original.location,
                )
                lead = upsert_lead(
                    session,
                    producer_run_id=campaign_id,
                    producer_run_type="campaign",
                    title=title,
                    description=(
                        f"{original.description}\n\n"
                        "This derived lead preserves the original backend evidence "
                        "and adds a bounded frontend-to-sink path."
                    ),
                    category=original.category,
                    severity=original.severity,
                    confidence=path.confidence,
                    location=location or original.location,
                    evidence=original.evidence,
                    source="campaign",
                    fingerprint=fingerprint,
                    suggested_endpoint=original.suggested_endpoint,
                    attack_path=attack_path,
                    source_trace=json.loads(original.source_trace_json or "{}"),
                    controls=json.loads(original.control_trace_json or "[]"),
                    sink_trace=json.loads(original.sink_trace_json or "{}"),
                    validation_status="pending",
                    reportable=True,
                )
                for name, value in (
                    ("origin_lead_id", original.id),
                    ("origin_sast_run_id", original.producer_run_id),
                    ("origin_component_id", member.component_id),
                    ("origin_path_json", original.attack_path_json or "{}"),
                    ("trace_path_key", path_identity),
                    ("trace_status", "complete" if path.complete else "incomplete"),
                    ("trace_confidence", path.confidence),
                ):
                    if hasattr(lead, name):
                        setattr(lead, name, value)
                session.add(lead)
                for position, fact in enumerate(path.facts):
                    if fact.component_id is None:
                        continue
                    _upsert_lead_provenance(
                        session,
                        lead_id=lead.id,
                        component_id=fact.component_id,
                        role="primary" if position == 0 else "contributing",
                        fact_id=fact.id,
                    )
                created.append(lead)
    session.flush()
    return created


async def _rewrite_pre_crawl_frontend_paths(
    campaign_id: int,
    *,
    llm_config,
) -> list[str]:
    """Improve deterministic path wording without allowing new evidence."""
    from aespa.services import llm as llm_svc

    warnings: list[str] = []
    with Session(get_engine()) as session:
        leads = session.exec(
            select(ScanLead)
            .where(ScanLead.producer_run_type == "campaign")
            .where(ScanLead.producer_run_id == campaign_id)
            .where(ScanLead.origin_lead_id != None)  # noqa: E711
            .where(ScanLead.reportable == True)  # noqa: E712
        ).all()
        lead_payloads: list[tuple[int, dict, set[int], dict[str, str]]] = []
        for lead in leads:
            try:
                path = json.loads(lead.attack_path_json or "{}")
            except (TypeError, json.JSONDecodeError):
                continue
            if not isinstance(path, dict):
                continue
            hops = path.get("hops") or []
            fact_ids = {
                int(value)
                for hop in hops
                if isinstance(hop, dict)
                for value in (hop.get("source_fact_id"), hop.get("target_fact_id"))
                if isinstance(value, int)
            }
            facts = (
                session.exec(
                    select(ComponentFact).where(ComponentFact.id.in_(fact_ids))
                ).all()
                if fact_ids
                else []
            )
            allowed_values: dict[str, str] = {}
            for fact in facts:
                for value in (
                    fact.path,
                    fact.method,
                    fact.name,
                    fact.evidence_location,
                ):
                    if value:
                        allowed_values[str(value)] = str(value)
            lead_payloads.append(
                (
                    lead.id,
                    path,
                    fact_ids,
                    allowed_values,
                )
            )

    for lead_id, path, fact_ids, allowed_values in lead_payloads:
        if not fact_ids:
            continue
        origin = path.get("origin_attack_path")
        if not isinstance(origin, dict):
            origin = {}
        prompt = (
            "Rewrite only the frontend wording for this approved pre-crawl "
            "security path. Return one JSON object with optional keys "
            "entry, frontend_entrypoint, request_transition, prerequisites, "
            "mutation_points, proof_gaps, dynamic_test, evidence_fact_ids. "
            "Use only the supplied fact IDs and values; do not invent routes, "
            "fields, selectors, URLs, or steps.\n\n"
            + json.dumps(
                {
                    "lead": {
                        "title": origin.get("title", ""),
                        "description": origin.get("description", ""),
                    },
                    "path": path,
                    "facts": {
                        "ids": sorted(fact_ids),
                        "values": sorted(allowed_values.values()),
                    },
                },
                separators=(",", ":"),
            )
        )
        try:
            raw = await llm_svc.plain_completion(
                llm_config,
                prompt,
                system_prompt=(
                    "You are an evidence-constrained security test planner. "
                    "Return valid JSON only and preserve every unmentioned field."
                ),
            )
            decoded = llm_svc.extract_json_response(raw, expect=dict)
            if not isinstance(decoded, dict):
                raise ValueError("response was not an object")
            allowed_keys = {
                "entry",
                "frontend_entrypoint",
                "request_transition",
                "prerequisites",
                "mutation_points",
                "proof_gaps",
                "dynamic_test",
                "evidence_fact_ids",
            }
            if set(decoded) - allowed_keys:
                raise ValueError("response contained unsupported fields")
            evidence_ids = decoded.get("evidence_fact_ids", sorted(fact_ids))
            if (
                not isinstance(evidence_ids, list)
                or not all(isinstance(value, int) for value in evidence_ids)
                or not set(evidence_ids) <= fact_ids
            ):
                raise ValueError("response cited an unknown fact")
            for key in ("entry", "dynamic_test"):
                if key in decoded and (
                    not isinstance(decoded[key], str) or len(decoded[key]) > 2000
                ):
                    raise ValueError(f"invalid {key}")
            for key in ("prerequisites", "mutation_points", "proof_gaps"):
                if key in decoded and (
                    not isinstance(decoded[key], list)
                    or not all(
                        isinstance(value, str) and value.strip()
                        for value in decoded[key]
                    )
                ):
                    raise ValueError(f"invalid {key}")
            generated_text = json.dumps(decoded, ensure_ascii=False)
            if any(
                token.startswith("/") and token not in allowed_values
                for token in re.findall(r"/[A-Za-z0-9_{}.:?=&%/-]+", generated_text)
            ):
                raise ValueError("response introduced an unsupported route")
        except Exception as exc:
            warnings.append(
                f"Lead {lead_id}: pre-crawl path wording was not rewritten ({exc})"
            )
            continue

        with Session(get_engine()) as session:
            lead = session.get(ScanLead, lead_id)
            if lead is None:
                continue
            try:
                current = json.loads(lead.attack_path_json or "{}")
            except (TypeError, json.JSONDecodeError):
                current = {}
            if not isinstance(current, dict):
                continue
            pre = deepcopy(current.get("approved_pre_crawl_path") or current)
            for key in (
                "entry",
                "frontend_entrypoint",
                "request_transition",
                "prerequisites",
                "mutation_points",
                "proof_gaps",
                "dynamic_test",
            ):
                if key in decoded:
                    pre[key] = decoded[key]
                    current[key] = decoded[key]
            pre["evidence_fact_ids"] = evidence_ids
            current["approved_pre_crawl_path"] = pre
            current["pre_crawl_wording_source"] = "llm_assisted"
            lead.attack_path_json = json.dumps(current, separators=(",", ":"))
            lead.updated_at = datetime.now(_UTC)
            session.add(lead)
            session.commit()
    return warnings


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
        evidence["hint"] = hint.note or "code-to-live-target routing association"

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


def _lead_has_proof_gaps(lead: ScanLead) -> bool:
    """Return whether a traced lead records any unresolved proof gap."""
    raw = getattr(lead, "proof_gaps_json", "") or ""
    try:
        gaps = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        gaps = []
    return bool(gaps) if isinstance(gaps, list | dict) else bool(str(raw).strip())


def _has_frontend_trace(attack_path: object) -> bool:
    """Return whether a path proves a schema-v3 browser entrypoint."""
    if not isinstance(attack_path, dict):
        return False
    if (
        attack_path.get("schema_version") != 3
        or attack_path.get("perspective") != "frontend"
    ):
        return False
    surface = attack_path.get("frontend_surface")
    if not isinstance(surface, dict):
        return False

    def has_evidence(node: object) -> bool:
        return isinstance(node, dict) and any(
            node.get(key) not in (None, "", [])
            for key in ("fact_id", "kind", "evidence_location", "method", "path")
        )

    return has_evidence(surface.get("browser_request")) and any(
        has_evidence(surface.get(key)) for key in ("ui_route", "ui_action")
    )


def _propose_mappings_for_lead(
    session: Session,
    campaign_id: int,
    lead: ScanLead,
    component_ids: set[int],
    targets: list[ApplicationTarget],
    mappings: list[LeadTargetMapping],
) -> None:
    try:
        attack_path = json.loads(lead.attack_path_json or "{}")
    except (TypeError, json.JSONDecodeError):
        attack_path = {}
    for target in targets:
        has_frontend_trace = _has_frontend_trace(attack_path)
        if (
            target.target_type == "site"
            and has_frontend_trace
            and not complete_path_can_map_to_site(attack_path, target.component_id)
        ):
            continue
        if (
            target.target_type == "site"
            and lead.producer_run_type == "campaign"
            and not has_frontend_trace
        ):
            # Site mappings come only from the role-aware frontend tracing
            # pipeline. Cross-service summaries remain available to API
            # targets and as correlation evidence, but cannot claim a browser
            # entrypoint or become web validation work.
            continue
        if (
            target.target_type == "api_collection"
            and isinstance(attack_path, dict)
            and attack_path.get("perspective") == "frontend"
        ):
            continue
        if lead.producer_run_type == "sast" and target.target_type == "site":
            path_lead_exists = session.exec(
                select(ScanLead.id)
                .where(ScanLead.producer_run_type == "campaign")
                .where(ScanLead.origin_lead_id == lead.id)
                .where(ScanLead.reportable == True)  # noqa: E712
            ).first()
            if path_lead_exists is not None:
                # The Site should investigate each frontend-rooted path rather
                # than receive an additional backend-only duplicate.
                continue
        score, rationale, evidence = _best_score_across_components(
            session, lead, component_ids, target
        )
        # A campaign-derived frontend path is safe to auto-route only when its
        # entire trace comes from the one component that owns the target.  A
        # path spanning repositories needs a reviewer to confirm the hop.
        owned_by_component = (
            len(component_ids) == 1 and target.component_id in component_ids
        )
        explicitly_owned = owned_by_component and (
            target.target_type == "api_collection"
            or (
                target.target_type == "site"
                and has_frontend_trace
                and (
                    lead.producer_run_type == "sast"
                    or (
                        lead.producer_run_type == "campaign"
                        and str(getattr(lead, "trace_status", "") or "") == "complete"
                        and not _lead_has_proof_gaps(lead)
                    )
                )
            )
        )
        if (
            owned_by_component
            and target.target_type == "site"
            and not has_frontend_trace
        ):
            # Keep useful ownership evidence visible for review, but do not
            # turn a backend lead into an approved browser path.
            score = max(score, 1.0)
            rationale = (
                "Component ownership suggests this site may be relevant, but "
                "no schema-v3 frontend trace proves a browser entrypoint."
            )
            evidence = {**evidence, "frontend_trace_required": True}
        elif explicitly_owned:
            score = max(score, 1.0)
            rationale = (
                "Explicit component ownership links this source lead to the "
                "selected live target; runtime path resolution is still required."
            )
            evidence = {
                **evidence,
                "explicit_component_ownership": True,
            }
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
            status=("approved" if explicitly_owned else "proposed"),
        )
        if hasattr(mapping, "path_json"):
            mapping.path_json = lead.attack_path_json or "{}"
        if hasattr(mapping, "approved_attack_path_json"):
            mapping.approved_attack_path_json = lead.attack_path_json or "{}"
        if hasattr(mapping, "path_status"):
            mapping.path_status = (
                getattr(lead, "trace_status", None)
                if has_frontend_trace
                else "unresolved"
            )
        if getattr(mapping, "status", "") == "approved":
            if hasattr(mapping, "auto_approved"):
                mapping.auto_approved = True
            mapping.reviewed_at = datetime.now(_UTC)
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
    from aespa.services import component_mapper

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
        if llm_match is None:
            for m in source_members:
                if m.sast_run_id:
                    component_mapper.purge_llm_component_facts(m.sast_run_id)
        connections = _build_component_connections(
            session, campaign_id, source_members, llm_match
        )
        cross_leads = _generate_cross_component_leads(session, campaign_id, connections)
        frontend_leads = _generate_frontend_path_leads(
            session, campaign_id, source_members
        )
        mappings = _propose_lead_target_mappings(
            session, campaign_id, source_members, target_members
        )
        session.commit()
        return {
            "connections": len(connections),
            "cross_component_leads": len(cross_leads) + len(frontend_leads),
            "lead_target_mappings": len(mappings),
        }


def rebuild_connections_deterministic(campaign_id: int) -> dict:
    """Rebuild only the application map without changing downstream review data."""
    from aespa.services import component_mapper

    with Session(get_engine()) as session:
        source_members = list(
            session.exec(
                select(CampaignSourceMember).where(
                    CampaignSourceMember.campaign_id == campaign_id
                )
            ).all()
        )
        for m in source_members:
            if m.sast_run_id:
                component_mapper.purge_llm_component_facts(m.sast_run_id)
        connections = _build_component_connections(
            session, campaign_id, source_members, None
        )
        session.commit()
        return {
            "connections": len(connections),
            "cross_component_leads": 0,
            "lead_target_mappings": 0,
        }


async def correlate_campaign_with_llm(
    campaign_id: int,
    *,
    stop_check=None,
    preserve_downstream: bool = False,
) -> dict:
    """Run source mapping, exact correlation, and bounded LLM disambiguation."""
    from aespa.services import component_mapper
    from aespa.services import llm as llm_svc
    from aespa.services.settings import (
        get_component_mapper_config,
        get_llm_config_for_role,
    )

    with events_svc.run_kind_scope("campaign"):
        llm_svc.set_run_context(
            campaign_id,
            lambda evt: events_svc.emit(campaign_id, evt),
            run_kind="campaign",
        )

        with Session(get_engine()) as session:
            campaign = session.get(AssessmentCampaign, campaign_id)
            if campaign is None:
                raise ValueError(f"Campaign {campaign_id} does not exist")
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
            for m in source_members:
                if m.sast_run_id:
                    component_mapper.purge_llm_component_facts(m.sast_run_id)
            llm_config = get_llm_config_for_role(session, campaign, "component_mapper")
            has_explicit_mapper_config = (
                campaign.llm_config_id is not None
                or campaign.llm_profile_id is not None
            )
            mapper_config = get_component_mapper_config(session)
            max_parallel = mapper_config.max_concurrent

            # A campaign continues with the source evidence it has when one
            # component scan fails. Do not ask the mapper to reopen a failed
            # SAST run: its extracted workspace may already have been cleaned
            # up, and one component must not prevent the other components from
            # reaching review.
            mappable_members = [
                member
                for member in source_members
                if member.sast_run_id is not None
                and (sast_run := session.get(SastRun, member.sast_run_id)) is not None
                and sast_run.status == "completed"
            ]
            skipped_members = len(source_members) - len(mappable_members)

        if llm_config is None:
            if not has_explicit_mapper_config:
                result = (
                    rebuild_connections_deterministic(campaign_id)
                    if preserve_downstream
                    else correlate_campaign(campaign_id)
                )
                events_svc.emit(
                    campaign_id,
                    {
                        "type": "scanner_phase",
                        "phase": "component_mapping",
                        "status": "warning",
                        "message": (
                            "No LLM mapping profile is configured; retained the "
                            "deterministic connection baseline."
                        ),
                        "data": result,
                    },
                )
                return result
            raise component_mapper.CorrelationTransientError(
                "No LLM configuration is available for component mapping."
            )

        events_svc.emit(
            campaign_id,
            {
                "type": "scanner_phase",
                "phase": "component_mapping",
                "status": "running",
                "message": (
                    f"Mapping interfaces for {len(mappable_members)} completed "
                    "component(s)."
                    if not skipped_members
                    else (
                        f"Mapping interfaces for {len(mappable_members)} completed "
                        f"component(s); skipped {skipped_members} unfinished "
                        "source scan(s)."
                    )
                ),
                "data": {
                    "components": len(mappable_members),
                    "skipped_components": skipped_members,
                },
            },
        )
        semaphore = asyncio.Semaphore(max_parallel)

        async def _map(
            member: CampaignSourceMember,
        ) -> component_mapper.ComponentMappingResult:
            async with semaphore:
                return await component_mapper.map_campaign_component(
                    campaign_id,
                    member.id,
                    llm_config=llm_config,
                    stop_check=stop_check,
                )

        mapping_tasks = [
            asyncio.create_task(_map(member), name=f"component-map-{member.id}")
            for member in mappable_members
        ]
        try:
            await asyncio.gather(*mapping_tasks)
        except BaseException:
            for task in mapping_tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*mapping_tasks, return_exceptions=True)
            raise
        if stop_check and stop_check():
            raise asyncio.CancelledError

        with Session(get_engine()) as session:
            connections = _build_component_connections(
                session, campaign_id, source_members, None
            )
            session.commit()
            ambiguous = _ambiguous_calls(session, source_members, connections)

        events_svc.emit(
            campaign_id,
            {
                "type": "scanner_phase",
                "phase": "component_mapping",
                "status": "complete",
                "message": (
                    f"Exact matching found {len(connections)} connection(s); "
                    f"{len(ambiguous)} unresolved candidate set(s) remain."
                ),
                "data": {
                    "deterministic_connections": len(connections),
                    "ambiguous_candidates": len(ambiguous),
                },
            },
        )
        try:
            proposals = await match_ambiguous_connections(
                llm_config,
                ambiguous,
                campaign_id=campaign_id,
                stop_check=stop_check,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            from aespa.services.component_mapper import CorrelationTransientError

            raise CorrelationTransientError(
                f"Ambiguous connection matching failed: {exc}"
            ) from exc
        if stop_check and stop_check():
            raise asyncio.CancelledError

        with Session(get_engine()) as session:
            source_by_fact: dict[int, ComponentFact] = {}
            route_by_fact: dict[int, ComponentFact] = {}
            for member in source_members:
                if member.sast_run_id is None:
                    continue
                facts = session.exec(
                    select(ComponentFact).where(
                        ComponentFact.sast_run_id == member.sast_run_id
                    )
                ).all()
                for fact in facts:
                    if fact.fact_type == "http_call":
                        source_by_fact[fact.id] = fact
                    elif fact.fact_type == "route":
                        route_by_fact[fact.id] = fact
            deterministic_call_ids = {
                connection.source_fact_id
                for connection in connections
                if getattr(connection, "edge_kind", "calls") == "calls"
            }
            seen_pairs: set[tuple[int, int]] = set()
            for proposal in proposals:
                pair = (proposal.call_id, proposal.route_id)
                if pair in seen_pairs or proposal.call_id in deterministic_call_ids:
                    continue
                call = source_by_fact.get(proposal.call_id)
                route = route_by_fact.get(proposal.route_id)
                if (
                    call is None
                    or route is None
                    or call.component_id == route.component_id
                ):
                    continue
                if proposal.confidence < 0.70:
                    continue
                evidence = {
                    **proposal.evidence,
                    "call": {
                        "method": call.method,
                        "path": call.path,
                        "host": call.host,
                        **_fact_evidence(call),
                    },
                    "route": {
                        "method": route.method,
                        "path": route.path,
                        **_fact_evidence(route),
                    },
                }
                session.add(
                    _make_connection(
                        campaign_id=campaign_id,
                        source=call,
                        target=route,
                        match_kind="llm_assisted",
                        confidence=proposal.confidence,
                        rationale=proposal.rationale,
                        evidence=evidence,
                        edge_kind="calls",
                    )
                )
                seen_pairs.add(pair)
            session.flush()
            all_connections = list(
                session.exec(
                    select(ComponentConnection).where(
                        ComponentConnection.campaign_id == campaign_id
                    )
                ).all()
            )
            if preserve_downstream:
                cross_leads = []
                frontend_leads = []
                mappings = []
            else:
                cross_leads = _generate_cross_component_leads(
                    session, campaign_id, all_connections
                )
                frontend_leads = _generate_frontend_path_leads(
                    session, campaign_id, source_members
                )
                mappings = _propose_lead_target_mappings(
                    session, campaign_id, source_members, target_members
                )
            session.commit()
            result = {
                "connections": len(all_connections),
                "cross_component_leads": len(cross_leads) + len(frontend_leads),
                "lead_target_mappings": len(mappings),
            }
        wording_warnings: list[str] = []
        if not preserve_downstream and frontend_leads:
            wording_warnings = await _rewrite_pre_crawl_frontend_paths(
                campaign_id,
                llm_config=llm_config,
            )
            if wording_warnings:
                with Session(get_engine()) as session:
                    campaign = session.get(AssessmentCampaign, campaign_id)
                    if campaign is not None:
                        try:
                            warnings = json.loads(campaign.warnings_json or "[]")
                        except (TypeError, json.JSONDecodeError):
                            warnings = []
                        warnings.extend(
                            warning
                            for warning in wording_warnings
                            if warning not in warnings
                        )
                        campaign.warnings_json = json.dumps(warnings[-50:])
                        session.add(campaign)
                        session.commit()
        if wording_warnings:
            events_svc.emit(
                campaign_id,
                {
                    "type": "scanner_phase",
                    "phase": "component_mapping",
                    "status": "warning",
                    "message": "Some frontend path wording remained deterministic.",
                    "data": {"warnings": wording_warnings},
                },
            )
        events_svc.emit(
            campaign_id,
            {
                "type": "scanner_phase",
                "phase": "component_mapping",
                "status": "complete",
                "message": (
                    f"Connection mapping complete: {result['connections']} connection(s)."
                ),
                "data": result,
            },
        )
        return result


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
            if approve:
                mapping.approved_attack_path_json = mapping.path_json or "{}"
                mapping.final_attack_path_json = mapping.approved_attack_path_json
                mapping.attack_path_changes_json = "[]"
                mapping.edited_at = now
            mapping.updated_at = now
            session.add(mapping)
        session.commit()
    return {"approved": approved, "rejected": rejected}


def edit_mapping_path(
    campaign_id: int,
    mapping_id: int,
    edited_path: dict,
    *,
    expected_updated_at: datetime | None = None,
) -> LeadTargetMapping:
    """Update only reviewer-editable frontend guidance for one mapping."""
    allowed = {
        "entry",
        "frontend_entrypoint",
        "request_transition",
        "hops",
        "prerequisites",
        "mutation_points",
        "proof_gaps",
        "dynamic_test",
        "impact",
        "severity_reasoning",
    }
    unknown = set(edited_path) - allowed
    if unknown:
        raise UnknownMappingError(
            "Only frontend path guidance may be edited: " + ", ".join(sorted(unknown))
        )
    with Session(get_engine()) as session:
        mapping = session.get(LeadTargetMapping, mapping_id)
        if mapping is None or mapping.campaign_id != campaign_id:
            raise UnknownMappingError(
                f"Mapping id={mapping_id} does not belong to this campaign"
            )
        if (
            expected_updated_at is not None
            and mapping.updated_at != expected_updated_at
        ):
            raise UnknownMappingError("Mapping was updated by another reviewer")
        try:
            current = json.loads(mapping.path_json or "{}")
        except (TypeError, json.JSONDecodeError):
            current = {}
        if not isinstance(current, dict):
            current = {}
        reviewer_fields = set(current.get("reviewer_supplied_fields") or [])
        for key, value in edited_path.items():
            current[key] = value
            reviewer_fields.add(key)
        current["reviewer_supplied_fields"] = sorted(reviewer_fields)
        mapping.path_json = json.dumps(current, separators=(",", ":"))
        mapping.edited_at = datetime.now(_UTC)
        mapping.updated_at = mapping.edited_at
        if mapping.status == "approved":
            mapping.approved_attack_path_json = mapping.path_json
            mapping.final_attack_path_json = mapping.path_json
        session.add(mapping)
        session.commit()
        session.refresh(mapping)
        return mapping


def copy_approved_mappings_for_target(
    campaign_id: int,
    target_id: int,
    run_type: str,
    run_id: int,
    *,
    mapping_ids: set[int] | None = None,
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
        if mapping_ids is not None:
            mappings = [mapping for mapping in mappings if mapping.id in mapping_ids]
        pending = [(m.id, m.lead_id) for m in mappings]
    for mapping_id, lead_id in pending:
        try:
            copy = copy_lead_to_run(lead_id, run_type, run_id)
        except ValueError:
            continue  # lead no longer eligible (e.g. dismissed) — skip it
        with Session(get_engine()) as session:
            mapping = session.get(LeadTargetMapping, mapping_id)
            if mapping is not None:
                approved_path = (
                    mapping.approved_attack_path_json
                    if getattr(mapping, "approved_attack_path_json", "{}")
                    not in ("", "{}")
                    else mapping.path_json
                )
                if run_type == "web" and approved_path and approved_path != "{}":
                    copied_row = session.get(ScanLead, copy.id)
                    if copied_row is not None:
                        copied_row.attack_path_json = approved_path
                        session.add(copied_row)
                mapping.copied_lead_id = copy.id
                mapping.updated_at = datetime.now(_UTC)
                session.add(mapping)
                session.commit()
        copied += 1
    return copied


def enrich_copied_web_leads_for_target(
    campaign_id: int,
    target_id: int,
    test_run_id: int,
    *,
    context: dict | None,
    warning: str | None = None,
) -> int:
    """Attach live crawl context to approved web lead copies only."""
    with Session(get_engine()) as session:
        mappings = session.exec(
            select(LeadTargetMapping)
            .where(LeadTargetMapping.campaign_id == campaign_id)
            .where(LeadTargetMapping.target_id == target_id)
            .where(LeadTargetMapping.status == "approved")
        ).all()
        mapping_lead_ids = [
            mapping.copied_lead_id
            for mapping in mappings
            if mapping.copied_lead_id is not None
        ]
        lead_ids = list(mapping_lead_ids)
        lead_ids.extend(
            lead.id
            for lead in session.exec(
                select(ScanLead)
                .where(ScanLead.imported_into_run_type == "web")
                .where(ScanLead.imported_into_run_id == test_run_id)
            ).all()
            if lead.id is not None
        )
        lead_ids = list(dict.fromkeys(lead_ids))
    updated = 0
    from aespa.services.scan_leads import set_final_frontend_path

    for mapping in mappings:
        if mapping.copied_lead_id is None:
            continue
        approved_path = (
            mapping.approved_attack_path_json
            if getattr(mapping, "approved_attack_path_json", "{}") not in ("", "{}")
            else mapping.path_json
        )
        try:
            path = json.loads(approved_path or "{}")
        except (TypeError, json.JSONDecodeError):
            path = {}
        if path and is_frontend_path(path):
            final_path = resolve_approved_path(path, context or {})
            if warning:
                final_path.setdefault("warnings", []).append(warning)
            if set_final_frontend_path(
                mapping.copied_lead_id, final_path=final_path, warning=warning
            ):
                with Session(get_engine()) as session:
                    current = session.get(LeadTargetMapping, mapping.id)
                    if current is not None:
                        current.final_attack_path_json = json.dumps(
                            final_path, separators=(",", ":")
                        )
                        current.attack_path_changes_json = json.dumps(
                            final_path.get("post_crawl_changes", []),
                            separators=(",", ":"),
                        )
                        current.path_status = final_path.get(
                            "live_frontend_context", {}
                        ).get("resolution_status")
                        session.add(current)
                        session.commit()
                updated += 1
    # Mapping copies already received an exact page/action/request resolution
    # above.  Do not replace that path with the bulk crawl inventory; only
    # non-mapping imports need the generic context warning.
    mapping_lead_id_set = set(mapping_lead_ids)
    for lead_id in lead_ids:
        if lead_id in mapping_lead_id_set:
            continue
        if (
            prepend_frontend_context_to_copied_lead(
                lead_id,
                context=context,
                warning=warning,
            )
            is not None
        ):
            updated += 1
    return updated


def propose_crawl_discovered_paths(
    campaign_id: int,
    target_id: int,
    *,
    context: dict | None,
) -> int:
    """Persist newly observed frontend entry paths as review-only proposals.

    Crawl artifacts can reveal a second page/action/request route for an
    already-approved SAST hypothesis.  The proposal is deliberately created
    after crawl and is never copied into the active run by this function.
    """
    live_context = context or {}
    pages = [item for item in live_context.get("pages", []) if isinstance(item, dict)]
    requests = [
        item for item in live_context.get("requests", []) if isinstance(item, dict)
    ]
    actions = [
        item for item in live_context.get("actions", []) if isinstance(item, dict)
    ]
    if not pages or not requests:
        return 0

    created = 0
    with Session(get_engine()) as session:
        approved = session.exec(
            select(LeadTargetMapping)
            .where(LeadTargetMapping.campaign_id == campaign_id)
            .where(LeadTargetMapping.target_id == target_id)
            .where(LeadTargetMapping.status == "approved")
        ).all()
        for mapping in approved:
            source = session.get(ScanLead, mapping.lead_id)
            if source is None or source.producer_run_type != "campaign":
                continue
            try:
                base_path = json.loads(
                    mapping.approved_attack_path_json or mapping.path_json or "{}"
                )
            except (TypeError, json.JSONDecodeError):
                continue
            if not isinstance(base_path, dict):
                continue
            existing_context = base_path.get("live_frontend_context")
            existing_request = (
                existing_context.get("request")
                if isinstance(existing_context, dict)
                else None
            )
            existing_request_key = (
                (
                    str(existing_request.get("method") or "").upper(),
                    str(existing_request.get("path") or ""),
                )
                if isinstance(existing_request, dict)
                else ("", "")
            )
            approved_transition = base_path.get("request_transition")
            if not isinstance(approved_transition, dict):
                approved_transition = {}
            approved_method = str(
                approved_transition.get("method") or existing_request_key[0] or ""
            ).upper()
            approved_path = str(
                approved_transition.get("path") or existing_request_key[1] or ""
            )

            def _route_key(value: str) -> str:
                parsed = urlparse(str(value or ""))
                return parsed.path.rstrip("/") or "/"

            for page in pages[:40]:
                page_id = page.get("id")
                page_route = str(page.get("route") or page.get("url") or "")
                if not page_route:
                    continue
                page_requests = [
                    item for item in requests if item.get("page_id") == page_id
                ][:10]
                for request in page_requests:
                    request_key = (
                        str(request.get("method") or "").upper(),
                        str(request.get("url") or ""),
                    )
                    if request_key == existing_request_key:
                        continue
                    # A crawl alternative is useful only when it observed the
                    # same backend operation as the approved trace.  Unrelated
                    # page traffic stays in the crawl inventory and is never
                    # turned into a vulnerability-specific proposal.
                    if approved_method and request_key[0] != approved_method:
                        continue
                    if approved_path and _route_key(request_key[1]) != _route_key(
                        approved_path
                    ):
                        continue
                    action = next(
                        (item for item in actions if item.get("page_id") == page_id),
                        None,
                    )
                    evidence_ids = [
                        value
                        for value in (
                            f"page:{page_id}" if page_id is not None else None,
                            (
                                f"traffic:{request['id']}"
                                if request.get("id") is not None
                                else None
                            ),
                            (
                                f"action:{action['id']}"
                                if action and action.get("id") is not None
                                else None
                            ),
                        )
                        if value
                    ]
                    path_key = hashlib.sha256(
                        "|".join(
                            [
                                str(source.trace_path_key or source.fingerprint),
                                page_route,
                                request_key[0],
                                request_key[1],
                            ]
                        ).encode("utf-8")
                    ).hexdigest()
                    if path_key == source.trace_path_key:
                        continue
                    fingerprint = lead_fingerprint(
                        category=source.category,
                        title=f"Crawl path: {source.title}:{path_key}",
                        location=f"{page_route} -> {request.get('url', '')}",
                    )
                    discovered = deepcopy(base_path)
                    discovered["live_frontend_context"] = {
                        "resolution_status": "live_resolved",
                        "crawl_status": live_context.get("crawl_status", "unknown"),
                        "url": page.get("url", ""),
                        "route": page_route,
                        "action": (
                            action.get("label") or action.get("action_kind")
                            if action
                            else None
                        ),
                        "trigger": action.get("action_kind") if action else "page_load",
                        "request": {
                            "method": request_key[0],
                            "path": request.get("url", ""),
                            "mutation_points": request.get("fields", []),
                        },
                        "evidence_ids": evidence_ids,
                    }
                    discovered["post_crawl_changes"] = []
                    discovered["dynamic_test"] = (
                        f"From {page_route}, reproduce the observed frontend action "
                        f"and verify the vulnerability at "
                        f"{request_key[0]} {request.get('url', '')}."
                    )
                    exists = session.exec(
                        select(ScanLead).where(
                            ScanLead.producer_run_type == "campaign",
                            ScanLead.producer_run_id == campaign_id,
                            ScanLead.fingerprint == fingerprint,
                        )
                    ).first()
                    if exists is not None:
                        continue
                    lead = ScanLead(
                        producer_run_type="campaign",
                        producer_run_id=campaign_id,
                        source="crawl",
                        category=source.category,
                        severity=source.severity,
                        confidence=source.confidence,
                        title=f"Crawl path: {source.title}",
                        description=(
                            f"{source.description}\n\n"
                            "This path was discovered from persisted crawl evidence "
                            "after the initial SAST path review."
                        ),
                        location=f"{page_route} -> {request.get('url', '')}",
                        evidence=source.evidence,
                        fingerprint=fingerprint,
                        suggested_endpoint=source.suggested_endpoint,
                        source_trace_json=source.source_trace_json,
                        control_trace_json=source.control_trace_json,
                        sink_trace_json=source.sink_trace_json,
                        proof_gaps_json=source.proof_gaps_json,
                        attack_path_json=json.dumps(discovered, separators=(",", ":")),
                        reportable=True,
                        validation_status="pending",
                        origin_lead_id=source.origin_lead_id or source.id,
                        trace_path_key=path_key,
                        trace_status="live_resolved",
                        trace_confidence=source.trace_confidence or source.confidence,
                    )
                    session.add(lead)
                    session.flush()
                    ensure_lead_reference(session, lead)
                    session.add(
                        LeadTargetMapping(
                            campaign_id=campaign_id,
                            lead_id=lead.id,
                            target_id=target_id,
                            target_type=mapping.target_type,
                            score=0.5,
                            rationale=(
                                "Crawl evidence discovered a new frontend entry "
                                "path; reviewer approval is required."
                            ),
                            evidence_json=json.dumps(
                                {"evidence_ids": evidence_ids}, separators=(",", ":")
                            ),
                            status="proposed",
                            path_json=json.dumps(discovered, separators=(",", ":")),
                            path_status="live_resolved",
                        )
                    )
                    created += 1
                    break
                if created >= 10:
                    break
            if created >= 10:
                break
        session.commit()
    return created


async def enrich_copied_web_leads_for_target_with_llm(
    campaign_id: int,
    target_id: int,
    test_run_id: int,
    *,
    context: dict | None,
    warning: str | None = None,
    llm_config=None,
) -> tuple[int, list[str]]:
    """Resolve copied paths, then apply an evidence-bounded campaign rewrite."""
    updated = enrich_copied_web_leads_for_target(
        campaign_id,
        target_id,
        test_run_id,
        context=context,
        warning=warning,
    )
    if llm_config is None:
        return updated, []

    warnings: list[str] = []
    with Session(get_engine()) as session:
        mappings = session.exec(
            select(LeadTargetMapping)
            .where(LeadTargetMapping.campaign_id == campaign_id)
            .where(LeadTargetMapping.target_id == target_id)
            .where(LeadTargetMapping.status == "approved")
        ).all()
        mapping_data = [
            (
                mapping.id,
                mapping.copied_lead_id,
                mapping.approved_attack_path_json or mapping.path_json,
                mapping.final_attack_path_json,
            )
            for mapping in mappings
            if mapping.copied_lead_id is not None
        ]

    for mapping_id, copied_lead_id, approved_json, final_json in mapping_data:
        try:
            approved_path = json.loads(approved_json or "{}")
            final_path = json.loads(final_json or "{}")
        except (TypeError, json.JSONDecodeError):
            continue
        if not isinstance(approved_path, dict) or not isinstance(final_path, dict):
            continue
        if not is_frontend_path(approved_path):
            continue
        revised, rewrite_warning = await revise_path_with_llm(
            approved_path,
            final_path,
            llm_config,
        )
        if rewrite_warning:
            warnings.append(f"Mapping {mapping_id}: {rewrite_warning}")
            continue
        if revised == final_path:
            continue
        set_final_frontend_path(
            copied_lead_id,
            final_path=revised,
            warning=warning,
        )
        with Session(get_engine()) as session:
            mapping = session.get(LeadTargetMapping, mapping_id)
            if mapping is None:
                continue
            mapping.final_attack_path_json = json.dumps(revised, separators=(",", ":"))
            mapping.attack_path_changes_json = json.dumps(
                revised.get("post_crawl_changes", []),
                separators=(",", ":"),
            )
            session.add(mapping)
            session.commit()
        updated += 1
    return updated, warnings


def copy_explicit_component_leads_for_target(
    campaign_id: int, target_id: int, run_type: str, run_id: int
) -> int:
    """Copy leads for the component explicitly assigned to this live target.

    The assignment is optional and scoped to the campaign's frozen source
    member. Only original, reportable SAST leads from that exact member are
    copied; inferred and campaign-owned cross-component leads remain subject
    to the normal review gate.
    """
    with Session(get_engine()) as session:
        target = session.get(ApplicationTarget, target_id)
        if target is None or target.component_id is None:
            return 0
        member = session.exec(
            select(CampaignSourceMember)
            .where(CampaignSourceMember.campaign_id == campaign_id)
            .where(CampaignSourceMember.component_id == target.component_id)
        ).first()
        if member is None or member.sast_run_id is None:
            return 0
        sast_run_id = member.sast_run_id
        path_origin_ids = {
            lead.origin_lead_id
            for lead in session.exec(
                select(ScanLead)
                .where(ScanLead.producer_run_type == "campaign")
                .where(ScanLead.producer_run_id == campaign_id)
                .where(ScanLead.origin_lead_id != None)  # noqa: E711
            ).all()
            if lead.origin_lead_id is not None
        }
        original_ids = [
            lead.id
            for lead in session.exec(
                select(ScanLead)
                .where(ScanLead.producer_run_type == "sast")
                .where(ScanLead.producer_run_id == sast_run_id)
                .where(ScanLead.imported_into_run_id == None)  # noqa: E711
                .where(ScanLead.reportable == True)  # noqa: E712
            ).all()
            if lead.id is not None and lead.id not in path_origin_ids
        ]
    copied = 0
    for lead_id in original_ids:
        try:
            copy_lead_to_run(lead_id, run_type, run_id)
        except ValueError:
            continue
        copied += 1
    return copied
