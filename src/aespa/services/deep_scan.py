"""Persistent queue and worker pool for the opt-in Deep web DAST mode."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from collections import Counter
from datetime import datetime, timezone
from urllib.parse import parse_qs, urljoin, urlparse, urlunparse

from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import (
    CoverageEvidence,
    CrawledPage,
    DeepScanAttempt,
    DeepScanCheck,
    DeepScanClaim,
    DeepScanProbeOutcome,
    DeepScanTask,
    DeepScanTaskFinding,
    DeepScanVariant,
    ProbeExecution,
    ScanFinding,
    ScanObligation,
    Site,
    TestRun,
    TrafficEntry,
)
from aespa.services import events as events_svc
from aespa.services import llm as llm_svc
from aespa.services import scanner_sessions as session_svc
from aespa.services import specialist_handoffs as handoff_svc
from aespa.services.settings import (
    get_deep_scan_config,
    get_llm_config_for_role,
    get_run_scanner_policy,
)

log = logging.getLogger("aespa.deep_scan")
_UTC = timezone.utc
_claim_locks: dict[int, asyncio.Lock] = {}
_planning_commit_locks: dict[int, asyncio.Lock] = {}
_planner_semaphores: dict[int, asyncio.Semaphore] = {}
_planning_scheduled_task_ids: dict[int, set[int]] = {}
_planning_active_task_ids: dict[int, set[int]] = {}

_DEEP_CAMPAIGN_PROMPT = """You are a Deep Attack Worker. Test one bounded HTTP operation,
saved workflow, systemic recon area, or imported SAST lead. Your briefing lists the checks
inside this tester. Reuse request baselines, browser state, and sessions across those checks.
Work through applicable checks in risk order. Do not repeat the same request for each label.
Create a follow-up probe only when traffic, a response difference, or source evidence supports
it. Put the relevant OWASP category and test class on each probe. Write a finding only with
direct tool evidence. Stop before bulk data access or unsafe state changes. Call done when the
applicable checks are complete or the remaining checks have a specific blocker."""

_DEEP_BASELINE_PROMPT = """You are a Deep baseline worker. Establish normal behaviour for
one saved tester before attack variants run. Replay or send the clean request, identify the
active session, and record the response. Do not inject attack payloads and do not write a
finding in this baseline step. Call done after the clean baseline is captured or explain the
specific blocker."""

_TECHNIQUE_TO_ATTACK_CLASS = {
    "auth_vs_unauth": "auth_bypass",
    "user_a_vs_user_b": "idor",
    "privilege_escalation": "auth_bypass",
    "http_cleartext_sensitive": "crypto",
    "exposed_tokens": "crypto",
    "sqli": "sqli",
    "reflected_xss": "xss",
    "stored_xss": "xss",
    "command_injection": "sqli",
    "ssti": "xss",
    "workflow_bypass": "business_logic",
    "rate_limiting": "business_logic",
    "admin_route_exposure": "config",
    "verbose_errors": "config",
    "outdated_library_banner": "config",
    "credential_stuffing": "auth_bypass",
    "weak_auth": "auth_bypass",
    "session_fixation": "auth_bypass",
    "deserialization": "business_logic",
    "untrusted_scripts": "xss",
    "unlogged_auth_failure": "business_logic",
    "ssrf_canary": "ssrf",
}


def _fingerprint(*parts: object) -> str:
    material = "|".join(str(part or "").strip().lower() for part in parts)
    return hashlib.sha256(material.encode()).hexdigest()


def _lead_attack_class(lead) -> str:
    text = " ".join(
        (lead.title or "", lead.category or "", lead.description or "")
    ).lower()
    checks = (
        (("idor", "bola", "object level"), "idor"),
        (("sql injection", "sqli"), "sqli"),
        (("cross-site", "cross site", "xss"), "xss"),
        (("ssrf", "server-side request forgery"), "ssrf"),
        (("traversal", "local file inclusion", "lfi"), "path_traversal"),
        (("upload",), "file_upload"),
        (("jwt", "crypt", "token signature"), "crypto"),
        (("auth", "session", "password"), "auth_bypass"),
        (("cors",), "cors"),
        (("config", "header", "component", "version", "debug"), "config"),
    )
    for words, attack_class in checks:
        if any(word in text for word in words):
            return attack_class
    return "business_logic"


def _page_for_target(pages: list[CrawledPage], target_url: str) -> CrawledPage | None:
    plain = target_url.split("?", 1)[0].replace("{id}", "")
    for page in pages:
        page_plain = page.url.split("?", 1)[0]
        if page.url == target_url or page_plain.startswith(plain):
            return page
    return None


def _json_list(value: str) -> list[str]:
    try:
        parsed = json.loads(value or "[]")
    except (TypeError, json.JSONDecodeError):
        return []
    return [str(item) for item in parsed if item not in (None, "")]


def _json_array(value: str) -> list:
    try:
        parsed = json.loads(value or "[]")
    except (TypeError, json.JSONDecodeError):
        return []
    return parsed if isinstance(parsed, list) else []


def _canonical_route(url: str) -> str:
    parsed = urlparse(url)
    path = re.sub(
        r"/(?:(?:\d+)|(?:[0-9a-f]{8}-[0-9a-f-]{27,}))(?=/|$)",
        "/{id}",
        parsed.path,
        flags=re.I,
    )
    return urlunparse(
        (parsed.scheme, parsed.netloc, path or "/", "", "", parsed.fragment)
    )


def _traffic_inputs(row: TrafficEntry) -> set[str]:
    names = set(parse_qs(urlparse(row.url).query, keep_blank_values=True))
    body = row.request_body or ""
    try:
        parsed = json.loads(body)
        if isinstance(parsed, dict):
            names.update(str(key) for key in parsed)
    except (TypeError, json.JSONDecodeError):
        names.update(parse_qs(body, keep_blank_values=True))
    return names


def _operation_for_obligation(
    obligation: ScanObligation,
    pages: list[CrawledPage],
    traffic: list[TrafficEntry],
) -> tuple[str, str, CrawledPage | None]:
    page = _page_for_target(pages, obligation.route_template)
    route = _canonical_route(obligation.route_template)
    method = (obligation.http_method or "GET").upper()
    matches = [row for row in traffic if (row.method or "GET").upper() == method]
    direct = [row for row in matches if _canonical_route(row.url) == route]
    if direct:
        chosen = direct[-1]
        return chosen.url, _canonical_route(chosen.url), page
    if page is not None:
        related = [row for row in matches if row.page_id == page.id]
        if obligation.parameter:
            parameter_matches = [
                row for row in related if obligation.parameter in _traffic_inputs(row)
            ]
            if parameter_matches:
                chosen = parameter_matches[-1]
                return chosen.url, _canonical_route(chosen.url), page
        api_related = [row for row in related if "/api/" in urlparse(row.url).path]
        if len({_canonical_route(row.url) for row in api_related}) == 1:
            chosen = api_related[-1]
            return chosen.url, _canonical_route(chosen.url), page
        return page.url, _canonical_route(page.url), page
    return obligation.route_template, route, None


def _check_dict(check: DeepScanCheck) -> dict:
    return {
        "id": check.id,
        "source": check.source,
        "attack_class": check.attack_class,
        "owasp_category": check.owasp_category,
        "parameter": check.parameter,
        "parameter_location": check.parameter_location,
        "session_label": check.session_label,
        "hypothesis": check.hypothesis,
        "status": check.status,
        "finding_id": check.finding_id,
        "outcome": check.outcome,
    }


def _variant_dict(
    variant: DeepScanVariant, finding_ids: list[int] | None = None
) -> dict:
    finding_ids = finding_ids or []
    return {
        "id": variant.id,
        "kind": variant.kind,
        "strategy": variant.strategy,
        "purpose": variant.purpose,
        "assigned_purpose": variant.assigned_purpose or variant.purpose,
        "current_purpose": variant.current_purpose or variant.purpose,
        "rationale": variant.rationale,
        "difference": variant.difference,
        "identities": _json_list(variant.identity_requirements_json),
        "check_ids": [int(value) for value in _json_list(variant.check_ids_json)],
        "status": variant.status,
        "worker_id": variant.worker_id,
        "attempt_count": variant.attempt_count,
        "finding_ids": finding_ids,
        "finding_count": len(finding_ids) or variant.finding_count,
        "novelty_score": variant.novelty_score,
        "pivot_history": _json_array(variant.pivot_history_json),
        "outcome": variant.outcome,
        "error_message": variant.error_message,
        "started_at": variant.started_at.isoformat() if variant.started_at else None,
        "completed_at": variant.completed_at.isoformat()
        if variant.completed_at
        else None,
    }


def _task_dict(
    task: DeepScanTask,
    checks: list[DeepScanCheck] | None = None,
    finding_ids: list[int] | None = None,
    variants: list[DeepScanVariant] | None = None,
    finding_ids_by_variant: dict[int, list[int]] | None = None,
) -> dict:
    checks = checks or []
    finding_ids = finding_ids or ([task.finding_id] if task.finding_id else [])
    finding_count = len(finding_ids)
    if not finding_count:
        legacy_count = re.search(r"\b(\d+) new findings?\b", task.outcome or "", re.I)
        finding_count = int(legacy_count.group(1)) if legacy_count else 0
    return {
        "id": task.id,
        "source": task.source,
        "task_kind": task.task_kind,
        "route_template": task.route_template or _canonical_route(task.target_url),
        "attack_class": task.attack_class,
        "owasp_category": task.owasp_category,
        "target_url": task.target_url,
        "http_method": task.http_method,
        "parameter": task.parameter,
        "session_label": task.session_label,
        "title": task.title,
        "priority": task.priority,
        "risk_level": task.risk_level,
        "status": task.status,
        "attempt_count": task.attempt_count,
        "worker_id": task.worker_id,
        "finding_id": task.finding_id,
        "inputs": _json_list(task.inputs_json),
        "identities": _json_list(task.identities_json),
        "checks": [_check_dict(check) for check in checks],
        "check_count": len(checks),
        "variants": [
            _variant_dict(
                variant,
                (finding_ids_by_variant or {}).get(variant.id or -1, []),
            )
            for variant in (variants or [])
        ],
        "variant_count": len(variants or []),
        "finding_ids": finding_ids,
        "finding_count": finding_count,
        "outcome": task.outcome,
        "error_message": task.error_message,
        "created_at": task.created_at.isoformat(),
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }


def get_queue(run_id: int) -> dict:
    with Session(get_engine()) as session:
        rows = list(
            session.exec(
                select(DeepScanTask)
                .where(DeepScanTask.run_id == run_id)
                .order_by(DeepScanTask.priority.desc(), DeepScanTask.id)
            ).all()
        )
        checks = list(
            session.exec(
                select(DeepScanCheck)
                .where(DeepScanCheck.run_id == run_id)
                .order_by(DeepScanCheck.id)
            ).all()
        )
        links = list(
            session.exec(
                select(DeepScanTaskFinding).where(DeepScanTaskFinding.run_id == run_id)
            ).all()
        )
        variants = list(
            session.exec(
                select(DeepScanVariant)
                .where(DeepScanVariant.run_id == run_id)
                .order_by(DeepScanVariant.task_id, DeepScanVariant.variant_index)
            ).all()
        )
    checks_by_task: dict[int, list[DeepScanCheck]] = {}
    findings_by_task: dict[int, list[int]] = {}
    variants_by_task: dict[int, list[DeepScanVariant]] = {}
    findings_by_variant: dict[int, list[int]] = {}
    for check in checks:
        checks_by_task.setdefault(check.task_id, []).append(check)
    for link in links:
        findings_by_task.setdefault(link.task_id, []).append(link.finding_id)
        if link.variant_id:
            findings_by_variant.setdefault(link.variant_id, []).append(link.finding_id)
    for variant in variants:
        variants_by_task.setdefault(variant.task_id, []).append(variant)
    counts = Counter(row.status for row in rows)
    planned_task_ids = {
        variant.task_id
        for variant in variants
        if variant.kind != "baseline" or _planning_is_complete(variant)
    }
    active_planning = len(_planning_active_task_ids.get(run_id, set()))
    return {
        "run_id": run_id,
        "total": len(rows),
        "counts": dict(counts),
        "checks_total": len(checks),
        "variants_total": len(variants),
        "planning": {
            "total": len(rows),
            "complete": len(planned_task_ids),
            "active": active_planning,
            "pending": max(0, len(rows) - len(planned_task_ids) - active_planning),
        },
        "tasks": [
            _task_dict(
                row,
                checks_by_task.get(row.id or -1, []),
                findings_by_task.get(row.id or -1, []),
                variants_by_task.get(row.id or -1, []),
                findings_by_variant,
            )
            for row in rows
        ],
    }


def _campaign_brief(checks: list[dict]) -> str:
    lines = [
        "Test this operation as one tester. Work through these checks and reuse request and session context:",
    ]
    for check in checks:
        detail = f"- [{check['owasp_category']}] {check['attack_class']}"
        if check.get("parameter"):
            detail += f" input={check['parameter']}"
        if check.get("session_label"):
            detail += f" identity={check['session_label']}"
        lines.append(f"{detail}: {check['hypothesis']}")
    lines.append("Create follow-up probes only when observed evidence supports them.")
    return "\n".join(lines)[:12000]


def _persist_campaign(session: Session, run_id: int, campaign: dict) -> None:
    checks = campaign.pop("checks")
    task = DeepScanTask(
        run_id=run_id,
        fingerprint=_fingerprint(
            campaign["task_kind"],
            campaign["route_template"],
            campaign["http_method"],
            campaign.get("lead_id"),
            campaign["source"],
            campaign["title"],
        ),
        inputs_json=json.dumps(
            sorted({c["parameter"] for c in checks if c.get("parameter")})
        ),
        identities_json=json.dumps(
            sorted({c["session_label"] for c in checks if c.get("session_label")})
        ),
        hypothesis=_campaign_brief(checks),
        **campaign,
    )
    session.add(task)
    session.flush()
    for check in checks:
        session.add(
            DeepScanCheck(
                run_id=run_id,
                task_id=task.id,
                fingerprint=_fingerprint(
                    check["source"],
                    check.get("obligation_id"),
                    check.get("lead_id"),
                    check["attack_class"],
                    check.get("parameter"),
                    check.get("session_label"),
                ),
                **check,
            )
        )


def seed_deep_tasks(run_id: int) -> int:
    """Build grouped Deep campaigns from recon, coverage, and imported SAST leads."""
    from aespa.services.scan_leads import get_leads_for_run
    from aespa.services.web_workprogram import (
        seed_scan_obligations,
        seed_web_workprogram,
    )

    seed_web_workprogram(run_id)
    seed_scan_obligations(run_id, scan_mode="full", run_kind="web")
    with Session(get_engine()) as session:
        run = session.get(TestRun, run_id)
        if run is None:
            raise ValueError(f"TestRun {run_id} not found")
        site = session.get(Site, run.site_id)
        if site is None:
            raise ValueError(f"Site {run.site_id} not found")
        config = get_deep_scan_config(session)
        pages = list(
            session.exec(
                select(CrawledPage)
                .where(CrawledPage.test_run_id == run_id)
                .where(CrawledPage.in_scope != False)  # noqa: E712
            ).all()
        )
        obligations = list(
            session.exec(
                select(ScanObligation)
                .where(ScanObligation.run_kind == "web")
                .where(ScanObligation.run_id == run_id)
                .order_by(ScanObligation.id)
            ).all()
        )
        if session.exec(
            select(DeepScanTask.id).where(DeepScanTask.run_id == run_id)
        ).first():
            return 0
        traffic = list(
            session.exec(
                select(TrafficEntry)
                .where(TrafficEntry.test_run_id == run_id)
                .order_by(TrafficEntry.created_at, TrafficEntry.id)
            ).all()
        )
        groups: dict[tuple, dict] = {}

        def add_group(key: tuple, values: dict, check: dict) -> None:
            campaign = groups.get(key)
            if campaign is None:
                campaign = {**values, "checks": []}
                groups[key] = campaign
            check_key = _fingerprint(
                check["source"],
                check.get("obligation_id"),
                check.get("lead_id"),
                check["attack_class"],
                check.get("parameter"),
                check.get("session_label"),
            )
            if all(existing["_key"] != check_key for existing in campaign["checks"]):
                campaign["checks"].append({**check, "_key": check_key})
            campaign["priority"] = max(campaign["priority"], check["priority"])

        if config.include_sast_leads:
            severity_priority = {"critical": 10, "high": 9, "medium": 8, "low": 6}
            for lead in get_leads_for_run("web", run_id):
                target = urljoin(site.base_url, lead.suggested_endpoint or "/")
                page = _page_for_target(pages, target)
                attack_class = _lead_attack_class(lead)
                priority = severity_priority.get((lead.severity or "medium").lower(), 7)
                add_group(
                    ("sast", lead.id),
                    {
                        "source": "sast_lead",
                        "task_kind": "sast",
                        "route_template": _canonical_route(target),
                        "lead_id": lead.id,
                        "page_id": page.id if page else None,
                        "attack_class": attack_class,
                        "owasp_category": lead.category or "",
                        "target_url": target,
                        "http_method": "GET",
                        "title": f"Validate SAST lead {lead.reference}: {lead.title}",
                        "priority": priority,
                        "risk_level": "safe_active",
                    },
                    {
                        "source": "sast_lead",
                        "lead_id": lead.id,
                        "attack_class": attack_class,
                        "owasp_category": lead.category or "",
                        "parameter": None,
                        "parameter_location": "",
                        "session_label": None,
                        "hypothesis": (
                            f"Validate imported SAST lead {lead.reference}. Retrieve its full "
                            "lead_detail before testing. " + (lead.description or "")
                        )[:4000],
                        "priority": priority,
                    },
                )

        for obligation in obligations:
            attack_class = _TECHNIQUE_TO_ATTACK_CLASS.get(
                obligation.vulnerability_technique
            )
            if not attack_class:
                continue
            target, route_template, page = _operation_for_obligation(
                obligation, pages, traffic
            )
            identity = obligation.required_identity_comparison
            priority = 9 if obligation.owasp_category in {"A01", "A03", "A07"} else 6
            key = ("operation", obligation.http_method.upper(), route_template)
            add_group(
                key,
                {
                    "source": "coverage",
                    "task_kind": "operation",
                    "route_template": route_template,
                    "obligation_id": obligation.id,
                    "page_id": page.id if page else None,
                    "attack_class": "business_logic",
                    "owasp_category": obligation.owasp_category,
                    "target_url": target,
                    "http_method": obligation.http_method.upper(),
                    "title": f"Test {obligation.http_method.upper()} {route_template}",
                    "priority": priority,
                    "risk_level": "safe_active",
                },
                {
                    "source": "coverage",
                    "obligation_id": obligation.id,
                    "attack_class": attack_class,
                    "owasp_category": obligation.owasp_category,
                    "parameter": obligation.parameter,
                    "parameter_location": "",
                    "session_label": identity,
                    "hypothesis": (
                        f"Test {obligation.vulnerability_technique}. Use obligation_id="
                        f"{obligation.id} and OWASP category {obligation.owasp_category} on probes."
                    ),
                    "priority": priority,
                },
            )

        if config.include_recon_checks:
            for attack_class, category, title, hypothesis, priority in (
                (
                    "config",
                    "A05",
                    "Deep route and configuration recon",
                    "Inspect the route inventory, JavaScript assets, common operational paths, error responses, and security headers. Record only verified exposures.",
                    7,
                ),
                (
                    "cors",
                    "A05",
                    "Cross-origin policy review",
                    "Test CORS behaviour with untrusted Origin values on representative public and authenticated routes.",
                    7,
                ),
                (
                    "config",
                    "A06",
                    "Browser component version review",
                    "Inspect loaded JavaScript and page assets for identifiable third-party component versions and verify whether detected versions are outdated.",
                    6,
                ),
            ):
                add_group(
                    ("systemic", category, attack_class),
                    {
                        "source": "recon",
                        "task_kind": "systemic",
                        "route_template": _canonical_route(site.base_url),
                        "attack_class": attack_class,
                        "owasp_category": category,
                        "target_url": site.base_url,
                        "http_method": "GET",
                        "title": title,
                        "priority": priority,
                        "risk_level": "safe_active",
                    },
                    {
                        "source": "recon",
                        "attack_class": attack_class,
                        "owasp_category": category,
                        "parameter": None,
                        "parameter_location": "",
                        "session_label": None,
                        "hypothesis": hypothesis,
                        "priority": priority,
                    },
                )
            for page in pages:
                if page.state_kind == "interactive" or page.has_business_logic:
                    add_group(
                        ("workflow", page.id),
                        {
                            "source": "workflow_recon",
                            "task_kind": "workflow",
                            "route_template": _canonical_route(page.url),
                            "page_id": page.id,
                            "attack_class": "business_logic",
                            "owasp_category": "A04",
                            "target_url": page.url,
                            "http_method": "POST",
                            "title": f"Replay and test workflow: {page.state_label or page.url}",
                            "priority": 8,
                            "risk_level": "safe_active",
                        },
                        {
                            "source": "workflow_recon",
                            "attack_class": "business_logic",
                            "owasp_category": "A04",
                            "parameter": None,
                            "parameter_location": "",
                            "session_label": None,
                            "hypothesis": (
                                "Replay the saved interactive state, identify the workflow's "
                                "captured request, and test safe ordering, replay, and authorization variants."
                            ),
                            "priority": 8,
                        },
                    )

        campaigns = list(groups.values())
        for campaign in campaigns:
            for check in campaign["checks"]:
                check.pop("_key", None)

        def ranked(kind: str) -> list[dict]:
            return sorted(
                (c for c in campaigns if c["task_kind"] == kind),
                key=lambda c: (-c["priority"], c["title"]),
            )

        sast = ranked("sast")
        systemic = ranked("systemic")
        workflows = ranked("workflow")
        operations = sorted(
            (c for c in campaigns if c["task_kind"] == "operation"),
            key=lambda c: (-c["priority"], c["title"]),
        )
        # SAST evidence and the small systemic recon set are never hidden behind a
        # large endpoint inventory. Keep at most one third of the remaining slots
        # for workflow campaigns while operation campaigns are waiting.
        campaign_limit = min(config.max_tasks, config.max_total_variants)
        selected = sast[:campaign_limit]
        remaining = campaign_limit - len(selected)
        systemic_slots = (
            min(len(systemic), max(1, remaining // 10))
            if remaining and (remaining > 1 or not operations)
            else 0
        )
        selected.extend(systemic[:systemic_slots])
        remaining = campaign_limit - len(selected)
        workflow_slots = (
            remaining if not operations else min(len(workflows), remaining // 3)
        )
        selected.extend(workflows[:workflow_slots])
        remaining = campaign_limit - len(selected)
        selected.extend(operations[:remaining])
        remaining = campaign_limit - len(selected)
        leftovers = systemic[systemic_slots:] + workflows[workflow_slots:]
        selected.extend(leftovers[:remaining])
        for campaign in selected:
            _persist_campaign(session, run_id, campaign)
        session.commit()
    return len(selected)


def _variant_fingerprint(task_id: int, strategy: str, purpose: str) -> str:
    return _fingerprint(task_id, strategy, re.sub(r"\s+", " ", purpose).strip())


def _set_planning_complete(session: Session, baseline: DeepScanVariant) -> None:
    try:
        checkpoint = json.loads(baseline.checkpoint_json or "{}")
    except (TypeError, json.JSONDecodeError):
        checkpoint = {}
    checkpoint["planning_complete"] = True
    baseline.checkpoint_json = json.dumps(checkpoint)
    baseline.updated_at = datetime.now(_UTC)
    session.add(baseline)


def _planning_is_complete(baseline: DeepScanVariant) -> bool:
    try:
        checkpoint = json.loads(baseline.checkpoint_json or "{}")
    except (TypeError, json.JSONDecodeError):
        return False
    return isinstance(checkpoint, dict) and bool(checkpoint.get("planning_complete"))


def _seed_baseline_variants(run_id: int, *, reuse_captured: bool) -> int:
    """Create one deterministic baseline per campaign without duplicating resume state."""
    created = 0
    with Session(get_engine()) as session:
        tasks = list(
            session.exec(
                select(DeepScanTask)
                .where(DeepScanTask.run_id == run_id)
                .order_by(DeepScanTask.id)
            ).all()
        )
        traffic = list(
            session.exec(
                select(TrafficEntry)
                .where(TrafficEntry.test_run_id == run_id)
                .order_by(TrafficEntry.created_at, TrafficEntry.id)
            ).all()
        )
        for task in tasks:
            if session.exec(
                select(DeepScanVariant.id).where(DeepScanVariant.task_id == task.id)
            ).first():
                continue
            matches = [
                row
                for row in traffic
                if (row.method or "GET").upper() == task.http_method.upper()
                and _canonical_route(row.url) == task.route_template
            ]
            captured = matches[-1] if reuse_captured and matches else None
            purpose = (
                "Reuse the captured request as the tester baseline."
                if captured
                else "Establish a clean request and response baseline before attack variants run."
            )
            now = datetime.now(_UTC)
            variant = DeepScanVariant(
                run_id=run_id,
                task_id=task.id,
                fingerprint=_variant_fingerprint(task.id, "baseline", purpose),
                variant_index=1,
                kind="baseline",
                strategy="baseline",
                purpose=purpose,
                assigned_purpose=purpose,
                current_purpose=purpose,
                rationale="All later workers use this baseline for response and session comparisons.",
                difference="This variant records normal behaviour and does not start with an exploit hypothesis.",
                check_ids_json="[]",
                identity_requirements_json=task.identities_json,
                status="complete" if captured else "queued",
                priority=task.priority + 1,
                outcome="Reused captured traffic baseline" if captured else "",
                novelty_score=1 if captured else 0,
                completed_at=now if captured else None,
            )
            session.add(variant)
            session.flush()
            if captured:
                session.add(
                    DeepScanProbeOutcome(
                        run_id=run_id,
                        task_id=task.id,
                        variant_id=variant.id,
                        traffic_id=captured.id,
                        fingerprint=_fingerprint(
                            task.id,
                            "baseline",
                            captured.method,
                            captured.url,
                            captured.status,
                        ),
                        technique="baseline",
                        request_summary=f"{captured.method} {captured.url}"[:2000],
                        response_status=captured.status,
                        signal_type="baseline",
                        signal_strength=1,
                        evidence_json=json.dumps({"traffic_id": captured.id}),
                        outcome="baseline_reused",
                    )
                )
            created += 1
        session.commit()
    return created


def _fallback_variant_specs(
    task: DeepScanTask, checks: list[DeepScanCheck], limit: int
) -> list[dict]:
    if task.task_kind == "sast":
        return [
            {
                "strategy": "sast_validation",
                "purpose": "Reproduce the imported source-code lead against the live application.",
                "rationale": "Confirm whether the source path is reachable and produces the claimed security effect.",
                "difference": "Uses the SAST evidence as its starting point and requires a live reproduction.",
                "check_ids": [check.id for check in checks if check.id],
                "identities": _json_list(task.identities_json),
            }
        ]
    grouped: dict[tuple[str, str], list[DeepScanCheck]] = {}
    for check in checks:
        grouped.setdefault((check.attack_class, check.session_label or ""), []).append(
            check
        )
    specs = []
    for (attack_class, identity), members in grouped.items():
        inputs = sorted({member.parameter for member in members if member.parameter})
        identity_text = f" using {identity.replace('_', ' ')}" if identity else ""
        input_text = f" across {', '.join(inputs)}" if inputs else ""
        specs.append(
            {
                "strategy": attack_class,
                "purpose": f"Test {attack_class.replace('_', ' ')}{input_text}{identity_text}.",
                "rationale": "Covers related checks in one worker while reusing the same request and session state.",
                "difference": f"Focuses on the {attack_class.replace('_', ' ')} perspective.",
                "check_ids": [member.id for member in members if member.id],
                "identities": [identity] if identity else [],
            }
        )
    return specs[:limit]


def _planner_prompt(
    task: DeepScanTask,
    checks: list[DeepScanCheck],
    limit: int,
    ledger: list[DeepScanProbeOutcome],
) -> str:
    payload = {
        "tester": {
            "kind": task.task_kind,
            "method": task.http_method,
            "route": task.route_template,
            "title": task.title,
            "brief": task.hypothesis,
        },
        "checks": [_check_dict(check) for check in checks],
        "shared_probe_ledger": [
            {
                "technique": row.technique,
                "request": row.request_summary,
                "status": row.response_status,
                "signal": row.signal_type,
                "strength": row.signal_strength,
            }
            for row in ledger[-20:]
        ],
    }
    return f"""Plan up to {limit} distinct attack-worker variants for this authorised Deep web scan tester.
