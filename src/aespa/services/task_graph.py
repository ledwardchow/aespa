from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse

from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import CrawledPage, PentestHypothesis, PentestTask, TargetIntelItem
from aespa.schemas import PentestHypothesisOut, PentestTaskGraphOut, PentestTaskOut
from aespa.services import events as events_svc


MAX_TASKS_PER_HYPOTHESIS = 20


@dataclass(frozen=True)
class TaskSeed:
    title: str
    description: str
    target_url: str
    method: str
    task_type: str
    priority: int
    evidence: str
    intel_id: int | None = None


def seed_task_graph(run_id: int, session: Session | None = None) -> dict[str, int]:
    """Create deterministic hypotheses/tasks from target intelligence.

    This gives the dynamic scanner an explicit work queue before the LLM starts
    making requests, and keeps that queue visible in the UI.
    """
    created_hypotheses = 0
    created_tasks = 0

    own_session = session is None
    s = session or Session(get_engine())
    try:
        intel = list(s.exec(
            select(TargetIntelItem)
            .where(TargetIntelItem.test_run_id == run_id)
            .order_by(TargetIntelItem.kind, TargetIntelItem.discovered_at.desc())
        ))
        pages = list(s.exec(
            select(CrawledPage)
            .where(CrawledPage.test_run_id == run_id)
            .where(CrawledPage.in_scope != False)  # noqa: E712
            .order_by(CrawledPage.depth, CrawledPage.url)
        ))

        specs = _build_seed_specs(intel, pages)
        for spec in specs:
            hypothesis, is_new = _ensure_hypothesis(
                s,
                run_id=run_id,
                title=spec["title"],
                description=spec["description"],
                attack_area=spec["attack_area"],
                owasp_category=spec["owasp_category"],
                priority=spec["priority"],
                confidence=spec["confidence"],
                rationale=spec["rationale"],
                created_from=spec["created_from"],
                related_intel_ids=spec["related_intel_ids"],
            )
            if is_new:
                created_hypotheses += 1
            for task in spec["tasks"][:MAX_TASKS_PER_HYPOTHESIS]:
                if _ensure_task(s, run_id, hypothesis.id, task):
                    created_tasks += 1

        s.commit()
    finally:
        if own_session:
            s.close()

    return {"hypotheses_created": created_hypotheses, "tasks_created": created_tasks}


def get_task_graph(run_id: int, session: Session | None = None) -> PentestTaskGraphOut:
    own_session = session is None
    s = session or Session(get_engine())
    try:
        hypotheses = list(s.exec(
            select(PentestHypothesis)
            .where(PentestHypothesis.test_run_id == run_id)
            .order_by(PentestHypothesis.priority.desc(), PentestHypothesis.created_at)
        ))
        tasks = list(s.exec(
            select(PentestTask)
            .where(PentestTask.test_run_id == run_id)
            .order_by(PentestTask.status, PentestTask.priority.desc(), PentestTask.created_at)
        ))
    finally:
        if own_session:
            s.close()

    counts: dict[str, int] = {
        "hypotheses": len(hypotheses),
        "tasks": len(tasks),
    }
    for h in hypotheses:
        counts[f"hypothesis_{h.status}"] = counts.get(f"hypothesis_{h.status}", 0) + 1
    for t in tasks:
        counts[f"task_{t.status}"] = counts.get(f"task_{t.status}", 0) + 1

    return PentestTaskGraphOut(
        counts=counts,
        hypotheses=[PentestHypothesisOut.model_validate(h) for h in hypotheses],
        tasks=[PentestTaskOut.model_validate(t) for t in tasks],
    )


