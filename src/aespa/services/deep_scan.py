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
    DeepScanTask,
    DeepScanTaskFinding,
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

_DEEP_CAMPAIGN_PROMPT = """You are a Deep Attack Worker. Test one bounded HTTP operation,
saved workflow, systemic recon area, or imported SAST lead. Your briefing lists the checks
inside this campaign. Reuse request baselines, browser state, and sessions across those checks.
Work through applicable checks in risk order. Do not repeat the same request for each label.
Create a follow-up probe only when traffic, a response difference, or source evidence supports
it. Put the relevant OWASP category and test class on each probe. Write a finding only with
direct tool evidence. Stop before bulk data access or unsafe state changes. Call done when the
applicable checks are complete or the remaining checks have a specific blocker."""

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


def _canonical_route(url: str) -> str:
    parsed = urlparse(url)
    path = re.sub(
        r"/(?:(?:\d+)|(?:[0-9a-f]{8}-[0-9a-f-]{27,}))(?=/|$)",
        "/{id}",
        parsed.path,
        flags=re.I,
    )
    return urlunparse((parsed.scheme, parsed.netloc, path or "/", "", "", parsed.fragment))


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


def _task_dict(
    task: DeepScanTask,
    checks: list[DeepScanCheck] | None = None,
    finding_ids: list[int] | None = None,
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
                select(DeepScanTaskFinding).where(
                    DeepScanTaskFinding.run_id == run_id
                )
            ).all()
        )
    checks_by_task: dict[int, list[DeepScanCheck]] = {}
    findings_by_task: dict[int, list[int]] = {}
    for check in checks:
        checks_by_task.setdefault(check.task_id, []).append(check)
    for link in links:
        findings_by_task.setdefault(link.task_id, []).append(link.finding_id)
    counts = Counter(row.status for row in rows)
    return {
        "run_id": run_id,
        "total": len(rows),
        "counts": dict(counts),
        "checks_total": len(checks),
        "tasks": [
            _task_dict(
                row,
                checks_by_task.get(row.id or -1, []),
                findings_by_task.get(row.id or -1, []),
            )
            for row in rows
        ],
    }