Each variant must cover a meaningful testing perspective, not one parameter and vulnerability label.
Reuse the baseline and shared evidence. Do not repeat an equivalent purpose. Include an identity comparison only when supported by the checks. For a SAST tester, include one explicit live-validation variant.

Return JSON only as an array. Each item must have:
strategy, purpose, rationale, difference, check_ids, identities.

Tester data:
{json.dumps(payload, ensure_ascii=False, default=str)}"""


async def _ensure_attack_variants(task_id: int, llm_cfg, config) -> int:
    """Plan and save bounded variants after the campaign baseline is complete."""
    with Session(get_engine(), expire_on_commit=False) as session:
        task = session.get(DeepScanTask, task_id)
        if task is None:
            return 0
        existing = list(
            session.exec(
                select(DeepScanVariant).where(DeepScanVariant.task_id == task_id)
            ).all()
        )
        if any(variant.kind != "baseline" for variant in existing):
            return 0
        baseline = next(
            (variant for variant in existing if variant.kind == "baseline"), None
        )
        if baseline is None or baseline.status != "complete":
            return 0
        total = len(
            session.exec(
                select(DeepScanVariant.id).where(DeepScanVariant.run_id == task.run_id)
            ).all()
        )
        available = min(
            1 if task.task_kind == "sast" else config.initial_variants_per_campaign,
            config.max_variants_per_campaign - len(existing),
            config.max_total_variants - total,
        )
        if available <= 0:
            _set_planning_complete(session, baseline)
            session.commit()
            return 0
        checks = list(
            session.exec(
                select(DeepScanCheck)
                .where(DeepScanCheck.task_id == task_id)
                .order_by(DeepScanCheck.priority.desc(), DeepScanCheck.id)
            ).all()
        )
        ledger = list(
            session.exec(
                select(DeepScanProbeOutcome)
                .where(DeepScanProbeOutcome.task_id == task_id)
                .order_by(DeepScanProbeOutcome.id)
            ).all()
        )
    specs: list[dict] = []
    try:
        configured_output = max(1, int(getattr(llm_cfg, "max_tokens", 0) or 4096))
        planner_output = min(
            configured_output,
            4096,
            max(1536, available * 512),
        )
        planner_llm_cfg = (
            llm_cfg.model_copy(update={"max_tokens": planner_output})
            if hasattr(llm_cfg, "model_copy")
            else llm_cfg
        )
        raw = await llm_svc.plain_completion(
            planner_llm_cfg,
            _planner_prompt(task, checks, available, ledger),
            system_prompt="You plan concise, evidence-led web security test variants.",
        )
        decoded = llm_svc.extract_json_response(raw, expect=list)
        if isinstance(decoded, list):
            specs = [item for item in decoded if isinstance(item, dict)]
    except llm_svc.LLMQuotaPauseError:
        raise
    except Exception as exc:
        log.warning("Deep variant planning fell back to deterministic checks: %s", exc)
    fallback = _fallback_variant_specs(task, checks, available)
    candidates = specs + fallback
    saved = 0
    seen: set[str] = set()
    valid_check_ids = {check.id for check in checks if check.id}
    commit_lock = _planning_commit_locks.setdefault(task.run_id, asyncio.Lock())
    async with commit_lock:
        with Session(get_engine()) as session:
            current_for_task = len(
                session.exec(
                    select(DeepScanVariant.id).where(DeepScanVariant.task_id == task_id)
                ).all()
            )
            current_for_run = len(
                session.exec(
                    select(DeepScanVariant.id).where(
                        DeepScanVariant.run_id == task.run_id
                    )
                ).all()
            )
            save_limit = min(
                available,
                config.max_variants_per_campaign - current_for_task,
                config.max_total_variants - current_for_run,
            )
            for item in candidates:
                if saved >= save_limit:
                    break
                strategy = str(item.get("strategy") or "targeted")[:80].strip()
                purpose = str(item.get("purpose") or "")[:1000].strip()
                difference = str(item.get("difference") or "")[:1000].strip()
                if not purpose or not difference:
                    continue
                fingerprint = _variant_fingerprint(task_id, strategy, purpose)
                if session.exec(
                    select(DeepScanVariant.id)
                    .where(DeepScanVariant.task_id == task_id)
                    .where(DeepScanVariant.fingerprint == fingerprint)
                ).first():
                    continue
                check_ids = [
                    int(value)
                    for value in item.get("check_ids", [])
                    if str(value).isdigit() and int(value) in valid_check_ids
                ]
                identities = [
                    str(value)[:120] for value in item.get("identities", []) if value
                ]
                semantic_key = _fingerprint(
                    strategy, *sorted(check_ids), *sorted(identities)
                )
                if semantic_key in seen:
                    continue
                kind = "sast_validation" if task.task_kind == "sast" else "planned"
                session.add(
                    DeepScanVariant(
                        run_id=task.run_id,
                        task_id=task_id,
                        fingerprint=fingerprint,
                        variant_index=current_for_task + saved + 1,
                        kind=kind,
                        strategy=strategy,
                        purpose=purpose,
                        assigned_purpose=purpose,
                        current_purpose=purpose,
                        rationale=str(item.get("rationale") or "")[:2000],
                        difference=difference,
                        identity_requirements_json=json.dumps(identities),
                        check_ids_json=json.dumps(check_ids),
                        priority=task.priority,
                    )
                )
                seen.add(semantic_key)
                saved += 1
            stored_baseline = session.get(DeepScanVariant, baseline.id)
            if stored_baseline:
                _set_planning_complete(session, stored_baseline)
            if saved:
                stored_task = session.get(DeepScanTask, task_id)
                if stored_task:
                    stored_task.status = "queued"
                    stored_task.completed_at = None
                    stored_task.updated_at = datetime.now(_UTC)
                    session.add(stored_task)
                for check in session.exec(
                    select(DeepScanCheck).where(DeepScanCheck.task_id == task_id)
                ).all():
                    if not check.finding_id:
                        check.status = "queued"
                        check.outcome = ""
                        check.updated_at = datetime.now(_UTC)
                        session.add(check)
            session.commit()
    return saved


def _emit_test_lead_progress(
    run_id: int, current_task: str, outcome: str | None = None
) -> None:
    events_svc.emit(
        run_id,
        {
            "type": "agent_status",
            "agent_id": "scanner",
            "role": "Test Lead",
            "status": "active",
            "current_task": current_task,
            "outcome": outcome,
            "_persist": True,
        },
    )


async def _plan_tester_variants(
    run_id: int,
    task_id: int,
    tester_number: int,
    tester_title: str,
    llm_cfg,
    config,
) -> int:
    """Plan one tester once, under the run's bounded planner pool."""
    scheduled = _planning_scheduled_task_ids.setdefault(run_id, set())
    if task_id in scheduled:
        return 0
    scheduled.add(task_id)
    semaphore = _planner_semaphores.setdefault(
        run_id, asyncio.Semaphore(config.max_concurrent_planners)
    )
    try:
        async with semaphore:
            active = _planning_active_task_ids.setdefault(run_id, set())
            active.add(task_id)
            _emit_test_lead_progress(
                run_id,
                f"Planning Tester {tester_number}: {tester_title}",
                f"Up to {config.max_concurrent_planners} planner calls can run concurrently.",
            )
            events_svc.emit(
                run_id,
                {
                    "type": "scanner_phase",
                    "phase": "deep_planning",
                    "status": "running",
                    "message": f"Planning variants for Tester {tester_number}: {tester_title}",
                    "data": {"task_id": task_id, "tester_number": tester_number},
                },
            )
            events_svc.emit(
                run_id,
                {
                    "type": "deep_queue_update",
                    "status": "planning",
                    **get_queue(run_id),
                },
            )
            try:
                saved = await _ensure_attack_variants(task_id, llm_cfg, config)
            finally:
                active.discard(task_id)

            queue = get_queue(run_id)
            progress = queue["planning"]
            _emit_test_lead_progress(
                run_id,
                f"Planned {progress['complete']} of {progress['total']} testers",
                f"Tester {tester_number} added {saved} attack variant{'s' if saved != 1 else ''}.",
            )
            events_svc.emit(
                run_id,
                {
                    "type": "scanner_phase",
                    "phase": "deep_planning",
                    "status": "complete",
                    "message": (
                        f"Tester {tester_number} plan ready with {saved} attack "
                        f"variant{'s' if saved != 1 else ''}."
                    ),
                    "data": {
                        "task_id": task_id,
                        "tester_number": tester_number,
                        "variants_created": saved,
                        "planning": progress,
                    },
                },
            )
            events_svc.emit(
                run_id,
                {"type": "deep_queue_update", "status": "planned", **queue},
            )
            return saved
    finally:
        scheduled.discard(task_id)


