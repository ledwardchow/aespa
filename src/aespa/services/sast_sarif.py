"""SARIF 2.1.0 generation service for SAST scan results."""

from __future__ import annotations

import json
import re
from typing import Any

from sqlmodel import Session, select

from aespa import __version__
from aespa.models import SastRun, ScanLead

SARIF_SCHEMA_URI = "https://json.schemastore.org/sarif-2.1.0.json"
SARIF_VERSION = "2.1.0"
SRCROOT_URI_BASE = "%SRCROOT%"

_LOCATION_RE = re.compile(
    r"^(?P<path>[^:]+):(?P<line>[1-9]\d*)(?::(?P<col>[1-9]\d*))?$"
)
_HTTP_METHOD_PREFIX = (
    "GET ",
    "POST ",
    "PUT ",
    "DELETE ",
    "PATCH ",
    "HEAD ",
    "OPTIONS ",
)


class SastSarifError(ValueError):
    """Raised when a SAST run cannot be exported to SARIF."""


def parse_location(
    location_str: str | None,
    source_trace: dict[str, Any] | None = None,
    sink_trace: dict[str, Any] | None = None,
    fallback_filename: str | None = None,
) -> tuple[str | None, int | None, int | None, str | None]:
    """Parse relative path, startLine, startColumn, and endpoint/logical hint.

    Returns:
        (file_path, line, col, logical_endpoint)
    """
    raw = (location_str or "").strip()

    # If location is an HTTP route or endpoint
    if any(raw.upper().startswith(m) for m in _HTTP_METHOD_PREFIX):
        # Fall back to sink_trace or source_trace for physical location
        physical = _extract_file_from_trace(sink_trace) or _extract_file_from_trace(
            source_trace
        )
        if physical:
            return physical[0], physical[1], None, raw
        return fallback_filename, 1 if fallback_filename else None, None, raw

    if raw:
        match = _LOCATION_RE.fullmatch(raw.replace("\\", "/"))
        if match:
            path = match.group("path").strip().lstrip("/")
            line = int(match.group("line"))
            col = int(match.group("col")) if match.group("col") else None
            return path, line, col, None

        # Check if it looks like a path without line (e.g. src/utils.py)
        cleaned = raw.replace("\\", "/").lstrip("/")
        if "/" in cleaned or "." in cleaned:
            return cleaned, 1, None, None

    # Try traces
    physical = _extract_file_from_trace(sink_trace) or _extract_file_from_trace(
        source_trace
    )
    if physical:
        return physical[0], physical[1], None, raw or None

    return fallback_filename, 1 if fallback_filename else None, None, raw or None


def _extract_file_from_trace(
    trace: dict[str, Any] | None,
) -> tuple[str, int] | None:
    if not isinstance(trace, dict):
        return None
    file_val = trace.get("file") or trace.get("path")
    if isinstance(file_val, str) and file_val.strip():
        path = file_val.strip().replace("\\", "/").lstrip("/")
        line_val = trace.get("line")
        line = 1
        if isinstance(line_val, int) and line_val >= 1:
            line = line_val
        elif isinstance(line_val, str) and line_val.isdigit() and int(line_val) >= 1:
            line = int(line_val)
        return path, line
    return None


def map_severity_to_level(severity: str | None) -> str:
    """Map AESPA severity string to SARIF level (error, warning, note)."""
    s = (severity or "").lower().strip()
    if s in ("critical", "high"):
        return "error"
    if s == "medium":
        return "warning"
    return "note"


def map_severity_to_score(severity: str | None) -> str:
    """Map AESPA severity string to a CVSS-like score string for GitHub Code Scanning."""
    s = (severity or "").lower().strip()
    if s == "critical":
        return "9.0"
    if s == "high":
        return "7.5"
    if s == "medium":
        return "5.0"
    if s == "low":
        return "2.5"
    return "0.0"


