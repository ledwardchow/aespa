"""Security test coverage for named browser workflows discovered during a crawl."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import (
    CrawledPage,
    ScanFinding,
    TestRun,
    TrafficEntry,
    WorkflowCoverageItem,
)
from aespa.services.crawl_workflows import list_workflow_notes

_UTC = timezone.utc
_COVERED = {"passed", "finding"}
_TERMINAL = _COVERED | {"blocked"}
_RESULTS = _TERMINAL | {"inconclusive"}

# What each workflow check asks the scanner to test. Shown in workflow_detail,
# coverage gaps, the enforce checklist, and Deep scan hypotheses.
WORKFLOW_TEST_GUIDANCE = {
    "sequence": (
        "Skip, reorder, or repeat earlier steps and check that the final step "
        "still enforces them."
    ),
    "access": (
        "Complete or read the final step as another account or without signing "
        "in, and check that the server refuses it."
    ),
    "replay": (
        "Resubmit the final request, and send a few copies at once, and check "
        "that it takes effect only once."
    ),
    "tampering": (
        "Change submitted amounts, quantities, prices, IDs, or hidden values to "
        "values the page would not allow, and check that the server rejects or "
        "recalculates them."
    ),
    "csrf": (
        "Check whether the final state-changing request is accepted without a "
        "valid anti-CSRF token or from another origin while the session cookie "
        "is sent."
    ),
    "reauth": (
        "Check whether this sensitive change requires the current password or "
        "fresh sign-in, and whether an old or downgraded session can make it."
    ),
}

# Field names that suggest values the server should calculate or limit.
_TAMPER_FIELD = re.compile(
    r"(?<![a-z])(?:qty|quantity|amount|price|subtotal|total|cost|fee|discount|"
    r"coupon|voucher|balance|points|role|plan|tier)s?(?![a-z])"
)
# Generic account changes that usually deserve a fresh sign-in.
_SENSITIVE_WORKFLOW = re.compile(
    r"\b(?:password|passphrase|e-?mail|phone|payments?|cards?|bank|billing|"
    r"address(?:es)?|transfers?|withdraw\w*|payouts?|2fa|mfa|two-factor|"
    r"recovery|api[ _-]?keys?|delete account|close account)\b",
    re.IGNORECASE,
)


def _replay_steps(page: CrawledPage) -> list[dict]:
    try:
        data = json.loads(page.replay_steps_json or "{}")
    except (TypeError, ValueError):
        return []
    steps = data.get("steps") if isinstance(data, dict) else data
    return [step for step in steps or [] if isinstance(step, dict)]


def _field_words(selector: object) -> str:
    """Split a field selector such as [name="itemPrice"] into lowercase words."""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(selector or ""))
    return re.sub(r"[^a-z0-9]+", " ", text.lower())


def _workflow_checks(note: dict, page: CrawledPage) -> list[tuple[str, str]]:
    """Choose which security checks a reached workflow needs."""
    steps = _replay_steps(page)
    inputs = [
        step for step in steps if step.get("kind") in {"fill", "select_option", "check"}
    ]
    submits_data = bool(inputs) or bool(page.has_business_logic)
    signed_in = bool(page.req_auth)
    checks = [("sequence", "A04")]
    if signed_in or page.has_object_ref:
        checks.append(("access", "A01"))
    if submits_data:
        checks.append(("replay", "A04"))
    if any(_TAMPER_FIELD.search(_field_words(step.get("selector"))) for step in inputs):
        checks.append(("tampering", "A08"))
    if signed_in and submits_data:
        checks.append(("csrf", "A01"))
    text = " ".join(
        str(value or "")
        for value in (note.get("name"), note.get("goal"), page.url, page.state_label)
    )
    if signed_in and _SENSITIVE_WORKFLOW.search(text):
        checks.append(("reauth", "A07"))
    return checks


def _root_note_id(note: dict, by_id: dict[int, dict]) -> int:
    current = note
    seen: set[int] = set()
    while isinstance(current.get("retry_of"), int):
        prior = by_id.get(current["retry_of"])
        if prior is None or current["id"] in seen:
            break
        seen.add(current["id"])
        current = prior
    return current["id"]


def _reached_page(note: dict, pages: list[CrawledPage]) -> CrawledPage | None:
    page_id = note.get("page_id")
    if isinstance(page_id, int):
        return next(
            (page for page in pages if page.id == page_id and page.in_scope), None
        )
    # Older workflow notes lack page_id. Only use the URL when it identifies one
    # interactive state, since several workflows can share the same URL.
    matches = [
        page
        for page in pages
        if page.in_scope
        and page.state_kind == "interactive"
        and page.url == note.get("url")
    ]
    if len(matches) == 1:
        return matches[0]
    if matches:
        return None
    # Some older successful notes point only to a captured API page.
    matches = [page for page in pages if page.in_scope and page.url == note.get("url")]
    return matches[0] if len(matches) == 1 else None


def seed_workflow_tests(run_id: int) -> int:
    """Add checks for reached workflows, preserving results across resume/retry."""
    with Session(get_engine()) as session:
        if session.get(TestRun, run_id) is None:
            return 0
        notes = list_workflow_notes(session, run_id)
        by_id = {note["id"]: note for note in notes}
        pages = list(
            session.exec(select(CrawledPage).where(CrawledPage.test_run_id == run_id))
        )
        existing = {
            (item.root_note_id, item.test_kind): item
            for item in session.exec(
                select(WorkflowCoverageItem).where(
                    WorkflowCoverageItem.test_run_id == run_id
                )
            )
        }
        latest: dict[int, tuple[dict, CrawledPage]] = {}
        for note in notes:
            if note.get("status") != "crawled" or note.get("destructive"):
                continue
            page = _reached_page(note, pages)
            if page is None:
                continue
            root = _root_note_id(note, by_id)
            if root not in latest or note["id"] > latest[root][0]["id"]:
                latest[root] = (note, page)

        max_traffic_id = (
            session.exec(
                select(TrafficEntry.id)
                .where(TrafficEntry.test_run_id == run_id)
                .order_by(TrafficEntry.id.desc())
            ).first()
            or 0
        )
        created = 0
        for root_id, (note, page) in latest.items():
            for test_kind, category in _workflow_checks(note, page):
                key = (root_id, test_kind)
                item = existing.get(key)
                if item is None:
                    item = WorkflowCoverageItem(
                        test_run_id=run_id,
                        root_note_id=root_id,
                        latest_note_id=note["id"],
                        reached_page_id=page.id,
                        name=str(note.get("name") or page.state_label or "Workflow")[
                            :100
                        ],
                        goal=str(note.get("goal") or "")[:220],
                        reached_page_url=page.url,
                        crawl_traffic_max_id=max_traffic_id,
                        test_kind=test_kind,
                        owasp_category=category,
                    )
                    session.add(item)
                    created += 1
                    continue
                if item.latest_note_id != note["id"]:
                    # A new replay state needs a new test. Re-seeding the same
                    # crawl or resuming a scan leaves established evidence intact.
                    if item.reached_page_id != page.id:
                        item.status = "not_started"
                        item.reason = ""
                        item.evidence_json = "{}"
                        item.finding_id = None
                        item.crawl_traffic_max_id = max_traffic_id
                    item.latest_note_id = note["id"]
                    item.reached_page_id = page.id
                    item.reached_page_url = page.url
                    item.name = str(note.get("name") or item.name)[:100]
                    item.goal = str(note.get("goal") or item.goal)[:220]
                    item.updated_at = datetime.now(_UTC)
                    session.add(item)
        session.commit()
        return created


def list_workflow_tests(run_id: int) -> dict:
    with Session(get_engine()) as session:
        rows = list(
            session.exec(
                select(WorkflowCoverageItem)
                .where(WorkflowCoverageItem.test_run_id == run_id)
                .order_by(WorkflowCoverageItem.root_note_id, WorkflowCoverageItem.id)
            )
        )
        totals = {
            status: 0
            for status in (
                *_COVERED,
                "blocked",
                "inconclusive",
                "not_started",
                "in_progress",
            )
        }
        items = []
        for row in rows:
            totals[row.status] = totals.get(row.status, 0) + 1
            try:
                evidence = json.loads(row.evidence_json or "{}")
            except (TypeError, ValueError):
                evidence = {}
            items.append(
                {
                    "id": row.id,
                    "root_note_id": row.root_note_id,
                    "latest_note_id": row.latest_note_id,
                    "reached_page_id": row.reached_page_id,
                    "reached_page_url": row.reached_page_url,
                    "name": row.name,
                    "goal": row.goal,
                    "owasp_category": row.owasp_category,
                    "test_kind": row.test_kind,
                    "test_guidance": WORKFLOW_TEST_GUIDANCE.get(row.test_kind, ""),
                    "status": row.status,
                    "reason": row.reason,
                    "evidence_summary": str(evidence.get("observed_behavior") or "")[
                        :300
                    ],
                    "expected_behavior": str(evidence.get("expected_behavior") or "")[
                        :300
                    ],
                    "attempted_sequence": evidence.get("attempted_sequence") or [],
                    "evidence_traffic_ids": evidence.get("evidence_traffic_ids") or [],
                    "finding_ids": [row.finding_id] if row.finding_id else [],
                }
            )
        return {"run_id": run_id, "items": items, "totals": totals}


def remaining_workflow_tests(run_id: int) -> list[dict]:
    return [
        item
        for item in list_workflow_tests(run_id)["items"]
        if item["status"] not in _TERMINAL
    ]


def record_workflow_test(
    run_id: int,
    item_id: int,
    *,
    status: str,
    attempted_sequence: list[str],
    expected_behavior: str,
    observed_behavior: str,
    evidence_traffic_ids: list[int],
    finding_id: int | None = None,
    blocked_reason: str | None = None,
) -> dict:
    """Record one evaluated workflow test using traffic from this scan."""
    if status not in _RESULTS:
        raise ValueError("Choose passed, finding, inconclusive, or blocked")
    sequence = [
        str(step).strip()[:240] for step in attempted_sequence if str(step).strip()
    ]
    expected = expected_behavior.strip()[:2000]
    observed = observed_behavior.strip()[:2000]
    reason = (blocked_reason or "").strip()[:1000]
    ids = list(dict.fromkeys(evidence_traffic_ids))
    if status in _COVERED and (not sequence or not expected or not observed or not ids):
        raise ValueError(
            "A covered workflow needs a test, expected and observed behavior, and traffic evidence"
        )
    if status == "blocked" and not reason:
        raise ValueError("A blocked workflow needs a specific reason")
    if status == "finding" and finding_id is None:
        raise ValueError("A finding result needs a finding ID")
    if len(ids) > 30 or len(sequence) > 20:
        raise ValueError("Too many workflow steps or traffic records")
    with Session(get_engine()) as session:
        item = session.get(WorkflowCoverageItem, item_id)
        if item is None or item.test_run_id != run_id:
            raise ValueError("Workflow test does not belong to this run")
        for traffic_id in ids:
            row = session.get(TrafficEntry, traffic_id)
            if (
                row is None
                or row.test_run_id != run_id
                or row.api_test_run_id is not None
                or row.id <= item.crawl_traffic_max_id
            ):
                raise ValueError("Workflow evidence must be traffic from this scan")
        if finding_id is not None:
            finding = session.get(ScanFinding, finding_id)
            if finding is None or finding.test_run_id != run_id:
                raise ValueError("Finding does not belong to this run")
        item.status = status
        item.reason = reason
        item.finding_id = finding_id
        item.evidence_json = json.dumps(
            {
                "attempted_sequence": sequence,
                "expected_behavior": expected,
                "observed_behavior": observed,
                "evidence_traffic_ids": ids,
            }
        )
        item.updated_at = datetime.now(_UTC)
        session.add(item)
        session.commit()
    return next(
        item for item in list_workflow_tests(run_id)["items"] if item["id"] == item_id
    )