async def _plan_ready_testers(
    run_id: int,
    task_ids: list[int],
    tester_details: dict[int, tuple[int, str]],
    llm_cfg,
    config,
) -> None:
    """Plan independent testers concurrently so workers can consume results early."""
    planning_tasks = [
        asyncio.create_task(
            _plan_tester_variants(
                run_id,
                task_id,
                tester_details[task_id][0],
                tester_details[task_id][1],
                llm_cfg,
                config,
            ),
            name=f"deep-planner-{run_id}-{task_id}",
        )
        for task_id in task_ids
    ]
    if not planning_tasks:
        return
    try:
        await asyncio.gather(*planning_tasks)
    except BaseException:
        for planning_task in planning_tasks:
            if not planning_task.done():
                planning_task.cancel()
        await asyncio.gather(*planning_tasks, return_exceptions=True)
        raise


async def _claim_variant(
    run_id: int, worker_id: str
) -> tuple[DeepScanTask, DeepScanVariant, int] | None:
    lock = _claim_locks.setdefault(run_id, asyncio.Lock())
    async with lock:
        with Session(get_engine(), expire_on_commit=False) as session:
            variant = session.exec(
                select(DeepScanVariant)
                .where(DeepScanVariant.run_id == run_id)
                .where(DeepScanVariant.status == "queued")
                .where(DeepScanVariant.attempt_count < DeepScanVariant.max_attempts)
                .order_by(
                    DeepScanVariant.priority.desc(),
                    DeepScanVariant.variant_index,
                    DeepScanVariant.id,
                )
            ).first()
            if variant is None:
                return None
            task = session.get(DeepScanTask, variant.task_id)
            if task is None:
                return None
            now = datetime.now(_UTC)
            variant.status = "running"
            variant.worker_id = worker_id
            variant.attempt_count += 1
            variant.started_at = variant.started_at or now
            variant.updated_at = now
            task.status = "running"
            task.worker_id = worker_id
            task.attempt_count = max(1, task.attempt_count)
            task.started_at = task.started_at or now
            task.updated_at = now
            prior = session.exec(
                select(DeepScanAttempt.attempt_number).where(
                    DeepScanAttempt.variant_id == variant.id
                )
            ).all()
            attempt = DeepScanAttempt(
                run_id=run_id,
                task_id=task.id,
                variant_id=variant.id,
                worker_id=worker_id,
                attempt_number=max(prior, default=0) + 1,
            )
            session.add(task)
            session.add(variant)
            session.add(attempt)
            session.commit()
            session.refresh(attempt)
            return task, variant, attempt.id