def build_task_graph_context(run_id: int, limit: int = 16) -> str:
    graph = get_task_graph(run_id)
    if not graph.hypotheses and not graph.tasks:
        return ""

    open_hypotheses = [
        h for h in graph.hypotheses
        if h.status in {"open", "testing"}
    ][:8]
    active_tasks = [
        t for t in graph.tasks
        if t.status in {"queued", "running", "blocked"}
    ][:limit]
    if not open_hypotheses and not active_tasks:
        return ""

    lines = ["Target-driven task graph:"]
    if open_hypotheses:
        lines.append("Hypotheses:")
        for h in open_hypotheses:
            lines.append(
                f"- H{h.id} [{h.status}, p{h.priority}, {h.owasp_category or h.attack_area}]: "
                f"{h.title} — {h.rationale[:180]}"
            )
    if active_tasks:
        lines.append("Queued/running tasks:")
        for t in active_tasks:
            target = f" {t.method} {t.target_url}" if t.target_url else ""
            lines.append(
                f"- T{t.id} [{t.status}, {t.task_type}, p{t.priority}]: "
                f"{t.title}{target}. {t.description[:180]}"
            )
    lines.append(
        "Prefer executing high-priority queued tasks, updating evidence through concrete requests, "
        "and writing findings only when the hypothesis is supported by reproducible evidence."
    )
    return "\n".join(lines)


def mark_task_running_for_action(run_id: int, action: dict, step: int) -> int | None:
    action_type = str(action.get("action") or "").lower()
    if action_type in {"done", "tool"}:
        return None
    target_url = str(action.get("url") or action.get("affected_url") or "")
    note = " ".join(str(action.get(k) or "") for k in (
        "note", "hypothesis", "observation", "payload_purpose", "title"
    ))
    with Session(get_engine()) as s:
        tasks = list(s.exec(
            select(PentestTask)
            .where(PentestTask.test_run_id == run_id)
            .where(PentestTask.status.in_(["queued", "running", "blocked"]))
            .order_by(PentestTask.priority.desc(), PentestTask.created_at)
        ))
        task = _best_task_for_action(tasks, target_url, note, action_type)
        if task is None:
            return None
        now = _now()
        task.status = "running"
        task.last_action_step = step
        task.updated_at = now
        if task.hypothesis_id:
            hypothesis = s.get(PentestHypothesis, task.hypothesis_id)
            if hypothesis and hypothesis.status == "open":
                hypothesis.status = "testing"
                hypothesis.updated_at = now
        s.add(task)
        s.commit()
        task_id = task.id
    _emit_update(run_id, "task_started", {"task_id": task_id, "step": step})
    return task_id


def complete_task_after_result(
    run_id: int,
    task_id: int | None,
    *,
    step: int,
    method: str,
    url: str,
    status: int | None,
    note: str,
    response_excerpt: str = "",
    finding_written: bool = False,
) -> None:
    if task_id is None:
        return
    with Session(get_engine()) as s:
        task = s.get(PentestTask, task_id)
        if task is None or task.test_run_id != run_id:
            return
        now = _now()
        task.status = "done" if status and status < 500 else "blocked"
        task.last_action_step = step
        task.result_summary = _truncate(
            f"{method} {url} -> {status if status is not None else 'n/a'}. {note}",
            1000,
        )
        if response_excerpt:
            task.evidence = _truncate(response_excerpt, 2000)
        task.updated_at = now

        if task.hypothesis_id:
            hypothesis = s.get(PentestHypothesis, task.hypothesis_id)
            if hypothesis:
                if finding_written:
                    hypothesis.status = "confirmed"
                    hypothesis.confidence = max(float(hypothesis.confidence or 0), 0.9)
                elif hypothesis.status == "testing":
                    remaining = s.exec(
                        select(PentestTask)
                        .where(PentestTask.hypothesis_id == hypothesis.id)
                        .where(PentestTask.status.in_(["queued", "running", "blocked"]))
                    ).first()
                    if remaining is None:
                        hypothesis.status = "unconfirmed"
                hypothesis.updated_at = now

        s.add(task)
        s.commit()
    _emit_update(run_id, "task_completed", {"task_id": task_id, "step": step})


def mark_related_hypothesis_confirmed(run_id: int, task_id: int | None) -> None:
    if task_id is None:
        return
    with Session(get_engine()) as s:
        task = s.get(PentestTask, task_id)
        if task is None or task.test_run_id != run_id or not task.hypothesis_id:
            return
        hypothesis = s.get(PentestHypothesis, task.hypothesis_id)
        if hypothesis is None:
            return
        hypothesis.status = "confirmed"
        hypothesis.confidence = max(float(hypothesis.confidence or 0), 0.9)
        hypothesis.updated_at = _now()
        s.add(hypothesis)
        s.commit()
    _emit_update(run_id, "hypothesis_confirmed", {"task_id": task_id})