def _campaign_brief(checks: list[dict]) -> str:
    lines = [
        "Test this operation as one campaign. Work through these checks and reuse request and session context:",
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
        selected = sast[: config.max_tasks]
        remaining = config.max_tasks - len(selected)
        systemic_slots = (
            min(len(systemic), max(1, remaining // 10))
            if remaining and (remaining > 1 or not operations)
            else 0
        )
        selected.extend(systemic[:systemic_slots])
        remaining = config.max_tasks - len(selected)
        workflow_slots = remaining if not operations else min(len(workflows), remaining // 3)
        selected.extend(workflows[:workflow_slots])
        remaining = config.max_tasks - len(selected)
        selected.extend(operations[:remaining])
        remaining = config.max_tasks - len(selected)
        leftovers = systemic[systemic_slots:] + workflows[workflow_slots:]
        selected.extend(leftovers[:remaining])
        for campaign in selected:
            _persist_campaign(session, run_id, campaign)
        session.commit()
    return len(selected)


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
        rows = list(
            session.exec(
                select(DeepScanTask)
                .where(DeepScanTask.run_id == run_id)
                .where(DeepScanTask.status.in_(("running", "cancelled")))
            ).all()
        )
        for task in rows:
            was_cancelled = task.status == "cancelled"
            if was_cancelled:
                task.attempt_count = max(0, task.attempt_count - 1)
            task.status = (
                "queued" if task.attempt_count < task.max_attempts else "failed"
            )
            task.worker_id = None
            task.error_message = "Recovered after an interrupted Deep scan."
            task.updated_at = datetime.now(_UTC)
            session.add(task)
            for check in session.exec(
                select(DeepScanCheck).where(DeepScanCheck.task_id == task.id)
            ).all():
                check.status = task.status
                check.updated_at = datetime.now(_UTC)
                session.add(check)
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
        session.commit()


def _mark_check_probe(
    task_id: int, owasp_category: str, test_class: str | None
) -> None:
    with Session(get_engine()) as session:
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
            and (not test_class or check.attack_class == _TECHNIQUE_TO_ATTACK_CLASS.get(test_class, test_class))
        ]
        if not matching and owasp_category:
            matching = [c for c in checks if c.owasp_category == owasp_category]
        if matching:
            matching[0].status = "running"
            matching[0].updated_at = datetime.now(_UTC)
            session.add(matching[0])
            session.commit()


def _record_task_finding(
    run_id: int, task_id: int, finding: ScanFinding, raw: dict
) -> None:
    with Session(get_engine()) as session:
        if session.exec(
            select(DeepScanTaskFinding)
            .where(DeepScanTaskFinding.task_id == task_id)
            .where(DeepScanTaskFinding.finding_id == finding.id)
        ).first() is None:
            session.add(
                DeepScanTaskFinding(
                    run_id=run_id, task_id=task_id, finding_id=finding.id
                )
            )
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
    events_svc.emit(
        run_id,
        {
            "type": "scanner_phase",
            "phase": "deep_recon",
            "status": "start",
            "message": "Building Deep attack tasks from recon, coverage, and SAST leads.",
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
            claimed = await _claim_task(run_id, worker_label)
            if claimed is None:
                return
            task, attempt_id = claimed
            agent_id = f"{worker_label}-task-{task.id}"
            handoff, _ = handoff_svc.create_or_get_handoff(
                run_id=run_id,
                run_kind="web",
                attack_class=task.attack_class,
                target_url=task.target_url,
                page_id=task.page_id,
                parameter=f"{task.parameter or 'target'}|deep-task:{task.id}",
                session_label=task.session_label,
                priority=task.priority,
                rationale=task.hypothesis,
                dispatch_source="deep",
                agent_id=agent_id,
            )
            with Session(get_engine()) as session:
                stored = session.get(DeepScanTask, task.id)
                if stored:
                    stored.handoff_id = handoff.id
                    stored.worker_id = agent_id
                    session.add(stored)
                    session.commit()
            events_svc.emit(
                run_id,
                {
                    "type": "deep_queue_update",
                    "status": "running",
                    "task": _task_dict(task),
                },
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
                    _mark_check_probe(task.id, category, test_class)
                    return result

                def deep_post_finding(finding: ScanFinding, raw: dict) -> None:
                    _record_task_finding(run_id, task.id, finding, raw)

                await scanner_svc._run_specialist_agent(
                    run_id=run_id,
                    agent_id=agent_id,
                    attack_class="deep_campaign",
                    target_url=task.target_url,
                    rationale=task.hypothesis,
                    session_vault=session_vault,
                    llm_cfg=llm_cfg,
                    base_url=base_url,
                    scanner_policy=scanner_policy,
                    max_steps=config.max_steps_per_task,
                    site_id=site_id,
                    target_page_id=task.page_id,
                    target_session_label=None,
                    handoff_id=handoff.id,
                    agent_role=(
                        task.title or task.attack_class.replace("_", " ").capitalize()
                    ),
                    event_phase="deep_worker_step",
                    post_probe_fn=deep_post_probe,
                    post_finding_fn=deep_post_finding,
                    default_owasp_category=task.owasp_category,
                    system_prompt_override=_DEEP_CAMPAIGN_PROMPT,
                    tools_override=scanner_svc._get_specialist_tools("crypto"),
                )
                persisted = handoff_svc.get_handoff(handoff.id)
                with Session(get_engine()) as session:
                    links = list(
                        session.exec(
                            select(DeepScanTaskFinding).where(
                                DeepScanTaskFinding.task_id == task.id
                            )
                        ).all()
                    )
                finding_id = links[0].finding_id if links else (
                    persisted.finding_id if persisted else None
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
                        "queued" if task.attempt_count < task.max_attempts else "failed"
                    )
                    _finish_task(
                        task.id,
                        attempt_id,
                        status=retry_status,
                        outcome=outcome,
                        error=outcome,
                    )
                else:
                    _finish_task(
                        task.id,
                        attempt_id,
                        status="finding" if finding_id else "inconclusive",
                        outcome=outcome,
                        finding_id=finding_id,
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
                    for lead_id in lead_ids:
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
                _finish_task(
                    task.id,
                    attempt_id,
                    status="queued",
                    attempt_status="cancelled",
                    consume_attempt=False,
                    outcome="Stopped before this task completed",
                )
                raise
            except llm_svc.LLMQuotaPauseError:
                _finish_task(
                    task.id,
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
                    "queued" if task.attempt_count < task.max_attempts else "failed"
                )
                _finish_task(
                    task.id,
                    attempt_id,
                    status=retry_status,
                    outcome="Worker failed",
                    error=str(exc),
                )
            events_svc.emit(
                run_id,
                {"type": "deep_queue_update", "status": "changed", **get_queue(run_id)},
            )

    events_svc.emit(
        run_id,
        {
            "type": "scanner_phase",
            "phase": "deep_attack",
            "status": "start",
            "message": f"Starting {config.max_concurrent_workers} Deep attack workers.",
        },
    )
    worker_tasks = [
        asyncio.create_task(worker(slot + 1), name=f"deep-worker-{run_id}-{slot + 1}")
        for slot in range(config.max_concurrent_workers)
    ]
    try:
        await asyncio.gather(*worker_tasks)
    except BaseException:
        for worker_task in worker_tasks:
            if not worker_task.done():
                worker_task.cancel()
        await asyncio.gather(*worker_tasks, return_exceptions=True)
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