def _queue_has_active_variants(run_id: int) -> bool:
    with Session(get_engine()) as session:
        return (
            session.exec(
                select(DeepScanVariant.id)
                .where(DeepScanVariant.run_id == run_id)
                .where(DeepScanVariant.status == "running")
            ).first()
            is not None
        )


def _queue_needs_planning(run_id: int) -> bool:
    with Session(get_engine()) as session:
        baselines = list(
            session.exec(
                select(DeepScanVariant)
                .where(DeepScanVariant.run_id == run_id)
                .where(DeepScanVariant.kind == "baseline")
                .where(DeepScanVariant.status == "complete")
            ).all()
        )
        return any(
            not _planning_is_complete(baseline)
            and len(
                session.exec(
                    select(DeepScanVariant.id).where(
                        DeepScanVariant.task_id == baseline.task_id
                    )
                ).all()
            )
            == 1
            for baseline in baselines
        )


def _shared_ledger_brief(task_id: int) -> str:
    with Session(get_engine()) as session:
        probes = list(
            session.exec(
                select(DeepScanProbeOutcome)
                .where(DeepScanProbeOutcome.task_id == task_id)
                .order_by(DeepScanProbeOutcome.id.desc())
                .limit(12)
            ).all()
        )
        claims = list(
            session.exec(
                select(DeepScanClaim)
                .where(DeepScanClaim.task_id == task_id)
                .order_by(DeepScanClaim.id.desc())
                .limit(8)
            ).all()
        )
    lines = ["Shared tester ledger. Reuse this evidence and do not repeat it:"]
    lines.extend(
        f"- Probe: {row.request_summary} -> {row.response_status or 'unknown'}; "
        f"{row.signal_type} strength {row.signal_strength}"
        for row in reversed(probes)
    )
    lines.extend(f"- Claim: {row.status} - {row.title}" for row in reversed(claims))
    return "\n".join(lines) if len(lines) > 1 else "Shared tester ledger is empty."