def _build_seed_specs(intel: list[TargetIntelItem], pages: list[CrawledPage]) -> list[dict]:
    specs: list[dict] = []

    def add_spec(
        key: str,
        title: str,
        description: str,
        attack_area: str,
        owasp_category: str,
        priority: int,
        confidence: float,
        rationale: str,
        created_from: str,
        tasks: list[TaskSeed],
    ) -> None:
        if not tasks:
            return
        related = [t.intel_id for t in tasks if t.intel_id is not None]
        specs.append({
            "key": key,
            "title": title,
            "description": description,
            "attack_area": attack_area,
            "owasp_category": owasp_category,
            "priority": priority,
            "confidence": confidence,
            "rationale": rationale,
            "created_from": created_from,
            "related_intel_ids": sorted(set(related)),
            "tasks": _dedupe_tasks(tasks),
        })

    public_config_tasks = [
        _task_from_intel(
            item,
            "Check whether operational/config endpoint leaks sensitive data",
            "Fetch the endpoint anonymously and with available sessions; inspect status, headers, and body for secrets, debug flags, environment names, or version disclosure.",
            "misconfig",
            88,
        )
        for item in intel
        if _looks_like_public_config_endpoint(item)
    ]
    add_spec(
        "public_config",
        "Public operational/config endpoint exposure",
        "Operational endpoints and generated API docs often leak environment details, keys, debug settings, or internal routes.",
        "misconfiguration",
        "A05",
        88,
        0.78,
        "Crawler/asset mining found endpoint names commonly associated with health, config, docs, status, or debug surfaces.",
        "target_intelligence",
        public_config_tasks,
    )

    sensitive_fields = [
        _task_from_intel(
            item,
            f"Trace exposure of response field `{item.key}`",
            "Identify the response or endpoint that emits this field, then determine whether it leaks credentials, secrets, roles, or sensitive user attributes.",
            "data_exposure",
            92,
        )
        for item in intel
        if item.kind == "response_field" and _looks_sensitive_name(item.key)
    ]
    add_spec(
        "sensitive_fields",
        "Sensitive field exposure",
        "Fields with secret-like or privilege-bearing names deserve focused verification across user roles and unauthenticated access.",
        "data exposure",
        "A02",
        92,
        0.82,
        "Response mining identified fields whose names imply credentials, tokens, secrets, hashes, roles, or MFA state.",
        "target_intelligence",
        sensitive_fields,
    )

    storage_tasks = [
        _task_from_intel(
            item,
            f"Review client-side storage key `{item.key}`",
            "Inspect local/session storage and related JavaScript to determine whether tokens or sensitive state can be stolen, replayed, or tampered with.",
            "auth",
            82,
        )
        for item in intel
        if item.kind == "storage_key" and _looks_tokenish(item.key, item.value)
    ]
    add_spec(
        "storage_tokens",
        "Client-side token/session storage review",
        "Token-like browser storage can expose bearer material or unsigned client-side authorization state.",
        "authentication",
        "A07",
        82,
        0.74,
        "The crawler observed storage keys/values that look like auth tokens or session state.",
        "target_intelligence",
        storage_tasks,
    )

    input_tasks = [
        _task_from_intel(
            item,
            f"Probe input `{item.key}` for validation and injection behavior",
            "Exercise benign injection markers, boundary values, and reflected values through this input while preserving application state.",
            "input",
            76,
        )
        for item in intel
        if item.kind in {"input", "form"} and _looks_attackable_input(item.key, item.value)
    ]
    add_spec(
        "input_validation",
        "Input validation and injection testing",
        "Search, filter, identity, message, and free-form fields are strong candidates for injection and output encoding checks.",
        "input validation",
        "A03",
        76,
        0.72,
        "DOM/form mining found parameters commonly involved in SQL/NoSQL injection, XSS, or authorization lookups.",
        "target_intelligence",
        input_tasks,
    )

    idor_tasks = [
        _task_from_intel(
            item,
            f"Test object ownership around `{item.key}`",
            "Compare responses across available users and nearby object identifiers to detect IDOR or missing ownership checks.",
            "idor",
            90,
        )
        for item in intel
        if item.kind in {"id", "endpoint", "input", "response_field"} and _looks_like_object_reference(item)
    ]
    add_spec(
        "idor",
        "Object ownership / IDOR testing",
        "Object identifiers and account-specific endpoints should be verified across roles and users.",
        "access control",
        "A01",
        90,
        0.8,
        "Crawl intelligence found IDs, numeric path segments, or object-reference parameters that may gate tenant/user data.",
        "target_intelligence",
        idor_tasks,
    )

    admin_tasks = [
        _task_from_intel(
            item,
            "Verify admin boundary and privilege checks",
            "Attempt low-privilege and unauthenticated access to admin-looking routes without destructive actions.",
            "authz",
            86,
        )
        for item in intel
        if "/admin" in _intel_text(item).lower()
    ]
    add_spec(
        "admin_boundary",
        "Admin boundary and privilege testing",
        "Admin routes are high-value authorization boundaries even when discovered only through scripts or links.",
        "access control",
        "A01",
        86,
        0.76,
        "Crawler or JavaScript mining found admin-looking paths.",
        "target_intelligence",
        admin_tasks,
    )

    business_tasks = [
        TaskSeed(
            title=f"Exercise business logic on {page.title or _path_label(page.url)}",
            description="Probe amount, state, workflow, and role assumptions using safe boundary values and cross-user comparisons.",
            target_url=page.url,
            method="BROWSER",
            task_type="business_logic",
            priority=84,
            evidence=(page.llm_context or page.page_text or "")[:500],
            intel_id=None,
        )
        for page in pages
        if page.has_business_logic
    ]
    add_spec(
        "business_logic",
        "Business logic gate and amount tampering",
        "Pages with workflow or transaction semantics should be tested for state, amount, role, and sequence manipulation.",
        "business logic",
        "A04",
        84,
        0.7,
        "Page categorization marked one or more crawled pages as business-logic surfaces.",
        "page_analysis",
        business_tasks,
    )

    return specs


