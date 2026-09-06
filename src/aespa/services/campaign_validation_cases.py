"""Storage and readiness lifecycle for campaign validation cases.

Mappings are review records.  Validation cases are the executable records that
are allowed to enter a child run.  Keeping this boundary in one service makes
the campaign runner safe to retry and keeps API responses from exposing the
JSON column details to callers.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import (
    ApiEndpoint,
    ApplicationTarget,
    CampaignTargetMember,
    CampaignValidationCase,
    LeadTargetMapping,
    ScanFinding,
    ScanLead,
)

READINESS_PENDING = "pending"
READINESS_RESOLVED = "resolved"
READINESS_STATIC_COMPLETE = "static_complete"
READINESS_AMBIGUOUS = "ambiguous"
READINESS_MISSING_FRONTEND_HOP = "missing_frontend_hop"
READINESS_MISSING_BACKEND_HOP = "missing_backend_hop"
READINESS_MISSING_PREREQUISITE = "missing_prerequisite"
READINESS_WRONG_TARGET = "wrong_target"
READINESS_CRAWL_FAILED = "crawl_failed"
READINESS_LEGACY_UNRESOLVED = "legacy_unresolved"

EXECUTION_NOT_QUEUED = "not_queued"
EXECUTION_QUEUED = "queued"
EXECUTION_RUNNING = "running"
EXECUTION_CONFIRMED = "confirmed"
EXECUTION_DISMISSED = "dismissed"
EXECUTION_INCONCLUSIVE = "inconclusive"
EXECUTION_SKIPPED = "skipped"

OUTCOME_CONFIRMED = "confirmed"
OUTCOME_SECURE_BEHAVIOR = "secure_behavior_observed"
OUTCOME_STALE_PATH = "stale_path"
OUTCOME_MISSING_RUNTIME_PREREQUISITE = "missing_runtime_prerequisite"
OUTCOME_INSUFFICIENT_CONSEQUENCE_EVIDENCE = "insufficient_consequence_evidence"
OUTCOME_EXECUTION_FAILED = "execution_failed"
OUTCOME_REASONS = frozenset(
    {
        OUTCOME_CONFIRMED,
        OUTCOME_SECURE_BEHAVIOR,
        OUTCOME_STALE_PATH,
        OUTCOME_MISSING_RUNTIME_PREREQUISITE,
        OUTCOME_INSUFFICIENT_CONSEQUENCE_EVIDENCE,
        OUTCOME_EXECUTION_FAILED,
    }
)

READINESS_STATUSES = frozenset(
    {
        READINESS_PENDING,
        READINESS_RESOLVED,
        READINESS_STATIC_COMPLETE,
        READINESS_AMBIGUOUS,
        READINESS_MISSING_FRONTEND_HOP,
        READINESS_MISSING_BACKEND_HOP,
        READINESS_MISSING_PREREQUISITE,
        READINESS_WRONG_TARGET,
        READINESS_CRAWL_FAILED,
        READINESS_LEGACY_UNRESOLVED,
    }
)
EXECUTION_STATUSES = frozenset(
    {
        EXECUTION_NOT_QUEUED,
        EXECUTION_QUEUED,
        EXECUTION_RUNNING,
        EXECUTION_CONFIRMED,
        EXECUTION_DISMISSED,
        EXECUTION_INCONCLUSIVE,
        EXECUTION_SKIPPED,
    }
)

_UTC = timezone.utc
_REDACT_KEYS = {
    "authorization",
    "authorization_header",
    "api_key",
    "api-key",
    "access_token",
    "refresh_token",
    "cookie",
    "cookies",
    "headers",
    "password",
    "secret",
    "token",
    "raw_request",
    "set-cookie",
}


@dataclass
class ResolutionSummary:
    """Counts and row ids returned after a target resolution pass."""

    counts: dict[str, int] = field(default_factory=dict)
    case_ids: list[int] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class CompilationSummary:
    """Counts and row ids returned after copying runnable cases."""

    counts: dict[str, int] = field(default_factory=dict)
    execution_counts: dict[str, int] = field(default_factory=dict)
    case_ids: list[int] = field(default_factory=list)
    copied_lead_ids: list[int] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _json(value: Any, default: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if not value:
        return default
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return default
    return parsed if isinstance(parsed, type(default)) else default


def _dump(value: Any, default: Any) -> str:
    return json.dumps(value if value is not None else default, separators=(",", ":"))


def _redact(value: Any) -> Any:
    """Remove credential-shaped keys from data returned by the API."""
    if isinstance(value, dict):
        return {
            key: _redact(item)
            for key, item in value.items()
            if str(key).casefold() not in _REDACT_KEYS
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _path_for_mapping(mapping: LeadTargetMapping) -> dict:
    raw = mapping.final_attack_path_json or mapping.approved_attack_path_json
    if not raw or raw == "{}":
        raw = mapping.path_json
    path = _json(raw, {})
    return path if isinstance(path, dict) else {}


def _assertion_for_path(path: dict) -> dict:
    assertion = path.get("validation_assertion", {})
    if not isinstance(assertion, dict):
        assertion = {}
    return {
        "claim": str(assertion.get("claim", "")),
        "mutation_points": assertion.get("mutation_points", [])
        if isinstance(assertion.get("mutation_points", []), list)
        else [],
        "secure_outcome": str(assertion.get("secure_outcome", "")),
        "vulnerable_outcome": str(assertion.get("vulnerable_outcome", "")),
        "prerequisites": assertion.get("prerequisites", [])
        if isinstance(assertion.get("prerequisites", []), list)
        else [],
    }


def _assertion_key(path: dict) -> str:
    assertion = _assertion_for_path(path)
    supplied = path.get("assertion_key") or assertion.get("key")
    if supplied:
        return str(supplied)[:200]
    # One case per mapping is the initial contract.  A stable default leaves
    # room for additional assertion keys without changing old rows.
    return "default"


def _normalise_binding(binding: Any) -> dict:
    if not isinstance(binding, dict):
        return {"status": READINESS_PENDING}
    result = dict(binding)
    result["status"] = str(result.get("status", READINESS_PENDING))
    if result["status"] not in READINESS_STATUSES:
        result["status"] = READINESS_PENDING
    result["candidate_count"] = int(result.get("candidate_count", 0) or 0)
    evidence_ids = result.get("evidence_ids", [])
    if not isinstance(evidence_ids, list):
        evidence_ids = [evidence_ids] if evidence_ids else []
    result["evidence_ids"] = [str(item) for item in evidence_ids]
    return result


def _binding_for_mapping(live_context: dict | None, mapping_id: int) -> dict:
    if not isinstance(live_context, dict):
        return {"status": READINESS_PENDING}
    for key in ("bindings", "resolutions", "cases"):
        values = live_context.get(key)
        if isinstance(values, dict):
            value = values.get(mapping_id, values.get(str(mapping_id)))
            if value is not None:
                return _normalise_binding(value)
        elif isinstance(values, list):
            for value in values:
                if isinstance(value, dict) and value.get("mapping_id") == mapping_id:
                    return _normalise_binding(value)
    if live_context.get("mapping_id") in (mapping_id, str(mapping_id)):
        return _normalise_binding(live_context)
    return _normalise_binding(live_context) if "status" in live_context else {
        "status": READINESS_PENDING
    }


def _static_status(path: dict, *, web: bool) -> tuple[str, list[str]]:
    if not path:
        return READINESS_MISSING_FRONTEND_HOP if web else READINESS_MISSING_BACKEND_HOP, [
            "static_path_missing"
        ]
    trace = path.get("static_trace", {})
    trace_status = trace.get("status") if isinstance(trace, dict) else None
    if trace_status not in (None, "complete"):
        return READINESS_MISSING_BACKEND_HOP, ["static_trace_incomplete"]
    if web:
        surface = path.get("frontend_surface", {})
        request = surface.get("browser_request") if isinstance(surface, dict) else None
        if not isinstance(surface, dict) or not isinstance(request, dict) or not request:
            return READINESS_MISSING_FRONTEND_HOP, ["browser_request_missing"]
        if not path.get("vulnerability_anchor") and not path.get("source_finding"):
            return READINESS_MISSING_BACKEND_HOP, ["vulnerability_anchor_missing"]
    return READINESS_PENDING, []


def upsert_validation_case(
    session: Session,
    mapping: LeadTargetMapping,
    target_member: CampaignTargetMember,
    *,
    readiness_status: str = READINESS_PENDING,
    static_path: dict | None = None,
    live_binding: dict | None = None,
    blocker_codes: list[str] | None = None,
    assertion_key: str | None = None,
) -> CampaignValidationCase:
    """Create or update the one case for a mapping and target member."""
    if readiness_status not in READINESS_STATUSES:
        raise ValueError(f"Unknown validation readiness status: {readiness_status}")
    path = static_path if isinstance(static_path, dict) else _path_for_mapping(mapping)
    key = assertion_key or _assertion_key(path)
    case = session.exec(
        select(CampaignValidationCase)
        .where(CampaignValidationCase.mapping_id == mapping.id)
        .where(CampaignValidationCase.target_member_id == target_member.id)
        .where(CampaignValidationCase.assertion_key == key)
    ).first()
    now = datetime.now(_UTC)
    if case is None:
        case = CampaignValidationCase(
            campaign_id=mapping.campaign_id,
            mapping_id=mapping.id,
            target_member_id=target_member.id,
            origin_lead_id=mapping.lead_id,
            assertion_key=key,
            execution_status=EXECUTION_NOT_QUEUED,
            created_at=now,
        )
    elif readiness_status != READINESS_RESOLVED and case.copied_lead_id is not None:
        copied = session.get(ScanLead, case.copied_lead_id)
        if copied is not None and copied.status in {"open", "investigating"}:
            # An unexecuted copy is only a queue artifact. Remove it when its
            # crawl binding becomes stale or unresolved so the child scanner
            # cannot consume work that no longer passes the readiness gate.
            mapping.copied_lead_id = None
            case.copied_lead_id = None
            case.execution_status = EXECUTION_NOT_QUEUED
            session.add(mapping)
            session.flush()
            session.delete(copied)
    case.static_path_json = _dump(_redact(path), {})
    case.live_binding_json = _dump(_redact(_normalise_binding(live_binding or {})), {})
    case.readiness_status = readiness_status
    case.blocker_codes_json = _dump(blocker_codes or [], [])
    case.updated_at = now
    session.add(case)
    session.flush()
    return case


def _approved_mappings(
    session: Session,
    campaign_id: int,
    target_member_id: int,
    mapping_ids: set[int] | None = None,
):
    target_member = session.get(CampaignTargetMember, target_member_id)
    if target_member is None or target_member.campaign_id != campaign_id:
        raise ValueError("Target member does not belong to campaign")
    mappings = session.exec(
        select(LeadTargetMapping)
        .where(LeadTargetMapping.campaign_id == campaign_id)
        .where(LeadTargetMapping.target_id == target_member.target_id)
        .where(LeadTargetMapping.status == "approved")
        .order_by(LeadTargetMapping.id)
    ).all()
    if mapping_ids is not None:
        mappings = [mapping for mapping in mappings if mapping.id in mapping_ids]
    return target_member, mappings


def _summary(cases: list[CampaignValidationCase], warnings: list[str] | None = None):
    counts: dict[str, int] = {}
    for case in cases:
        counts[case.readiness_status] = counts.get(case.readiness_status, 0) + 1
    return counts, [case.id for case in cases if case.id is not None], warnings or []


def create_pending_cases(campaign_id: int, target_member_id: int) -> ResolutionSummary:
    """Create pending cases for all approved mappings of a target."""
    with Session(get_engine()) as session:
        _target, mappings = _approved_mappings(session, campaign_id, target_member_id)
        cases = [
            upsert_validation_case(session, mapping, _target)
            for mapping in mappings
        ]
        session.commit()
        counts, ids, warnings = _summary(cases)
    return ResolutionSummary(counts, ids, warnings)


def resolve_cases_for_web_target(
    campaign_id: int,
    target_member_id: int,
    test_run_id: int,
    live_context: dict,
    *,
    mapping_ids: set[int] | None = None,
) -> ResolutionSummary:
    """Persist resolver results for approved mappings on a web child run."""
    from aespa.services.frontend_path_resolver import resolve_frontend_path

    with Session(get_engine()) as session:
        target_member, mappings = _approved_mappings(
            session, campaign_id, target_member_id, mapping_ids
        )
        if target_member.target_type != "site":
            raise ValueError("Target member is not a Site target")
        if target_member.test_run_id not in (None, test_run_id):
            raise ValueError("Test run does not belong to target member")
        if target_member.test_run_id is None:
            target_member.test_run_id = test_run_id
            session.add(target_member)
        cases: list[CampaignValidationCase] = []
        for mapping in mappings:
            path = _path_for_mapping(mapping)
            static_status, blockers = _static_status(path, web=True)
            # Historical paths have no v3 role information. Keep them visible
            # for review, but never make them runnable from current crawl data.
            if path.get("schema_version") != 3:
                status = READINESS_LEGACY_UNRESOLVED
                binding = {"status": status, "candidate_count": 0}
                blockers = ["legacy_path_requires_rebuild"]
            else:
                # The resolver owns candidate selection. Callers pass one
                # bounded crawl context rather than pre-selecting a request.
                context_for_mapping = live_context
                if isinstance(live_context, dict):
                    supplied = _binding_for_mapping(live_context, mapping.id)
                    if any(
                        key in live_context for key in ("bindings", "resolutions", "cases")
                    ):
                        # Backward-compatible support for orchestrators that have
                        # already resolved a binding.
                        binding = supplied
                    else:
                        binding = _normalise_binding(
                            resolve_frontend_path(path, context_for_mapping)
                        )
                else:
                    binding = _normalise_binding(
                        resolve_frontend_path(path, context_for_mapping)
                    )
            raw_binding = binding.get("binding")
            if isinstance(raw_binding, dict):
                page = raw_binding.get("page") or {}
                action = raw_binding.get("action") or {}
                request = raw_binding.get("request") or {}
                binding = {
                    "status": binding.get("status", READINESS_PENDING),
                    "candidate_count": binding.get("candidate_count", 1),
                    "page_id": page.get("id"),
                    "action_id": action.get("id"),
                    "traffic_id": request.get("id"),
                    "interaction_id": request.get("interaction_id"),
                    "session_label": request.get("session_label"),
                    "observed_request": {
                        "method": str(request.get("method") or "").upper(),
                        "path": request.get("url") or request.get("path") or "",
                        "fields": request.get("fields", []),
                    },
                    "evidence_ids": [
                        f"page:{page['id']}" if page.get("id") is not None else None,
                        f"action:{action['id']}" if action.get("id") is not None else None,
                        f"traffic:{request['id']}" if request.get("id") is not None else None,
                    ],
                }
                binding["evidence_ids"] = [
                    item for item in binding["evidence_ids"] if item
                ]
            status = binding.get("status", READINESS_PENDING)
            if status == "unavailable":
                status = (
                    READINESS_LEGACY_UNRESOLVED
                    if path.get("schema_version") != 3
                    else READINESS_MISSING_FRONTEND_HOP
                )
                blockers = ["browser_request_unavailable"]
            if static_status != READINESS_PENDING:
                status = static_status
            elif status == READINESS_RESOLVED:
                blockers = list(binding.get("blocker_codes", blockers))
            elif status in READINESS_STATUSES:
                blockers = list(binding.get("blocker_codes", blockers))
            else:
                status = READINESS_PENDING
            case = upsert_validation_case(
                session,
                mapping,
                target_member,
                readiness_status=status,
                static_path=path,
                live_binding=binding,
                blocker_codes=blockers,
            )
            cases.append(case)
        session.commit()
        counts, ids, warnings = _summary(cases)
    return ResolutionSummary(counts, ids, warnings)


def _endpoint_path(path: dict) -> tuple[str | None, str | None]:
    surface = path.get("frontend_surface", {})
    request = surface.get("browser_request", {}) if isinstance(surface, dict) else {}
    hops = path.get("service_hops", [])
    candidates = [
        item
        for item in hops
        if isinstance(item, dict)
        and item.get("request_role") in {"server_ingress", "server_egress", None}
    ] if isinstance(hops, list) else []
    candidates.append(request)
    transition = path.get("request_transition")
    if isinstance(transition, dict):
        candidates.append(transition)
    backend_route = path.get("backend_route")
    if isinstance(backend_route, dict):
        candidates.append(backend_route)
    frontend = path.get("frontend_entrypoint")
    if isinstance(frontend, dict):
        candidates.append(frontend)
    for item in candidates:
        method = item.get("method")
        route = item.get("path")
        if method and route:
            return str(method).upper(), str(route)
    return None, None


def _api_path_matches(observed: str, candidate: str) -> bool:
    """Match API paths after URL, trailing-slash, and template normalization."""
    left = (urlparse(observed).path or observed).rstrip("/") or "/"
    right = (urlparse(candidate).path or candidate).rstrip("/") or "/"
    if left == right:
        return True
    left_parts = left.strip("/").split("/") if left != "/" else []
    right_parts = right.strip("/").split("/") if right != "/" else []
    if len(left_parts) != len(right_parts):
        return False
    return all(
        left_part == right_part
        or (left_part.startswith("{") and left_part.endswith("}"))
        or (right_part.startswith("{") and right_part.endswith("}"))
        for left_part, right_part in zip(left_parts, right_parts)
    )


def resolve_cases_for_api_target(
    campaign_id: int,
    target_member_id: int,
    api_test_run_id: int,
    *,
    mapping_ids: set[int] | None = None,
) -> ResolutionSummary:
    """Resolve approved cases by matching their route to an ApiEndpoint."""
    with Session(get_engine()) as session:
        target_member, mappings = _approved_mappings(
            session, campaign_id, target_member_id, mapping_ids
        )
        if target_member.target_type != "api_collection":
            raise ValueError("Target member is not an API collection target")
        if target_member.api_test_run_id not in (None, api_test_run_id):
            raise ValueError("API test run does not belong to target member")
        if target_member.api_test_run_id is None:
            target_member.api_test_run_id = api_test_run_id
            session.add(target_member)
        target = session.get(ApplicationTarget, target_member.target_id)
        if target is None:
            raise ValueError("Application target does not exist")
        endpoints = session.exec(
            select(ApiEndpoint)
            .where(ApiEndpoint.collection_id == target.target_id)
            .where(ApiEndpoint.in_scope == True)  # noqa: E712
        ).all()
        cases: list[CampaignValidationCase] = []
        for mapping in mappings:
            path = _path_for_mapping(mapping)
            method, route = _endpoint_path(path)
            endpoint = next(
                (
                    item
                    for item in endpoints
                    if item.method.upper() == method
                    and _api_path_matches(item.path, route)
                ),
                None,
            )
            blockers: list[str] = []
            if endpoint is None:
                readiness = READINESS_MISSING_BACKEND_HOP
                blockers.append("api_endpoint_missing")
                binding = {"status": readiness, "candidate_count": 0}
            elif not endpoint.prereq_can_test or (
                endpoint.auth_required and not endpoint.prereq_can_test_auth
            ):
                readiness = READINESS_MISSING_PREREQUISITE
                blockers.extend(_json(endpoint.prereq_notes, []))
                if not blockers:
                    blockers.append("endpoint_prerequisite_missing")
                binding = {
                    "status": readiness,
                    "endpoint_id": endpoint.id,
                    "evidence_ids": [f"endpoint:{endpoint.id}"],
                }
            else:
                readiness = READINESS_RESOLVED
                binding = {
                    "status": readiness,
                    "endpoint_id": endpoint.id,
                    "observed_request": {"method": method, "path": route},
                    "evidence_ids": [f"endpoint:{endpoint.id}"],
                }
            cases.append(
                upsert_validation_case(
                    session,
                    mapping,
                    target_member,
                    readiness_status=readiness,
                    static_path=path,
                    live_binding=binding,
                    blocker_codes=blockers,
                )
            )
        session.commit()
        counts, ids, warnings = _summary(cases)
    return ResolutionSummary(counts, ids, warnings)


def _copy_attack_path(case: CampaignValidationCase) -> dict:
    path = _json(case.static_path_json, {})
    if not isinstance(path, dict):
        path = {}
    path = dict(path)
    path["schema_version"] = max(int(path.get("schema_version", 3) or 3), 3)
    path["live_binding"] = _json(case.live_binding_json, {})
    path["validation_assertion"] = _assertion_for_path(path)
    path["validation_case_id"] = case.id
    return path


def compile_runnable_cases(
    campaign_id: int,
    target_member_id: int,
    *,
    mapping_ids: set[int] | None = None,
) -> CompilationSummary:
    """Copy each resolved case once into its target child run."""
    from aespa.services.scan_leads import copy_lead_to_run

    with Session(get_engine()) as session:
        target_member = session.get(CampaignTargetMember, target_member_id)
        if target_member is None or target_member.campaign_id != campaign_id:
            raise ValueError("Target member does not belong to campaign")
        run_type = "web" if target_member.target_type == "site" else "api"
        run_id = target_member.test_run_id if run_type == "web" else target_member.api_test_run_id
        if run_id is None:
            raise ValueError("Target child run does not exist")
        cases = session.exec(
            select(CampaignValidationCase)
            .where(CampaignValidationCase.campaign_id == campaign_id)
            .where(CampaignValidationCase.target_member_id == target_member_id)
            .where(CampaignValidationCase.readiness_status == READINESS_RESOLVED)
            .order_by(CampaignValidationCase.id)
        ).all()
        if mapping_ids is not None:
            cases = [case for case in cases if case.mapping_id in mapping_ids]
        warnings: list[str] = []
        copied_ids: list[int] = []
        for case in cases:
            if case.copied_lead_id is not None:
                copied = session.get(ScanLead, case.copied_lead_id)
                if copied is not None:
                    execution_status = {
                        "open": EXECUTION_QUEUED,
                        "investigating": EXECUTION_RUNNING,
                        "confirmed": EXECUTION_CONFIRMED,
                        "dismissed": EXECUTION_DISMISSED,
                        "inconclusive": EXECUTION_INCONCLUSIVE,
                    }.get(copied.status, case.execution_status)
                    case.execution_status = execution_status
                    if copied.status in {"open", "investigating"}:
                        copied_ids.append(copied.id)
                    if copied.status in {"open", "investigating"}:
                        copied.attack_path_json = _dump(_copy_attack_path(case), {})
                        session.add(copied)
                    session.add(case)
                    continue
                case.copied_lead_id = None
            try:
                copied = copy_lead_to_run(case.origin_lead_id, run_type, run_id)
            except ValueError as exc:
                warnings.append(f"case {case.id}: {exc}")
                case.execution_status = EXECUTION_SKIPPED
                session.add(case)
                continue
            case.copied_lead_id = copied.id
            case.execution_status = EXECUTION_QUEUED
            copied_ids.append(copied.id)
            # ``copy_lead_to_run`` returns an expunged object. Reload it in
            # this session before attaching the exact case replay path.
            copied_row = session.get(ScanLead, copied.id)
            if copied_row is not None:
                copied_row.attack_path_json = _dump(_copy_attack_path(case), {})
                session.add(copied_row)
            mapping = session.get(LeadTargetMapping, case.mapping_id)
            if mapping is not None:
                mapping.copied_lead_id = copied.id
                mapping.updated_at = datetime.now(_UTC)
                session.add(mapping)
            session.add(case)
        session.commit()
        counts: dict[str, int] = {}
        execution_counts: dict[str, int] = {}
        for case in cases:
            counts[case.readiness_status] = counts.get(case.readiness_status, 0) + 1
            execution_counts[case.execution_status] = (
                execution_counts.get(case.execution_status, 0) + 1
            )
        case_ids = [case.id for case in cases if case.id is not None]
    return CompilationSummary(counts, execution_counts, case_ids, copied_ids, warnings)


def sync_case_outcome_from_lead(
    copied_lead_id: int,
    *,
    outcome_reason: str | None = None,
    baseline_evidence: Any = None,
    mutated_evidence: Any = None,
) -> None:
    """Mirror a copied lead's outcome into its validation case.

    Outcome metadata is passed separately from ``ScanLead.note`` because that
    field is free-form user-facing text and must remain backwards compatible.
    """
    with Session(get_engine()) as session:
        case = session.exec(
            select(CampaignValidationCase).where(
                CampaignValidationCase.copied_lead_id == copied_lead_id
            )
        ).first()
        lead = session.get(ScanLead, copied_lead_id)
        if case is None or lead is None:
            return
        status_map = {
            "investigating": EXECUTION_RUNNING,
            "confirmed": EXECUTION_CONFIRMED,
            "dismissed": EXECUTION_DISMISSED,
            "inconclusive": EXECUTION_INCONCLUSIVE,
        }
        case.execution_status = status_map.get(lead.status, case.execution_status)
        case.finding_id = lead.linked_finding_id
        if outcome_reason in OUTCOME_REASONS:
            case.outcome_reason = outcome_reason
        if baseline_evidence is not None:
            case.baseline_evidence_json = _dump(
                baseline_evidence
                if isinstance(baseline_evidence, dict)
                else {"summary": str(baseline_evidence)[:4000]},
                {},
            )
        if mutated_evidence is not None:
            case.mutated_evidence_json = _dump(
                mutated_evidence
                if isinstance(mutated_evidence, dict)
                else {"summary": str(mutated_evidence)[:4000]},
                {},
            )
        case.updated_at = datetime.now(_UTC)
        session.add(case)
        session.commit()


def invalidate_case(
    session: Session, case_id: int, *, reason: str = "stale_evidence"
) -> CampaignValidationCase | None:
    """Mark a case unresolved when its crawl evidence is no longer valid."""
    case = session.get(CampaignValidationCase, case_id)
    if case is None:
        return None
    blockers = _json(case.blocker_codes_json, [])
    if reason not in blockers:
        blockers.append(reason)
    case.readiness_status = READINESS_PENDING
    case.blocker_codes_json = _dump(blockers, [])
    case.execution_status = EXECUTION_NOT_QUEUED
    if case.copied_lead_id is not None:
        copied = session.get(ScanLead, case.copied_lead_id)
        if copied is not None and copied.status in {"open", "investigating"}:
            copied.status = "dismissed"
            copied.reportable = False
            copied.note = "Validation case is stale and must be rebuilt."
            copied.updated_at = datetime.now(_UTC)
            session.add(copied)
        case.copied_lead_id = None
    case.updated_at = datetime.now(_UTC)
    session.add(case)
    return case


def list_validation_cases(
    session: Session, campaign_id: int, target_member_id: int | None = None
) -> list[CampaignValidationCase]:
    query = select(CampaignValidationCase).where(
        CampaignValidationCase.campaign_id == campaign_id
    )
    if target_member_id is not None:
        query = query.where(CampaignValidationCase.target_member_id == target_member_id)
    return session.exec(query.order_by(CampaignValidationCase.id)).all()


def summarize_cases(
    session: Session, campaign_id: int, target_member_id: int | None = None
) -> dict[str, Any]:
    """Return readiness/execution counts for campaign progress summaries."""
    cases = list_validation_cases(session, campaign_id, target_member_id)
    readiness: dict[str, int] = {}
    execution: dict[str, int] = {}
    for case in cases:
        readiness[case.readiness_status] = readiness.get(case.readiness_status, 0) + 1
        execution[case.execution_status] = execution.get(case.execution_status, 0) + 1
    return {
        "total": len(cases),
        "readiness": readiness,
        "execution": execution,
        "runnable": sum(
            1
            for case in cases
            if case.readiness_status == READINESS_RESOLVED
            and case.execution_status
            in {EXECUTION_QUEUED, EXECUTION_RUNNING, EXECUTION_NOT_QUEUED}
        ),
    }


summarize_validation_cases = summarize_cases


def case_to_output(session: Session, case: CampaignValidationCase) -> dict:
    """Build the structured API representation without leaking credentials."""
    path = _json(case.static_path_json, {})
    binding = _json(case.live_binding_json, {})
    if not isinstance(path, dict):
        path = {}
    if not isinstance(binding, dict):
        binding = {}
    path = _redact(path)
    binding = _redact(binding)
    surface = path.get("frontend_surface", {})
    if not isinstance(surface, dict):
        surface = {}
    hops = path.get("service_hops", [])
    if not isinstance(hops, list):
        hops = []
    safe_binding = {
        key: value for key, value in binding.items() if key != "raw_request"
    }
    copied_reference = None
    finding_reference = None
    source = session.get(ScanLead, case.origin_lead_id)
    if case.copied_lead_id is not None:
        lead = session.get(ScanLead, case.copied_lead_id)
        copied_reference = lead.public_reference if lead else None
    if case.finding_id is not None:
        finding = session.get(ScanFinding, case.finding_id)
        finding_reference = finding.public_reference if finding else None
    return {
        "id": case.id,
        "campaign_id": case.campaign_id,
        "mapping_id": case.mapping_id,
        "target_member_id": case.target_member_id,
        "origin_lead_id": case.origin_lead_id,
        "source_lead": {
            "id": source.id,
            "reference": source.public_reference,
            "source": source.source,
            "category": source.category,
            "severity": source.severity,
            "confidence": source.confidence,
            "title": source.title,
            "description": source.description,
            "location": source.location,
            "evidence": (source.evidence or "")[:8000],
        }
        if source is not None
        else {},
        "assertion_key": case.assertion_key,
        "frontend_surface": {
            "ui_route": surface.get("ui_route", {}),
            "ui_action": surface.get("ui_action", {}),
            "browser_request": surface.get("browser_request", {}),
        },
        "service_hops": hops,
        "live_binding": safe_binding,
        "validation_assertion": _assertion_for_path(path),
        "static_path": path,
        "readiness_status": case.readiness_status,
        "blocker_codes": _json(case.blocker_codes_json, []),
        "copied_lead_id": case.copied_lead_id,
        "copied_lead_reference": copied_reference,
        "finding_id": case.finding_id,
        "finding_reference": finding_reference,
        "execution_status": case.execution_status,
        "outcome_reason": case.outcome_reason,
        "baseline_evidence": _json(case.baseline_evidence_json, {}),
        "mutated_evidence": _json(case.mutated_evidence_json, {}),
        "created_at": case.created_at,
        "updated_at": case.updated_at,
    }