def _refresh_campaign_state(session: Session, task: DeepScanTask) -> None:
    variants = list(
        session.exec(
            select(DeepScanVariant).where(DeepScanVariant.task_id == task.id)
        ).all()
    )
    if any(variant.status == "running" for variant in variants):
        task.status = "running"
        return
    if any(variant.status == "queued" for variant in variants):
        task.status = "queued"
        task.worker_id = None
        return
    findings = list(
        session.exec(
            select(DeepScanTaskFinding).where(DeepScanTaskFinding.task_id == task.id)
        ).all()
    )
    failed = variants and all(variant.status == "failed" for variant in variants)
    task.status = "failed" if failed else ("finding" if findings else "inconclusive")
    task.finding_id = findings[0].finding_id if findings else None
    task.outcome = (
        "All variants failed"
        if failed
        else f"{len(findings)} new finding{'s' if len(findings) != 1 else ''}"
        if findings
        else "No confirmed finding"
    )
    task.worker_id = None
    task.completed_at = datetime.now(_UTC)
    for check in session.exec(
        select(DeepScanCheck).where(DeepScanCheck.task_id == task.id)
    ).all():
        check.status = (
            "finding" if check.finding_id else ("failed" if failed else "complete")
        )
        check.outcome = task.outcome
        check.updated_at = datetime.now(_UTC)
        session.add(check)
        if check.obligation_id:
            obligation = session.get(ScanObligation, check.obligation_id)
            if obligation:
                obligation.status = (
                    "finding"
                    if check.finding_id
                    else ("blocked" if failed else "inconclusive")
                )
                obligation.updated_at = datetime.now(_UTC)
                session.add(obligation)


def _finish_variant(
    variant_id: int,
    attempt_id: int,
    *,
    status: str,
    outcome: str,
    error: str = "",
    attempt_status: str | None = None,
    consume_attempt: bool = True,
) -> tuple[int, int]:
    """Persist a variant checkpoint and return its strongest signal and finding count."""
    with Session(get_engine()) as session:
        variant = session.get(DeepScanVariant, variant_id)
        attempt = session.get(DeepScanAttempt, attempt_id)
        if variant is None or attempt is None:
            return 0, 0
        task = session.get(DeepScanTask, variant.task_id)
        if task is None:
            return 0, 0
        now = datetime.now(_UTC)
        traffic_agent_id = variant.worker_id
        traffic_rows = list(
            session.exec(
                select(TrafficEntry)
                .where(TrafficEntry.test_run_id == variant.run_id)
                .where(TrafficEntry.agent_id == traffic_agent_id)
                .where(TrafficEntry.created_at >= attempt.started_at)
            ).all()
        )
        existing_signatures = {
            row.fingerprint
            for row in session.exec(
                select(DeepScanProbeOutcome).where(
                    DeepScanProbeOutcome.task_id == task.id
                )
            ).all()
        }
        strongest = 0
        new_signatures = 0
        for traffic in traffic_rows:
            signal_strength = 2 if traffic.status and traffic.status >= 400 else 1
            signal_type = "error_or_denial" if signal_strength == 2 else "response"
            signature = _fingerprint(
                task.id,
                traffic.method,
                _canonical_route(traffic.url),
                traffic.status,
                (traffic.response_body or "")[:256],
            )
            if signature in existing_signatures:
                continue
            strongest = max(strongest, signal_strength)
            new_signatures += 1
            existing_signatures.add(signature)
            session.add(
                DeepScanProbeOutcome(
                    run_id=variant.run_id,
                    task_id=task.id,
                    variant_id=variant.id,
                    traffic_id=traffic.id,
                    fingerprint=signature,
                    technique=variant.strategy,
                    identity_label=",".join(
                        _json_list(variant.identity_requirements_json)
                    ),
                    request_summary=f"{traffic.method} {traffic.url}"[:2000],
                    response_status=traffic.status,
                    signal_type=signal_type,
                    signal_strength=signal_strength,
                    evidence_json=json.dumps({"traffic_id": traffic.id}),
                    outcome="observed",
                )
            )
        finding_links = list(
            session.exec(
                select(DeepScanTaskFinding)
                .where(DeepScanTaskFinding.task_id == task.id)
                .where(DeepScanTaskFinding.variant_id == variant.id)
            ).all()
        )
        if finding_links:
            strongest = 3
        assigned_check_ids = {
            int(value)
            for value in _json_list(variant.check_ids_json)
            if value.isdigit()
        }
        assigned_checks = list(
            session.exec(
                select(DeepScanCheck).where(DeepScanCheck.task_id == task.id)
            ).all()
        )
        if assigned_check_ids:
            assigned_checks = [
                check for check in assigned_checks if check.id in assigned_check_ids
            ]
        if variant.kind != "baseline":
            for check in assigned_checks:
                if not check.obligation_id:
                    continue
                matching_traffic = [
                    row
                    for row in traffic_rows
                    if not row.owasp_category
                    or row.owasp_category == check.owasp_category
                ]
                for traffic in matching_traffic[:1]:
                    execution = session.exec(
                        select(ProbeExecution)
                        .where(ProbeExecution.run_kind == "web")
                        .where(ProbeExecution.run_id == task.run_id)
                        .where(ProbeExecution.obligation_id == check.obligation_id)
                        .where(ProbeExecution.traffic_id == traffic.id)
                    ).first()
                    if execution is None:
                        execution = ProbeExecution(
                            run_kind="web",
                            run_id=task.run_id,
                            obligation_id=check.obligation_id,
                            traffic_id=traffic.id,
                            session_identity=check.session_label,
                            status_code=traffic.status,
                            response_time_ms=traffic.duration_ms,
                        )
                        session.add(execution)
                        session.flush()
                        session.add(
                            CoverageEvidence(
                                execution_id=execution.id,
                                observed_behavior=outcome[:2000],
                                evaluation_oracle="deep_variant",
                                outcome="finding"
                                if check.finding_id
                                else "inconclusive",
                            )
                        )
        variant.status = status
        variant.outcome = outcome[:4000]
        variant.error_message = error[:4000]
        variant.finding_count = len(finding_links)
        variant.novelty_score = new_signatures
        variant.checkpoint_json = json.dumps(
            {
                "purpose": variant.current_purpose or variant.purpose,
                "traffic_ids": [row.id for row in traffic_rows if row.id],
                "completed_at": now.isoformat(),
            }
        )
        if not consume_attempt:
            variant.attempt_count = max(0, variant.attempt_count - 1)
        variant.completed_at = None if status == "queued" else now
        variant.updated_at = now
        if status == "queued":
            variant.worker_id = None
        attempt.status = attempt_status or status
        attempt.traffic_ids_json = json.dumps(
            [row.id for row in traffic_rows if row.id]
        )
        attempt.outcome = outcome[:4000]
        attempt.error_message = error[:4000]
        attempt.completed_at = now
        session.add(variant)
        session.add(attempt)
        _refresh_campaign_state(session, task)
        if status == "queued" and not any(
            row.status in {"complete", "finding"}
            for row in session.exec(
                select(DeepScanVariant).where(DeepScanVariant.task_id == task.id)
            ).all()
        ):
            task.attempt_count = 0
        task.updated_at = now
        session.add(task)
        session.commit()
        return strongest, len(finding_links)