def _ensure_hypothesis(
    s: Session,
    *,
    run_id: int,
    title: str,
    description: str,
    attack_area: str,
    owasp_category: str,
    priority: int,
    confidence: float,
    rationale: str,
    created_from: str,
    related_intel_ids: list[int],
) -> tuple[PentestHypothesis, bool]:
    existing = s.exec(
        select(PentestHypothesis)
        .where(PentestHypothesis.test_run_id == run_id)
        .where(PentestHypothesis.title == title)
    ).first()
    if existing:
        return existing, False
    hypothesis = PentestHypothesis(
        test_run_id=run_id,
        title=title,
        description=description,
        attack_area=attack_area,
        owasp_category=owasp_category,
        priority=priority,
        confidence=confidence,
        rationale=rationale,
        created_from=created_from,
        related_intel_ids=json.dumps(related_intel_ids),
    )
    s.add(hypothesis)
    s.flush()
    return hypothesis, True


def _ensure_task(s: Session, run_id: int, hypothesis_id: int | None, task: TaskSeed) -> bool:
    existing = s.exec(
        select(PentestTask)
        .where(PentestTask.test_run_id == run_id)
        .where(PentestTask.title == task.title)
        .where(PentestTask.target_url == task.target_url)
        .where(PentestTask.task_type == task.task_type)
    ).first()
    if existing:
        return False
    row = PentestTask(
        test_run_id=run_id,
        hypothesis_id=hypothesis_id,
        title=task.title,
        description=task.description,
        target_url=task.target_url,
        method=task.method or "GET",
        task_type=task.task_type,
        priority=task.priority,
        evidence=task.evidence[:2000],
    )
    s.add(row)
    return True