def _safe_json_loads(val: str | None, default: Any) -> Any:
    if not val:
        return default
    try:
        parsed = json.loads(val)
        return parsed if isinstance(parsed, type(default)) else default
    except (ValueError, TypeError):
        return default


def _rule_id_for_category(category: str | None) -> str:
    cat = (category or "").strip()
    if not cat:
        return "AESPA/SAST-Finding"
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", cat).strip("-")
    return f"AESPA/{safe}" if safe else "AESPA/SAST-Finding"


def build_sarif_rules(
    leads: list[ScanLead],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Derive deduplicated reportingDescriptor rules and an index lookup map."""
    rules: list[dict[str, Any]] = []
    rule_index_map: dict[str, int] = {}

    for lead in leads:
        rule_id = _rule_id_for_category(lead.category)
        if rule_id in rule_index_map:
            continue

        cat_name = (
            lead.category.strip() if lead.category else "Unclassified Vulnerability"
        )
        desc = lead.description.strip() if lead.description else lead.title.strip()
        help_markdown = (
            f"### {cat_name}\n\n"
            f"{desc}\n\n"
            f"**Initial Severity:** {lead.severity.upper()}\n\n"
            "Identified by AESPA SAST static taint analysis."
        )

        rule_descriptor: dict[str, Any] = {
            "id": rule_id,
            "name": cat_name,
            "shortDescription": {
                "text": lead.title.strip() if lead.title else cat_name
            },
            "fullDescription": {"text": desc or cat_name},
            "help": {
                "text": desc or cat_name,
                "markdown": help_markdown,
            },
            "defaultConfiguration": {
                "level": map_severity_to_level(lead.severity),
            },
            "properties": {
                "tags": [
                    "security",
                    "sast",
                    *([lead.category.strip()] if lead.category else []),
                ],
                "security-severity": map_severity_to_score(lead.severity),
                "precision": "high" if lead.confidence >= 0.7 else "medium",
            },
        }

        rule_index_map[rule_id] = len(rules)
        rules.append(rule_descriptor)

    return rules, rule_index_map


def build_code_flow(
    lead: ScanLead,
    primary_file: str | None,
    primary_line: int | None,
) -> list[dict[str, Any]]:
    """Build SARIF codeFlows representing source-to-sink taint analysis steps."""
    source_trace: dict[str, Any] = _safe_json_loads(lead.source_trace_json, {})
    control_trace: list[Any] = _safe_json_loads(lead.control_trace_json, [])
    sink_trace: dict[str, Any] = _safe_json_loads(lead.sink_trace_json, {})

    thread_flow_locations: list[dict[str, Any]] = []
    order = 1

    # Step 1: Source
    source_file, source_line = _extract_file_from_trace(source_trace) or (
        primary_file,
        primary_line,
    )
    if source_file:
        source_symbol = (
            source_trace.get("symbol") or source_trace.get("input") or "entry"
        )
        thread_flow_locations.append(
            {
                "location": {
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": source_file,
                            "uriBaseId": SRCROOT_URI_BASE,
                        },
                        "region": {"startLine": source_line or 1, "startColumn": 1},
                    },
                    "message": {
                        "text": f"Source input ({source_symbol}) enters data flow"
                    },
                },
                "executionOrder": order,
                "importance": "essential",
            }
        )
        order += 1

    # Intermediate steps: Controls / sanitizers
    for control in control_trace:
        ctrl_text = str(control).strip()
        if not ctrl_text:
            continue
        thread_flow_locations.append(
            {
                "location": {"message": {"text": f"Control encountered: {ctrl_text}"}},
                "executionOrder": order,
                "importance": "important",
            }
        )
        order += 1

    # Final step: Sink
    sink_file, sink_line = _extract_file_from_trace(sink_trace) or (
        primary_file,
        primary_line,
    )
    if sink_file:
        sink_op = (
            sink_trace.get("operation")
            or sink_trace.get("symbol")
            or lead.title
            or "sink"
        )
        thread_flow_locations.append(
            {
                "location": {
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": sink_file,
                            "uriBaseId": SRCROOT_URI_BASE,
                        },
                        "region": {"startLine": sink_line or 1, "startColumn": 1},
                    },
                    "message": {"text": f"Sink reached: {sink_op}"},
                },
                "executionOrder": order,
                "importance": "essential",
            }
        )

    if not thread_flow_locations:
        return []

    return [
        {
            "message": {"text": "Taint flow trace from source to sink"},
            "threadFlows": [{"locations": thread_flow_locations}],
        }
    ]


def build_result_markdown(
    lead: ScanLead,
    counterevidence: list[Any],
    proof_gaps: list[Any],
    attack_path: dict[str, Any],
) -> str:
    """Format rich domain pentest details into GitHub/SARIF-viewer compatible Markdown."""
    lines: list[str] = [
        f"### {lead.title or 'SAST Finding'}",
        "",
        f"- **Reference:** `{lead.reference or '—'}`",
        f"- **Severity:** `{lead.severity.upper()}`",
        f"- **Confidence:** `{round((lead.confidence or 0.0) * 100)}%`",
        f"- **Validation Status:** `{lead.validation_status}`",
        f"- **Reportable:** `{'Yes' if lead.reportable else 'No'}`",
    ]
    if lead.origin_reference:
        lines.append(f"- **Origin Lead:** `{lead.origin_reference}`")
    if lead.suggested_endpoint:
        lines.append(f"- **Suggested Endpoint:** `{lead.suggested_endpoint}`")
    lines.append("")

    if lead.description:
        lines.extend(["#### Description", lead.description.strip(), ""])

    if lead.validation_reasoning:
        lines.extend(
            ["#### Validator Reasoning", lead.validation_reasoning.strip(), ""]
        )

    if counterevidence:
        lines.append("#### Counterevidence")
        for item in counterevidence:
            lines.append(f"- {item}")
        lines.append("")

    if proof_gaps:
        lines.append("#### Unresolved Proof Gaps")
        for gap in proof_gaps:
            lines.append(f"- {gap}")
        lines.append("")

    dynamic_test = attack_path.get("dynamic_test")
    if dynamic_test:
        lines.extend(["#### Dynamic Test Guidance", str(dynamic_test).strip(), ""])

    if lead.evidence:
        lines.extend(["#### Code Evidence", "```", lead.evidence.strip(), "```", ""])

    return "\n".join(lines).strip()


def build_result_properties(
    lead: ScanLead,
    counterevidence: list[Any],
    proof_gaps: list[Any],
    attack_path: dict[str, Any],
) -> dict[str, Any]:
    """Serialize all AESPA domain metadata into a SARIF property bag."""
    return {
        "leadReference": lead.reference,
        "originReference": lead.origin_reference,
        "category": lead.category,
        "severity": lead.severity,
        "confidence": lead.confidence,
        "validationStatus": lead.validation_status,
        "validationReasoning": lead.validation_reasoning,
        "reportable": lead.reportable,
        "status": lead.status,
        "suggestedEndpoint": lead.suggested_endpoint,
        "counterevidence": counterevidence,
        "proofGaps": proof_gaps,
        "attackPath": attack_path,
        "fingerprint": lead.fingerprint,
    }


def generate_sast_sarif(
    session: Session, run_id: int, reportable_only: bool = False
) -> dict[str, Any]:
    """Generate a complete OASIS SARIF 2.1.0 document for a SAST run."""
    run = session.get(SastRun, run_id)
    if run is None:
        raise SastSarifError(f"SAST run id={run_id} does not exist")

    leads = session.exec(
        select(ScanLead)
        .where(ScanLead.producer_run_type == "sast")
        .where(ScanLead.producer_run_id == run_id)
        .where(ScanLead.imported_into_run_id == None)  # noqa: E711
        .order_by(ScanLead.id)
    ).all()

    if reportable_only:
        leads = [lead for lead in leads if lead.reportable]

    # Order leads: high/critical first, then by confidence descending
    sev_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    sorted_leads = sorted(
        leads,
        key=lambda lead: (
            sev_rank.get(lead.severity.lower(), 99),
            -(lead.confidence or 0.0),
        ),
    )

    rules, rule_index_map = build_sarif_rules(sorted_leads)

    results: list[dict[str, Any]] = []
    for lead in sorted_leads:
        rule_id = _rule_id_for_category(lead.category)
        rule_index = rule_index_map.get(rule_id, 0)
        level = map_severity_to_level(lead.severity)
        rank_val = round(float(lead.confidence or 0.0) * 100, 1)

        source_trace = _safe_json_loads(lead.source_trace_json, {})
        sink_trace = _safe_json_loads(lead.sink_trace_json, {})
        counterevidence = _safe_json_loads(lead.counterevidence_json, [])
        proof_gaps = _safe_json_loads(lead.proof_gaps_json, [])
        attack_path = _safe_json_loads(lead.attack_path_json, {})

        file_path, line, col, logical_endpoint = parse_location(
            lead.location,
            source_trace=source_trace,
            sink_trace=sink_trace,
            fallback_filename=run.source_filename,
        )

        locations: list[dict[str, Any]] = []
        if file_path:
            region: dict[str, Any] = {"startLine": line or 1}
            if col:
                region["startColumn"] = col
            if lead.evidence:
                snippet_text = lead.evidence.strip()
                if len(snippet_text) <= 500:
                    region["snippet"] = {"text": snippet_text}

            location_obj: dict[str, Any] = {
                "physicalLocation": {
                    "artifactLocation": {
                        "uri": file_path,
                        "uriBaseId": SRCROOT_URI_BASE,
                    },
                    "region": region,
                }
            }
            if logical_endpoint:
                location_obj["logicalLocations"] = [
                    {"name": logical_endpoint, "kind": "endpoint"}
                ]
            locations.append(location_obj)
        elif logical_endpoint:
            locations.append(
                {"logicalLocations": [{"name": logical_endpoint, "kind": "endpoint"}]}
            )

        code_flows = build_code_flow(lead, file_path, line)
        properties = build_result_properties(
            lead, counterevidence, proof_gaps, attack_path
        )
        markdown_message = build_result_markdown(
            lead, counterevidence, proof_gaps, attack_path
        )

        result_obj: dict[str, Any] = {
            "ruleId": rule_id,
            "ruleIndex": rule_index,
            "level": level,
            "rank": rank_val,
            "message": {
                "text": lead.description or lead.title or "Security finding",
                "markdown": markdown_message,
            },
            "locations": locations,
            "properties": properties,
        }

        if lead.fingerprint:
            result_obj["partialFingerprints"] = {
                "primaryLocationHash": lead.fingerprint
            }

        if code_flows:
            result_obj["codeFlows"] = code_flows

        # Standard suppressions for dismissed candidates
        if not lead.reportable or lead.validation_status == "dismissed":
            result_obj["suppressions"] = [
                {
                    "kind": "external",
                    "status": "accepted",
                    "justification": (
                        lead.validation_reasoning
                        or "Dismissed during adversarial SAST validation"
                    ),
                }
            ]

        results.append(result_obj)

    invocations: list[dict[str, Any]] = [
        {
            "executionSuccessful": run.status == "completed",
            "startTimeUtc": (run.started_at.isoformat() if run.started_at else None),
            "endTimeUtc": (run.completed_at.isoformat() if run.completed_at else None),
        }
    ]

    version_str = __version__ if __version__ != "unknown" else "0.6.0"

    return {
        "$schema": SARIF_SCHEMA_URI,
        "version": SARIF_VERSION,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "AESPA",
                        "semanticVersion": version_str,
                        "informationUri": "https://github.com/ledwardchow/aespa",
                        "rules": rules,
                    }
                },
                "invocations": invocations,
                "results": results,
            }
        ],
    }