def _record_variant_pivot(variant_id: int, purpose: str) -> None:
    with Session(get_engine()) as session:
        variant = session.get(DeepScanVariant, variant_id)
        if variant is None:
            return
        purpose = purpose.strip()[:1000]
        if not purpose or purpose == variant.current_purpose:
            return
        try:
            history = json.loads(variant.pivot_history_json or "[]")
        except (TypeError, json.JSONDecodeError):
            history = []
        history.append(
            {
                "from": variant.current_purpose or variant.purpose,
                "to": purpose,
                "at": datetime.now(_UTC).isoformat(),
            }
        )
        variant.current_purpose = purpose
        variant.pivot_history_json = json.dumps(history[-20:])
        variant.updated_at = datetime.now(_UTC)
        session.add(variant)
        session.commit()


def _maybe_add_follow_up(
    task_id: int, variant_id: int, config, signal_strength: int
) -> bool:
    if (
        not config.adaptive_follow_up
        or signal_strength < config.minimum_signal_strength
    ):
        return False
    with Session(get_engine()) as session:
        task = session.get(DeepScanTask, task_id)
        source = session.get(DeepScanVariant, variant_id)
        if task is None or source is None:
            return False
        variants = list(
            session.exec(
                select(DeepScanVariant).where(DeepScanVariant.task_id == task_id)
            ).all()
        )
        total = len(
            session.exec(
                select(DeepScanVariant.id).where(DeepScanVariant.run_id == task.run_id)
            ).all()
        )
        if (
            len(variants) >= config.max_variants_per_campaign
            or total >= config.max_total_variants
        ):
            return False
        purpose = f"Confirm the new {source.strategy.replace('_', ' ')} response signal with a controlled comparison."
        fingerprint = _variant_fingerprint(task_id, "follow_up", purpose)
        if session.exec(
            select(DeepScanVariant.id)
            .where(DeepScanVariant.task_id == task_id)
            .where(DeepScanVariant.fingerprint == fingerprint)
        ).first():
            return False
        session.add(
            DeepScanVariant(
                run_id=task.run_id,
                task_id=task_id,
                fingerprint=fingerprint,
                variant_index=max(row.variant_index for row in variants) + 1,
                kind="follow_up",
                strategy=source.strategy,
                purpose=purpose,
                assigned_purpose=purpose,
                current_purpose=purpose,
                rationale=f"Variant {source.id} produced signal strength {signal_strength}.",
                difference="Confirms a prior signal and stops if the comparison does not reproduce it.",
                identity_requirements_json=source.identity_requirements_json,
                check_ids_json=source.check_ids_json,
                priority=task.priority + 1,
            )
        )
        task.status = "queued"
        task.completed_at = None
        task.updated_at = datetime.now(_UTC)
        session.add(task)
        session.commit()
        return True


async def _claim_task(run_id: int, worker_id: str) -> tuple[DeepScanTask, int] | None:
    lock = _claim_locks.setdefault(run_id, asyncio.Lock())
    async with lock:
        with Session(get_engine(), expire_on_commit=False) as session:
            task = session.exec(
                select(DeepScanTask)
                .where(DeepScanTask.run_id == run_id)
                .where(DeepScanTask.status == "queued")
                .where(DeepScanTask.attempt_count < DeepScanTask.max_attempts)
                .order_by(DeepScanTask.priority.desc(), DeepScanTask.id)
            ).first()
            if task is None:
                return None
            now = datetime.now(_UTC)
            task.status = "running"
            task.worker_id = worker_id
            task.attempt_count += 1
            task.started_at = task.started_at or now
            task.updated_at = now
            prior_attempt_numbers = session.exec(
                select(DeepScanAttempt.attempt_number).where(
                    DeepScanAttempt.task_id == task.id
                )
            ).all()
            attempt = DeepScanAttempt(
                run_id=run_id,
                task_id=task.id,
                worker_id=worker_id,
                attempt_number=max(prior_attempt_numbers, default=0) + 1,
            )
            session.add(task)
            session.add(attempt)
            for check in session.exec(
                select(DeepScanCheck).where(DeepScanCheck.task_id == task.id)
            ).all():
                check.status = "running"
                check.updated_at = now
                session.add(check)
            session.commit()
            session.refresh(attempt)
            return task, attempt.id


def _finish_task(
    task_id: int,
    attempt_id: int,
    *,
    status: str,
    outcome: str,
    finding_id: int | None = None,
    error: str = "",
    attempt_status: str | None = None,
    consume_attempt: bool = True,
) -> None:
    with Session(get_engine()) as session:
        task = session.get(DeepScanTask, task_id)
        attempt = session.get(DeepScanAttempt, attempt_id)
        if task is None or attempt is None:
            return
        now = datetime.now(_UTC)
        task.status = status
        task.finding_id = finding_id
        task.outcome = outcome[:4000]
        task.error_message = error[:4000]
        if not consume_attempt:
            task.attempt_count = max(0, task.attempt_count - 1)
        task.completed_at = None if status == "queued" else now
        traffic_agent_id = task.worker_id
        if status == "queued":
            task.worker_id = None
        task.updated_at = now
        traffic_rows = list(
            session.exec(
                select(TrafficEntry)
                .where(TrafficEntry.test_run_id == task.run_id)
                .where(TrafficEntry.agent_id == traffic_agent_id)
                .where(TrafficEntry.created_at >= attempt.started_at)
            ).all()
        )
        traffic_ids = [row.id for row in traffic_rows if row.id is not None]
        attempt.status = attempt_status or status
        attempt.outcome = outcome[:4000]
        attempt.error_message = error[:4000]
        attempt.traffic_ids_json = json.dumps(traffic_ids)
        attempt.completed_at = now
        checks = list(
            session.exec(
                select(DeepScanCheck).where(DeepScanCheck.task_id == task.id)
            ).all()
        )
        finding_links = list(
            session.exec(
                select(DeepScanTaskFinding).where(
                    DeepScanTaskFinding.task_id == task.id
                )
            ).all()
        )
        linked_finding_ids = {link.finding_id for link in finding_links}
        if finding_id and finding_id not in linked_finding_ids:
            session.add(
                DeepScanTaskFinding(
                    run_id=task.run_id, task_id=task.id, finding_id=finding_id
                )
            )
            linked_finding_ids.add(finding_id)
        for check in checks:
            if status == "queued":
                check.status = "queued"
            elif check.finding_id:
                check.status = "finding"
            elif status == "failed":
                check.status = "failed"
            else:
                check.status = "complete"
            check.outcome = outcome[:4000]
            check.updated_at = now
            session.add(check)
            if check.obligation_id and status != "queued":
                obligation = session.get(ScanObligation, check.obligation_id)
            else:
                obligation = None
            if obligation is not None:
                obligation.status = "finding" if check.finding_id else "inconclusive"
                obligation.updated_at = now
                session.add(obligation)
                matching_traffic = [
                    traffic
                    for traffic in traffic_rows
                    if not traffic.owasp_category
                    or traffic.owasp_category == check.owasp_category
                ]
                for traffic in matching_traffic[:1]:
                    execution = ProbeExecution(
                        run_kind="web",
                        run_id=task.run_id,
                        obligation_id=obligation.id,
                        traffic_id=traffic.id,
                        session_identity=check.session_label,
                        status_code=traffic.status,
                        response_time_ms=traffic.duration_ms,
                    )
                    session.add(execution)
                    session.flush()
                    session.add(
                        CoverageEvidence(
                            execution_id=execution.id,
                            observed_behavior=outcome[:2000],
                            evaluation_oracle="deep_worker",
                            outcome="finding" if check.finding_id else "inconclusive",
                        )
                    )
        session.add(task)
        session.add(attempt)
        session.commit()


def _recover_queue(run_id: int) -> None:
    with Session(get_engine()) as session:
        variants = list(
            session.exec(
                select(DeepScanVariant)
                .where(DeepScanVariant.run_id == run_id)
                .where(DeepScanVariant.status.in_(("running", "cancelled")))
            ).all()
        )
        touched_tasks: set[int] = set()
        for variant in variants:
            was_cancelled = variant.status == "cancelled"
            if was_cancelled:
                variant.attempt_count = max(0, variant.attempt_count - 1)
            variant.status = (
                "queued" if variant.attempt_count < variant.max_attempts else "failed"
            )
            variant.worker_id = None
            variant.error_message = "Recovered after an interrupted Deep scan."
            variant.updated_at = datetime.now(_UTC)
            session.add(variant)
            touched_tasks.add(variant.task_id)
        for attempt in session.exec(
            select(DeepScanAttempt)
            .where(DeepScanAttempt.run_id == run_id)
            .where(DeepScanAttempt.status == "running")
        ).all():
            attempt.status = "failed"
            attempt.outcome = "Interrupted before the worker completed"
            attempt.error_message = "Recovered when the Deep scan resumed."
            attempt.completed_at = datetime.now(_UTC)
            session.add(attempt)
        for task_id in touched_tasks:
            task = session.get(DeepScanTask, task_id)
            if task:
                _refresh_campaign_state(session, task)
                task.error_message = "Recovered saved variant checkpoint."
                task.updated_at = datetime.now(_UTC)
                session.add(task)
        # Runs stopped on the older campaign-only implementation have no variants.
        legacy_tasks = list(
            session.exec(
                select(DeepScanTask)
                .where(DeepScanTask.run_id == run_id)
                .where(DeepScanTask.status.in_(("running", "cancelled")))
            ).all()
        )
        for task in legacy_tasks:
            if session.exec(
                select(DeepScanVariant.id).where(DeepScanVariant.task_id == task.id)
            ).first():
                continue
            if task.status == "cancelled":
                task.attempt_count = max(0, task.attempt_count - 1)
            task.status = "queued"
            task.worker_id = None
            task.updated_at = datetime.now(_UTC)
            session.add(task)
        session.commit()