def _task_from_intel(
    item: TargetIntelItem,
    title: str,
    description: str,
    task_type: str,
    priority: int,
) -> TaskSeed:
    url = item.url or item.value or item.key
    return TaskSeed(
        title=title,
        description=description,
        target_url=url,
        method=(item.method or "GET").upper(),
        task_type=task_type,
        priority=priority,
        evidence=_truncate(item.evidence or _intel_text(item), 800),
        intel_id=item.id,
    )


def _dedupe_tasks(tasks: list[TaskSeed]) -> list[TaskSeed]:
    seen: set[tuple[str, str, str]] = set()
    out: list[TaskSeed] = []
    for task in tasks:
        key = (task.title, task.target_url, task.task_type)
        if key in seen:
            continue
        seen.add(key)
        out.append(task)
    return sorted(out, key=lambda t: (-t.priority, t.target_url, t.title))


def _best_task_for_action(
    tasks: list[PentestTask],
    target_url: str,
    note: str,
    action_type: str,
) -> PentestTask | None:
    if not tasks:
        return None
    target_path = _url_path(target_url)
    note_l = note.lower()
    best: tuple[int, PentestTask] | None = None
    for task in tasks:
        score = int(task.priority or 0)
        task_path = _url_path(task.target_url)
        if target_url and task.target_url and (target_url == task.target_url or task.target_url in target_url):
            score += 80
        if target_path and task_path and (target_path == task_path or task_path in target_path or target_path in task_path):
            score += 60
        if task.task_type == action_type:
            score += 20
        title_words = [w for w in re.findall(r"[a-z0-9_]{4,}", task.title.lower()) if w not in {"check", "test", "probe"}]
        score += min(40, sum(8 for word in title_words[:8] if word in note_l))
        if task.status == "running":
            score += 10
        if best is None or score > best[0]:
            best = (score, task)
    if best is None or best[0] < 55:
        return None
    return best[1]


def _looks_like_public_config_endpoint(item: TargetIntelItem) -> bool:
    text = _intel_text(item).lower()
    if item.kind not in {"endpoint", "script"}:
        return False
    return any(marker in text for marker in (
        "/api/health", "/health", "/status", "/metrics", "/debug",
        "/config", "/env", "/openapi", "/swagger", "/docs",
    ))


def _looks_sensitive_name(value: str) -> bool:
    v = (value or "").lower()
    return any(marker in v for marker in (
        "secret", "password", "passwd", "pwd", "token", "jwt", "hash",
        "totp", "mfa", "role", "admin", "debug", "api_key", "apikey",
        "private", "credential",
    ))


def _looks_tokenish(key: str, value: str) -> bool:
    text = f"{key} {value}".lower()
    return any(marker in text for marker in (
        "token", "jwt", "bearer", "session", "auth", "csrf", "xsrf",
        "refresh", "access",
    ))


def _looks_attackable_input(key: str, value: str) -> bool:
    text = f"{key} {value}".lower()
    return any(marker in text for marker in (
        "search", "sort", "filter", "query", "q", "email", "username",
        "name", "description", "comment", "message", "amount", "price",
        "redirect", "url", "return", "next",
    ))


def _looks_like_object_reference(item: TargetIntelItem) -> bool:
    text = _intel_text(item).lower()
    if item.kind == "id":
        return True
    if re.search(r"/\d+(?:[/?.#]|$)", text):
        return True
    return any(marker in text for marker in (
        "id", "user_id", "account_id", "customer_id", "transaction_id",
        "invoice_id", "order_id", "tenant_id", "uuid",
    ))


def _intel_text(item: TargetIntelItem) -> str:
    return " ".join(str(part or "") for part in (
        item.kind, item.key, item.value, item.url, item.method, item.source, item.evidence,
    ))


def _url_path(url: str) -> str:
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        return parsed.path or url
    except Exception:
        return url


def _path_label(url: str) -> str:
    path = _url_path(url).rstrip("/")
    return path or url


def _truncate(value: str, limit: int) -> str:
    value = value or ""
    return value if len(value) <= limit else value[: limit - 1] + "…"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _emit_update(run_id: int, reason: str, data: dict | None = None) -> None:
    events_svc.emit(run_id, {
        "type": "task_graph_update",
        "reason": reason,
        "data": data or {},
    })
