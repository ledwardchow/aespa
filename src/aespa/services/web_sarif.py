"""SARIF 2.1.0 generation service for web (DAST) scan results.

Read-only: builds a document from a ``TestRun``'s ``ScanFinding`` rows and
never writes to the database.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from sqlmodel import Session, select

from aespa import __version__
from aespa.models import ScanFinding, Site, TestRun
from aespa.services.llm import OWASP_WEB_LABELS
from aespa.services.sast_sarif import (
    SARIF_SCHEMA_URI,
    SARIF_VERSION,
    map_severity_to_level,
    map_severity_to_score,
)

FALSE_POSITIVE = "false_positive"
_SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
_SNIPPET_LIMIT = 500


class WebSarifError(ValueError):
    """Raised when a web run cannot be exported to SARIF."""


def _rule_id_for_category(category: str | None) -> str:
    cat = (category or "").strip().upper()
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", cat).strip("-")
    return f"AESPA/WEB-{safe}" if safe else "AESPA/WEB-Finding"


def _category_name(category: str | None) -> str:
    cat = (category or "").strip().upper()
    if not cat:
        return "Unclassified web finding"
    label = OWASP_WEB_LABELS.get(cat)
    return f"{cat} {label}" if label else cat


def _security_score(finding: ScanFinding) -> float:
    if finding.cvss_score and finding.cvss_score > 0:
        return float(finding.cvss_score)
    return float(map_severity_to_score(finding.severity))


def _merged_instances(finding: ScanFinding) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(finding.merged_instances or "[]")
    except (TypeError, ValueError):
        return []
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, dict)]


def _url_location(url: str, snippet: str | None = None) -> dict[str, Any]:
    physical: dict[str, Any] = {"artifactLocation": {"uri": url}}
    text = (snippet or "").strip()
    if text and len(text) <= _SNIPPET_LIMIT:
        physical["region"] = {"startLine": 1, "snippet": {"text": text}}
    return {
        "physicalLocation": physical,
        "logicalLocations": [{"name": url, "kind": "url"}],
    }


def build_sarif_rules(
    findings: list[ScanFinding],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """One rule per OWASP category, scored by its most severe finding."""
    grouped: dict[str, list[ScanFinding]] = {}
    for finding in findings:
        grouped.setdefault(_rule_id_for_category(finding.owasp_category), []).append(
            finding
        )

    rules: list[dict[str, Any]] = []
    rule_index_map: dict[str, int] = {}
    for rule_id, members in grouped.items():
        worst = min(
            members,
            key=lambda f: _SEVERITY_RANK.get((f.severity or "").lower(), 99),
        )
        category = (worst.owasp_category or "").strip().upper()
        name = _category_name(category)
        text = f"AESPA found {name} issues while testing the running web application."
        tags = ["security", "dast", "web"]
        if category:
            tags.append(f"OWASP-{category}")
        rule_index_map[rule_id] = len(rules)
        rules.append(
            {
                "id": rule_id,
                "name": name,
                "shortDescription": {"text": name},
                "fullDescription": {"text": text},
                "help": {
                    "text": text,
                    "markdown": f"### {name}\n\n{text}",
                },
                "defaultConfiguration": {
                    "level": map_severity_to_level(worst.severity),
                },
                "properties": {
                    "tags": tags,
                    "security-severity": f"{max(_security_score(f) for f in members):.1f}",
                    "precision": "high",
                },
            }
        )
    return rules, rule_index_map


def build_result_markdown(finding: ScanFinding) -> str:
    """Format a web finding as Markdown for SARIF viewers."""
    lines: list[str] = [
        f"### {finding.title or 'Web finding'}",
        "",
        f"- **Reference:** `{finding.public_reference or '—'}`",
        f"- **Severity:** `{(finding.severity or '').upper()}`",
        f"- **OWASP category:** `{_category_name(finding.owasp_category)}`",
        f"- **Affected URL:** `{finding.affected_url or '—'}`",
        f"- **Validation status:** `{finding.validation_status}`",
    ]
    if finding.cvss_score:
        vector = f" ({finding.cvss_vector})" if finding.cvss_vector else ""
        lines.append(f"- **CVSS:** `{finding.cvss_score}{vector}`")
    lines.append("")
    for heading, value in (
        ("Description", finding.description),
        ("Impact", finding.impact),
        ("Recommendation", finding.recommendation),
        ("Validator note", finding.validation_note),
    ):
        if value and value.strip():
            lines.extend([f"#### {heading}", value.strip(), ""])
    if finding.poc_command:
        lines.extend(["#### Proof of concept", "```", finding.poc_command.strip()])
        lines.extend(["```", ""])
    for heading, value in (
        ("Evidence", finding.evidence),
        ("Request", finding.request_evidence),
        ("Response", finding.response_evidence),
    ):
        if value and value.strip():
            lines.extend([f"#### {heading}", "```", value.strip(), "```", ""])
    return "\n".join(lines).strip()


def build_result_properties(finding: ScanFinding) -> dict[str, Any]:
    """Serialize AESPA finding metadata into a SARIF property bag."""
    return {
        "findingId": finding.id,
        "reference": finding.public_reference,
        "category": finding.owasp_category,
        "categoryName": _category_name(finding.owasp_category),
        "severity": (finding.severity or "").lower(),
        "cvssScore": finding.cvss_score,
        "cvssVector": finding.cvss_vector or None,
        "affectedUrl": finding.affected_url or None,
        "validationStatus": finding.validation_status,
        "source": finding.finding_source,
        "proofOfConcept": finding.poc_command or None,
    }


def _fingerprint(finding: ScanFinding) -> str:
    key = "\n".join(
        [
            (finding.owasp_category or "").upper(),
            finding.affected_url or "",
            (finding.title or "").strip().lower(),
        ]
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _invocation(run: TestRun) -> dict[str, Any]:
    invocation: dict[str, Any] = {"executionSuccessful": run.status == "complete"}
    if run.started_at:
        invocation["startTimeUtc"] = run.started_at.isoformat()
    if run.completed_at:
        invocation["endTimeUtc"] = run.completed_at.isoformat()
    return invocation


def generate_web_sarif(
    session: Session, run_id: int, include_false_positives: bool = False
) -> dict[str, Any]:
    """Generate an OASIS SARIF 2.1.0 document for a web run."""
    run = session.get(TestRun, run_id)
    if run is None:
        raise WebSarifError(f"Web run id={run_id} does not exist")

    findings = list(
        session.exec(
            select(ScanFinding)
            .where(ScanFinding.test_run_id == run_id)
            .order_by(ScanFinding.id)
        ).all()
    )
    if not include_false_positives:
        findings = [f for f in findings if f.validation_status != FALSE_POSITIVE]
    findings.sort(
        key=lambda f: (
            _SEVERITY_RANK.get((f.severity or "").lower(), 99),
            -(f.cvss_score or 0.0),
            f.id or 0,
        )
    )

    rules, rule_index_map = build_sarif_rules(findings)

    results: list[dict[str, Any]] = []
    for finding in findings:
        rule_id = _rule_id_for_category(finding.owasp_category)
        locations: list[dict[str, Any]] = []
        if finding.affected_url:
            locations.append(_url_location(finding.affected_url, finding.evidence))
        related: list[dict[str, Any]] = []
        seen = {finding.affected_url}
        for instance in _merged_instances(finding):
            url = instance.get("affected_url")
            if not isinstance(url, str) or not url or url in seen:
                continue
            seen.add(url)
            related.append(
                {
                    "id": len(related) + 1,
                    **_url_location(url),
                    "message": {"text": "Same issue also found here"},
                }
            )

        result: dict[str, Any] = {
            "ruleId": rule_id,
            "ruleIndex": rule_index_map[rule_id],
            "level": map_severity_to_level(finding.severity),
            "message": {
                "text": finding.title or finding.description or "Security finding",
                "markdown": build_result_markdown(finding),
            },
            "locations": locations,
            "partialFingerprints": {"primaryLocationHash": _fingerprint(finding)},
            "properties": build_result_properties(finding),
        }
        if related:
            result["relatedLocations"] = related
        if finding.validation_status == FALSE_POSITIVE:
            result["suppressions"] = [
                {
                    "kind": "external",
                    "status": "accepted",
                    "justification": finding.validation_note
                    or "Marked as a false positive in AESPA",
                }
            ]
        results.append(result)

    site = session.get(Site, run.site_id) if run.site_id else None
    run_obj: dict[str, Any] = {
        "tool": {
            "driver": {
                "name": "AESPA",
                "semanticVersion": __version__ if __version__ != "unknown" else "0.6.0",
                "informationUri": "https://github.com/ledwardchow/aespa",
                "rules": rules,
            }
        },
        "invocations": [_invocation(run)],
        "results": results,
        "properties": {"runKind": "web", "runId": run.id},
    }
    if site is not None and site.base_url:
        run_obj["properties"]["target"] = site.base_url
    return {"$schema": SARIF_SCHEMA_URI, "version": SARIF_VERSION, "runs": [run_obj]}