def _mark_check_probe(
    task_id: int,
    variant_id: int,
    owasp_category: str,
    test_class: str | None,
    *,
    url: str = "",
    method: str = "GET",
    response_status: int | None = None,
) -> None:
    with Session(get_engine()) as session:
        task = session.get(DeepScanTask, task_id)
        if task is None:
            return
        checks = list(
            session.exec(
                select(DeepScanCheck)
                .where(DeepScanCheck.task_id == task_id)
                .where(DeepScanCheck.status.in_(("queued", "running")))
            ).all()
        )
        matching = [
            check
            for check in checks
            if (not owasp_category or check.owasp_category == owasp_category)
            and (
                not test_class
                or check.attack_class
                == _TECHNIQUE_TO_ATTACK_CLASS.get(test_class, test_class)
            )
        ]
        if not matching and owasp_category:
            matching = [c for c in checks if c.owasp_category == owasp_category]
        if matching:
            matching[0].status = "running"
            matching[0].updated_at = datetime.now(_UTC)
            session.add(matching[0])
        fingerprint = _fingerprint(
            task_id,
            variant_id,
            method,
            _canonical_route(url) if url else "",
            test_class,
            owasp_category,
            response_status,
        )
        if (
            session.exec(
                select(DeepScanProbeOutcome.id)
                .where(DeepScanProbeOutcome.run_id == task.run_id)
                .where(DeepScanProbeOutcome.fingerprint == fingerprint)
            ).first()
            is None
        ):
            strength = 2 if response_status and response_status >= 400 else 1
            session.add(
                DeepScanProbeOutcome(
                    run_id=task.run_id,
                    task_id=task_id,
                    variant_id=variant_id,
                    check_id=matching[0].id if matching else None,
                    fingerprint=fingerprint,
                    technique=test_class or "",
                    request_summary=f"{method} {url}"[:2000],
                    response_status=response_status,
                    signal_type="error_or_denial" if strength == 2 else "response",
                    signal_strength=strength,
                )
            )
        session.commit()


def _record_task_finding(
    run_id: int, task_id: int, variant_id: int, finding: ScanFinding, raw: dict
) -> None:
    with Session(get_engine()) as session:
        if (
            session.exec(
                select(DeepScanTaskFinding)
                .where(DeepScanTaskFinding.task_id == task_id)
                .where(DeepScanTaskFinding.finding_id == finding.id)
            ).first()
            is None
        ):
            session.add(
                DeepScanTaskFinding(
                    run_id=run_id,
                    task_id=task_id,
                    variant_id=variant_id,
                    finding_id=finding.id,
                )
            )
        claim_fingerprint = _fingerprint(
            finding.affected_url, finding.title, finding.owasp_category
        )
        claim = session.exec(
            select(DeepScanClaim)
            .where(DeepScanClaim.run_id == run_id)
            .where(DeepScanClaim.fingerprint == claim_fingerprint)
        ).first()
        if claim is None:
            session.add(
                DeepScanClaim(
                    run_id=run_id,
                    task_id=task_id,
                    variant_id=variant_id,
                    fingerprint=claim_fingerprint,
                    title=finding.title,
                    status="confirmed",
                    finding_id=finding.id,
                    evidence_json=json.dumps({"finding_id": finding.id}),
                )
            )
        else:
            claim.status = "confirmed"
            claim.finding_id = claim.finding_id or finding.id
            claim.updated_at = datetime.now(_UTC)
            session.add(claim)
        checks = list(
            session.exec(
                select(DeepScanCheck).where(DeepScanCheck.task_id == task_id)
            ).all()
        )
        category = str(raw.get("owasp_category") or finding.owasp_category or "")
        title = str(raw.get("title") or finding.title or "").lower()
        matching = [check for check in checks if check.owasp_category == category]
        if len(matching) > 1:
            named = [check for check in matching if check.attack_class in title]
            matching = named or matching
        if matching:
            matching[0].finding_id = finding.id
            matching[0].status = "finding"
            matching[0].outcome = finding.title
            matching[0].updated_at = datetime.now(_UTC)
            session.add(matching[0])
        session.commit()


