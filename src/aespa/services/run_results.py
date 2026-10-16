"""Read-only results for integrations: findings, summaries, and SARIF.

The output format here is a public contract for the API extension. Keep field
names stable; add fields rather than renaming or removing them.
"""

from __future__ import annotations

import json
from datetime import timezone
from typing import Any

from sqlmodel import Session, select

from aespa.models import SastRun, ScanFinding, ScanLead, TestRun
from aespa.services.run_progress import SEVERITIES

SEVERITY_RANK = {severity: index for index, severity in enumerate(SEVERITIES)}
DISMISSED_WEB = {"false_positive"}
DISMISSED_SAST = {"dismissed"}


def _iso(value) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _json(value: str | None, default: Any) -> Any:
    try:
        return json.loads(value) if value else default
    except (TypeError, ValueError):
        return default


def _web_finding(row: ScanFinding) -> dict[str, Any]:
    return {
        "id": row.id,
        "reference": row.public_reference,
        "title": row.title,
        "severity": (row.severity or "").lower(),
        "category": row.owasp_category,
        "description": row.description,
        "impact": row.impact,
        "recommendation": row.recommendation,
        "cvss_score": row.cvss_score,
        "cvss_vector": row.cvss_vector,
        "status": row.validation_status,
        "dismissed": row.validation_status in DISMISSED_WEB,
        "source": row.finding_source,
        "location": {"url": row.affected_url or None},
        "evidence": {
            "request": row.request_evidence or None,
            "response": row.response_evidence or None,
            "summary": row.evidence or None,
        },
        "proof_of_concept": row.poc_command or None,
        "created_at": _iso(row.created_at),
    }


def _sast_finding(row: SastRun | None, lead: ScanLead) -> dict[str, Any]:
    from aespa.services.sast_sarif import parse_location

    path, line, column, endpoint = parse_location(
        lead.location,
        _json(lead.source_trace_json, {}),
        _json(lead.sink_trace_json, {}),
    )
    return {
        "id": lead.id,
        "reference": lead.public_reference,
        "title": lead.title,
        "severity": (lead.severity or "").lower(),
        "category": lead.category,
        "description": lead.description,
        "confidence": lead.confidence,
        "classification": lead.classification,
        "status": lead.status,
        "validation_status": lead.validation_status,
        "dismissed": lead.status in DISMISSED_SAST
        or lead.validation_status in DISMISSED_SAST,
        "reportable": lead.reportable,
        "location": {
            "raw": lead.location or None,
            "file": path,
            "line": line,
            "column": column,
            "endpoint": endpoint or lead.suggested_endpoint or None,
        },
        "evidence": {"summary": lead.evidence or None},
        "created_at": _iso(lead.created_at),
    }


def list_findings(
    session: Session,
    run_id: int,
    *,
    severities: set[str] | None = None,
    include_dismissed: bool = False,
) -> list[dict[str, Any]] | None:
    """Return findings for a web or SAST run, most severe first.

    Returns ``None`` when the run does not exist.
    """
    if session.get(TestRun, run_id) is not None:
        rows = session.exec(
            select(ScanFinding)
            .where(ScanFinding.test_run_id == run_id)
            .order_by(ScanFinding.id)
        ).all()
        items = [_web_finding(row) for row in rows]
    elif (sast := session.get(SastRun, run_id)) is not None:
        leads = session.exec(
            select(ScanLead)
            .where(ScanLead.producer_run_type == "sast")
            .where(ScanLead.producer_run_id == run_id)
            .where(ScanLead.imported_into_run_id == None)  # noqa: E711
            .where(ScanLead.reportable == True)  # noqa: E712
            .order_by(ScanLead.id)
        ).all()
        items = [_sast_finding(sast, lead) for lead in leads]
    else:
        return None
    if not include_dismissed:
        items = [item for item in items if not item["dismissed"]]
    if severities:
        items = [item for item in items if item["severity"] in severities]
    items.sort(key=lambda item: (SEVERITY_RANK.get(item["severity"], 99), item["id"]))
    return items


def summarize(
    findings: list[dict[str, Any]], *, fail_on: str | None = None
) -> dict[str, Any]:
    """Count findings and, with ``fail_on``, decide whether a CI gate passes."""
    by_severity = {severity: 0 for severity in SEVERITIES}
    by_category: dict[str, int] = {}
    for item in findings:
        if item["severity"] in by_severity:
            by_severity[item["severity"]] += 1
        category = item.get("category") or "unknown"
        by_category[category] = by_category.get(category, 0) + 1
    result: dict[str, Any] = {
        "total": len(findings),
        "by_severity": by_severity,
        "by_category": dict(sorted(by_category.items())),
    }
    if fail_on is not None:
        limit = SEVERITY_RANK[fail_on]
        blocking = sum(
            count
            for severity, count in by_severity.items()
            if SEVERITY_RANK[severity] <= limit
        )
        result["gate"] = {
            "fail_on": fail_on,
            "blocking_findings": blocking,
            "passed": blocking == 0,
        }
    return result


def sast_sarif(session: Session, run_id: int) -> dict[str, Any] | None:
    from aespa.services import sast_sarif as sarif

    if session.get(SastRun, run_id) is None:
        return None
    return sarif.generate_sast_sarif(session, run_id, reportable_only=True)


def web_sarif(
    session: Session, run_id: int, *, include_false_positives: bool = False
) -> dict[str, Any] | None:
    from aespa.services import web_sarif as sarif

    if session.get(TestRun, run_id) is None:
        return None
    return sarif.generate_web_sarif(
        session, run_id, include_false_positives=include_false_positives
    )