async def _run_deep_scan(run_id: int) -> None:
    """Seed and drain the Deep queue using bounded parallel attack workers."""
    from aespa.services import scanner as scanner_svc
    from aespa.services.scan_leads import update_lead
    from aespa.services.web_workprogram import (
        _make_web_post_finding_fn,
        _make_web_post_probe_fn,
        mark_in_progress_to_covered,
    )

    _recover_queue(run_id)
    _emit_test_lead_progress(
        run_id,
        "Building the Deep tester queue",
        "Grouping recon evidence, coverage checks, workflows, and SAST leads.",
    )
    events_svc.emit(
        run_id,
        {
            "type": "scanner_phase",
            "phase": "deep_recon",
            "status": "start",
            "message": "Building Deep testers from recon, coverage, and SAST leads.",
        },
    )
    created = seed_deep_tasks(run_id)
    with Session(get_engine()) as session:
        run = session.get(TestRun, run_id)
        site = session.get(Site, run.site_id) if run else None
        if run is None or site is None:
            raise ValueError("Deep scan target is unavailable")
        config = get_deep_scan_config(session)
        llm_cfg = get_llm_config_for_role(session, run, "specialist")
        scanner_policy = get_run_scanner_policy(session, run)
        if llm_cfg is None:
            raise RuntimeError(
                "No specialist model is configured for Deep scan workers"
            )
        run.phase = "scanning"
        session.add(run)
        session.commit()
        site_id = site.id
        base_url = site.base_url
    _seed_baseline_variants(run_id, reuse_captured=config.reuse_captured_baselines)
    with Session(get_engine()) as session:
        ordered_tasks = list(
            session.exec(
                select(DeepScanTask)
                .where(DeepScanTask.run_id == run_id)
                .order_by(DeepScanTask.priority.desc(), DeepScanTask.id)
            ).all()
        )
        tester_details = {
            task.id: (index + 1, task.title)
            for index, task in enumerate(ordered_tasks)
            if task.id is not None
        }
        completed_baselines = list(
            session.exec(
                select(DeepScanVariant)
                .where(DeepScanVariant.run_id == run_id)
                .where(DeepScanVariant.kind == "baseline")
                .where(DeepScanVariant.status == "complete")
            ).all()
        )
        variant_task_ids = list(
            session.exec(
                select(DeepScanVariant.task_id).where(DeepScanVariant.run_id == run_id)
            ).all()
        )
        variant_counts = Counter(variant_task_ids)
        ready_task_ids = [
            baseline.task_id
            for baseline in completed_baselines
            if not _planning_is_complete(baseline)
            and variant_counts[baseline.task_id] == 1
        ]
    session_vault = session_svc.load_session_vault(run_id)
    scanner_svc._finding_hooks[run_id] = _make_web_post_finding_fn(run_id)
    events_svc.emit(
        run_id,
        {
            "type": "deep_queue_update",
            "status": "ready",
            "created": created,
            **get_queue(run_id),
        },
    )

    async def worker(slot: int) -> None:
        worker_label = f"deep-worker-{slot}"
        while run_id not in scanner_svc._thinking_stop_requested:
            claimed = await _claim_variant(run_id, worker_label)
            if claimed is None:
                if _queue_has_active_variants(run_id) or _queue_needs_planning(run_id):
                    await asyncio.sleep(0.05)
                    continue
                return
            task, variant, attempt_id = claimed
            tester_number, _ = tester_details.get(task.id, (0, task.title))
            agent_id = f"{worker_label}-task-{task.id}-variant-{variant.id}"
            campaign_checks = (
                "" if variant.kind == "baseline" else f"\n\n{task.hypothesis}"
            )
            variant_brief = (
                f"Tester: {task.title}\nAssigned purpose: {variant.purpose}\n"
                f"Why this variant exists: {variant.rationale}\n"
                f"How it differs: {variant.difference}{campaign_checks}\n\n"
                f"{_shared_ledger_brief(task.id)}"
            )
            handoff, _ = handoff_svc.create_or_get_handoff(
                run_id=run_id,
                run_kind="web",
                attack_class=task.attack_class,
                target_url=task.target_url,
                page_id=task.page_id,
                parameter=(
                    f"{task.parameter or 'target'}|deep-task:{task.id}|"
                    f"variant:{variant.id}"
                ),
                session_label=task.session_label,
                priority=task.priority,
                rationale=variant_brief,
                dispatch_source="deep",
                agent_id=agent_id,
            )
            with Session(get_engine()) as session:
                stored = session.get(DeepScanTask, task.id)
                stored_variant = session.get(DeepScanVariant, variant.id)
                if stored:
                    stored.handoff_id = handoff.id
                    stored.worker_id = agent_id
                    session.add(stored)
                if stored_variant:
                    stored_variant.handoff_id = handoff.id
                    stored_variant.worker_id = agent_id
                    session.add(stored_variant)
                session.commit()
            events_svc.emit(
                run_id,
                {
                    "type": "deep_queue_update",
                    "status": "running",
                    "task_id": task.id,
                    "variant": _variant_dict(variant),
                },
            )
            _emit_test_lead_progress(
                run_id,
                f"Assigned Tester {tester_number}, Variant {variant.variant_index} to Attack Worker {slot}",
                variant.purpose,
            )
            try:
                base_post_probe = _make_web_post_probe_fn(run_id)

                def deep_post_probe(
                    url: str,
                    method: str,
                    owasp_category: str,
                    test_class: str | None = None,
                    response_status: int | None = None,
                    page_id: int | None = None,
                ):
                    category = owasp_category or task.owasp_category
                    result = base_post_probe(
                        url,
                        method,
                        category,
                        test_class,
                        response_status,
                        page_id if page_id is not None else task.page_id,
                    )
                    _mark_check_probe(
                        task.id,
                        variant.id,
                        category,
                        test_class,
                        url=url,
                        method=method,
                        response_status=response_status,
                    )
                    observed_strategy = _TECHNIQUE_TO_ATTACK_CLASS.get(
                        test_class or "", test_class or ""
                    )
                    if observed_strategy and variant.strategy not in {
                        "baseline",
                        observed_strategy,
                    }:
                        _record_variant_pivot(
                            variant.id,
                            f"Investigate the {observed_strategy.replace('_', ' ')} signal observed during this variant.",
                        )
                    return result

                def deep_post_finding(finding: ScanFinding, raw: dict) -> None:
                    _record_task_finding(run_id, task.id, variant.id, finding, raw)

                await scanner_svc._run_specialist_agent(
                    run_id=run_id,
                    agent_id=agent_id,
                    attack_class="deep_campaign",
                    target_url=task.target_url,
                    rationale=variant_brief,
                    session_vault=session_vault,
                    llm_cfg=llm_cfg,
                    base_url=base_url,
                    scanner_policy=scanner_policy,
                    max_steps=config.max_steps_per_task,
                    site_id=site_id,
                    target_page_id=task.page_id,
                    target_session_label=(
                        _json_list(variant.identity_requirements_json)[0]
                        if _json_list(variant.identity_requirements_json)
                        else None
                    ),
                    handoff_id=handoff.id,
                    agent_role=f"{task.title} · {variant.purpose}",
                    event_phase="deep_worker_step",
                    post_probe_fn=deep_post_probe,
                    post_finding_fn=deep_post_finding,
                    default_owasp_category=task.owasp_category,
                    system_prompt_override=(
                        _DEEP_BASELINE_PROMPT
                        if variant.kind == "baseline"
                        else _DEEP_CAMPAIGN_PROMPT
                    ),
                    tools_override=scanner_svc._get_specialist_tools("crypto"),
                )
                persisted = handoff_svc.get_handoff(handoff.id)
                with Session(get_engine()) as session:
                    links = list(
                        session.exec(
                            select(DeepScanTaskFinding).where(
                                DeepScanTaskFinding.task_id == task.id,
                                DeepScanTaskFinding.variant_id == variant.id,
                            )
                        ).all()
                    )
                finding_id = (
                    links[0].finding_id
                    if links
                    else (persisted.finding_id if persisted else None)
                )
                finding_count = len({link.finding_id for link in links}) or int(
                    bool(finding_id)
                )
                outcome = (persisted.outcome if persisted else None) or (
                    f"{finding_count} new finding{'s' if finding_count != 1 else ''}"
                    if finding_id
                    else "No confirmed finding"
                )
                if persisted is not None and persisted.status == "failed":
                    retry_status = (
                        "queued"
                        if variant.attempt_count < variant.max_attempts
                        else "failed"
                    )
                    _finish_variant(
                        variant.id,
                        attempt_id,
                        status=retry_status,
                        outcome=outcome,
                        error=outcome,
                    )
                else:
                    signal_strength, _ = _finish_variant(
                        variant.id,
                        attempt_id,
                        status=(
                            "complete"
                            if variant.kind == "baseline"
                            else "finding"
                            if finding_id
                            else "inconclusive"
                        ),
                        outcome=outcome,
                    )
                    if variant.kind == "baseline":
                        await _plan_tester_variants(
                            run_id,
                            task.id,
                            tester_number,
                            task.title,
                            llm_cfg,
                            config,
                        )
                    elif _maybe_add_follow_up(
                        task.id, variant.id, config, signal_strength
                    ):
                        _record_variant_pivot(
                            variant.id,
                            "Produced a new response signal; a separate confirmation variant was queued.",
                        )
                    with Session(get_engine()) as session:
                        lead_ids = {
                            check.lead_id
                            for check in session.exec(
                                select(DeepScanCheck).where(
                                    DeepScanCheck.task_id == task.id
                                )
                            ).all()
                            if check.lead_id
                        }
                    for lead_id in lead_ids if variant.kind != "baseline" else []:
                        update_lead(
                            lead_id,
                            status="confirmed" if finding_id else "inconclusive",
                            note=outcome,
                            owner_run_type="web",
                            owner_run_id=run_id,
                            investigated_by_run_type="web",
                            investigated_by_run_id=run_id,
                            linked_finding_id=finding_id,
                        )
            except asyncio.CancelledError:
                _finish_variant(
                    variant.id,
                    attempt_id,
                    status="queued",
                    attempt_status="cancelled",
                    consume_attempt=False,
                    outcome="Stopped before this task completed",
                )
                raise
            except llm_svc.LLMQuotaPauseError:
                _finish_variant(
                    variant.id,
                    attempt_id,
                    status="queued",
                    attempt_status="paused",
                    consume_attempt=False,
                    outcome="Paused because the model allowance was exhausted",
                )
                raise
            except Exception as exc:
                log.exception("Deep worker failed: run=%s task=%s", run_id, task.id)
                retry_status = (
                    "queued"
                    if variant.attempt_count < variant.max_attempts
                    else "failed"
                )
                _finish_variant(
                    variant.id,
                    attempt_id,
                    status=retry_status,
                    outcome="Worker failed",
                    error=str(exc),
                )
            events_svc.emit(
                run_id,
                {"type": "deep_queue_update", "status": "changed", **get_queue(run_id)},
            )
            queue = get_queue(run_id)
            active_count = queue["counts"].get("running", 0)
            queued_count = queue["counts"].get("queued", 0)
            complete_count = sum(
                queue["counts"].get(status, 0) for status in ("finding", "inconclusive")
            )
            _emit_test_lead_progress(
                run_id,
                f"Tester {tester_number}, Variant {variant.variant_index} finished",
                f"{active_count} active, {queued_count} queued, {complete_count} testers complete.",
            )

    events_svc.emit(
        run_id,
        {
            "type": "scanner_phase",
            "phase": "deep_attack",
            "status": "start",
            "message": (
                f"Starting {config.max_concurrent_workers} Deep attack workers and "
                f"up to {config.max_concurrent_planners} concurrent planner calls."
            ),
        },
    )
    _emit_test_lead_progress(
        run_id,
        f"Starting {config.max_concurrent_workers} Deep attack workers",
        (
            f"{len(ready_task_ids)} testers are ready for planning; "
            f"up to {config.max_concurrent_planners} plans will run at once."
        ),
    )
    planning_task = asyncio.create_task(
        _plan_ready_testers(run_id, ready_task_ids, tester_details, llm_cfg, config),
        name=f"deep-planners-{run_id}",
    )
    worker_tasks = [
        asyncio.create_task(worker(slot + 1), name=f"deep-worker-{run_id}-{slot + 1}")
        for slot in range(config.max_concurrent_workers)
    ]
    try:
        await asyncio.gather(planning_task, *worker_tasks)
    except BaseException:
        active_tasks = [planning_task, *worker_tasks]
        for active_task in active_tasks:
            if not active_task.done():
                active_task.cancel()
        await asyncio.gather(*active_tasks, return_exceptions=True)
        raise
    stopped = run_id in scanner_svc._thinking_stop_requested
    if not stopped:
        mark_in_progress_to_covered(run_id)
    with Session(get_engine()) as session:
        run = session.get(TestRun, run_id)
        finding_count = len(
            session.exec(
                select(ScanFinding).where(ScanFinding.test_run_id == run_id)
            ).all()
        )
        unresolved_leads = []
        if config.include_sast_leads:
            from aespa.services.scan_leads import get_all_leads_for_run

            unresolved_leads = [
                lead
                for lead in get_all_leads_for_run("web", run_id)
                if lead.status not in {"confirmed", "dismissed", "inconclusive"}
            ]
        queue_counts = get_queue(run_id)["counts"]
        failed = queue_counts.get("failed", 0)
        unfinished = queue_counts.get("queued", 0) + queue_counts.get("running", 0)
        if run is not None:
            run.phase = "finished"
            if stopped:
                run.status = "stopped"
                run.outcome = "stopped"
                run.terminal_reason = "user_stop"
            elif failed or unfinished or unresolved_leads:
                run.status = "incomplete"
                run.outcome = "incomplete"
                run.terminal_reason = "deep_tasks_incomplete"
            else:
                run.status = "complete"
                run.outcome = "complete"
                run.terminal_reason = "coverage_complete"
            run.completed_at = datetime.now(_UTC)
            session.add(run)
            session.commit()
    scanner_svc._thinking_scan_status[run_id] = "stopped" if stopped else "complete"
    scanner_svc._emit_thinking_status(run_id)
    if not stopped:
        scanner_svc._emit_scan_complete(run_id, finding_count)
    events_svc.emit(
        run_id,
        {
            "type": "scanner_phase",
            "phase": "deep_attack",
            "status": "complete" if not stopped else "warning",
            "message": "Deep attack queue finished."
            if not stopped
            else "Deep attack queue stopped.",
            "data": get_queue(run_id),
        },
    )


async def run_deep_scan(run_id: int) -> None:
    """Run Deep DAST with token usage attributed to the owning web run."""
    llm_svc.set_run_context(run_id, lambda event: events_svc.emit(run_id, event))
    try:
        await _run_deep_scan(run_id)
    finally:
        from aespa.services import scanner as scanner_svc

        scanner_svc._finding_hooks.pop(run_id, None)
        llm_svc.clear_run_context()
        _claim_locks.pop(run_id, None)
        _planning_commit_locks.pop(run_id, None)
        _planner_semaphores.pop(run_id, None)
        _planning_scheduled_task_ids.pop(run_id, None)
        _planning_active_task_ids.pop(run_id, None)
