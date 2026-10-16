"""Import external scanner reports as unverified, run-owned dynamic-test leads.

Parsing is deterministic and never opens artifact paths, URLs, or source files.
SARIF 2.1.0: https://docs.oasis-open.org/sarif/sarif/v2.1.0/os/sarif-v2.1.0-os.html
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass, field
from pathlib import PurePosixPath
from urllib.parse import unquote

from sqlmodel import Session, select

from aespa.models import ApiTestRun, ScanLead, TestRun
from aespa.services.references import ensure_lead_reference

MAX_REPORT_BYTES = 5 * 1024 * 1024
MAX_RESULTS = 5000


class ReportImportError(ValueError):
    """The supplied report cannot be imported without losing its meaning."""


@dataclass
class ReportLead:
    title: str
    description: str
    severity: str = "medium"
    category: str = ""
    location: str = ""
    evidence: str = ""
    confidence: float = 0.0
    scanner: str = "External scanner"
    rule_id: str = ""
    suggested_endpoint: str = ""
    trace: dict = field(default_factory=dict)

    @property
    def fingerprint(self) -> str:
        identity = [self.scanner.casefold(), self.rule_id, self.title, self.location]
        return (
            "external:"
            + hashlib.sha256(
                json.dumps(identity, ensure_ascii=False).encode()
            ).hexdigest()
        )


def _obj(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _text(value: object) -> str:
    text = value.strip() if isinstance(value, str) else ""
    try:
        text.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ReportImportError("The report contains invalid Unicode text.") from exc
    return text


def _array(value: object, label: str) -> list:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ReportImportError(f"{label} must be a list.")
    return value


def _severity(value: object) -> str:
    text = _text(value).lower()
    aliases = {"informational": "info", "information": "info", "moderate": "medium"}
    text = aliases.get(text, text)
    if text and text not in {"critical", "high", "medium", "low", "info"}:
        raise ReportImportError(
            f"Unknown severity: {text[:80]}. Use critical, high, medium, low, or info."
        )
    return text or "medium"


def _confidence(value: object) -> float:
    if value is None or value == "":
        return 0.0
    try:
        result = float(str(value).rstrip("%"))
        if isinstance(value, str) and value.endswith("%"):
            result /= 100
    except (TypeError, ValueError) as exc:
        raise ReportImportError(
            "Confidence must be between 0 and 1, or a percentage."
        ) from exc
    if not math.isfinite(result) or not 0 <= result <= 1:
        raise ReportImportError("Confidence must be between 0 and 1, or a percentage.")
    return result


def _message(value: object, rule: dict, component: dict) -> str:
    message = _obj(value)
    text = _text(message.get("text")) or _text(message.get("markdown"))
    if not text and message.get("id"):
        message_id = message["id"]
        if not isinstance(message_id, str):
            raise ReportImportError("SARIF message IDs must be text.")
        template = _obj(rule.get("messageStrings")).get(message_id)
        template = template or _obj(component.get("globalMessageStrings")).get(
            message_id
        )
        text = _text(_obj(template).get("text")) or _text(
            _obj(template).get("markdown")
        )
    args = _array(message.get("arguments"), "Message arguments")
    return _text(
        re.sub(
            r"\{(\d{1,9})\}",
            lambda match: (
                str(args[int(match[1])]) if int(match[1]) < len(args) else match[0]
            ),
            text,
        )
    )


def _sarif_locations(result: dict, run: dict) -> tuple[str, str, list[dict]]:
    paths, evidence, traces = [], [], []
    artifacts = _array(run.get("artifacts"), "SARIF artifacts")
    for location in _array(result.get("locations"), "SARIF locations"):
        physical = _obj(_obj(location).get("physicalLocation"))
        artifact = _obj(physical.get("artifactLocation"))
        index = artifact.get("index")
        if (
            not artifact.get("uri")
            and isinstance(index, int)
            and 0 <= index < len(artifacts)
        ):
            artifact = _obj(_obj(artifacts[index]).get("location"))
        path = unquote(_text(artifact.get("uri")))
        region = _obj(physical.get("region"))
        line = region.get("startLine")
        if path and isinstance(line, int) and line > 0:
            path += f":{line}"
            column = region.get("startColumn")
            if isinstance(column, int) and column > 0:
                path += f":{column}"
        if not path:
            logical = _array(
                _obj(location).get("logicalLocations"), "Logical locations"
            )
            path = "; ".join(
                _text(_obj(item).get("fullyQualifiedName"))
                or _text(_obj(item).get("name"))
                for item in logical
            )
        if path:
            paths.append(path)
        snippet = _text(_obj(region.get("snippet")).get("text"))
        snippet = snippet or _text(
            _obj(_obj(physical.get("contextRegion")).get("snippet")).get("text")
        )
        if snippet:
            evidence.append(snippet)
        traces.append(_obj(location))
    return "; ".join(paths), "\n\n".join(evidence), traces


def _sarif_leads(document: object) -> tuple[list[ReportLead], int]:
    if not isinstance(document, dict) or document.get("version") != "2.1.0":
        raise ReportImportError("Upload a SARIF 2.1.0 report.")
    if not isinstance(document.get("runs"), list):
        raise ReportImportError("The SARIF report must contain a runs list.")
    leads, skipped, result_count = [], 0, 0
    for run in document["runs"]:
        if not isinstance(run, dict):
            raise ReportImportError("Each SARIF run must be an object.")
        tool = _obj(run.get("tool"))
        driver = _obj(tool.get("driver"))
        if not _text(driver.get("name")):
            raise ReportImportError(
                "Each SARIF run must name its scanner in tool.driver.name."
            )
        components = [driver, *_array(tool.get("extensions"), "Tool extensions")]
        rule_cache: dict[int, tuple[list, dict]] = {}
        for result in _array(run.get("results"), "SARIF results"):
            result_count += 1
            if result_count > MAX_RESULTS:
                raise ReportImportError(
                    f"Reports may contain at most {MAX_RESULTS} results."
                )
            if not isinstance(result, dict):
                raise ReportImportError("Each SARIF result must be an object.")
            suppressions = _array(result.get("suppressions"), "SARIF suppressions")
            if (
                result.get("baselineState") == "absent"
                or (_text(result.get("kind")) or "fail") not in {"fail", "review"}
                or any(
                    _obj(s).get("status", "accepted") == "accepted"
                    for s in suppressions
                )
            ):
                skipped += 1
                continue
            descriptor = _obj(result.get("rule"))
            component_ref = _obj(descriptor.get("toolComponent"))
            component = driver
            if component_ref:
                index = component_ref.get("index")
                extensions = components[1:]
                if isinstance(index, int) and 0 <= index < len(extensions):
                    component = _obj(extensions[index])
                elif component_ref.get("name"):
                    component = next(
                        (
                            c
                            for c in components
                            if _obj(c).get("name") == component_ref["name"]
                        ),
                        {},
                    )
                else:
                    raise ReportImportError(
                        "A SARIF rule refers to an unavailable tool component."
                    )
                if not component:
                    raise ReportImportError(
                        "A SARIF rule refers to an unavailable tool component."
                    )
            if id(component) not in rule_cache:
                component_rules = _array(component.get("rules"), "Scanner rules")
                rule_cache[id(component)] = (
                    component_rules,
                    {
                        _text(_obj(rule).get("id")): _obj(rule)
                        for rule in component_rules
                    },
                )
            rules, rule_by_id = rule_cache[id(component)]
            rule_id = _text(result.get("ruleId")) or _text(descriptor.get("id"))
            index = result.get("ruleIndex", descriptor.get("index"))
            rule = (
                _obj(rules[index])
                if isinstance(index, int) and 0 <= index < len(rules)
                else {}
            )
            if rule_id and rule.get("id") != rule_id:
                rule = rule_by_id.get(rule_id, {})
            rule_id = rule_id or _text(rule.get("id"))
            message = _message(result.get("message"), rule, component)
            if not message:
                raise ReportImportError(
                    f"SARIF result {result_count} has no readable message."
                )
            title = (
                _text(_obj(rule.get("shortDescription")).get("text"))
                or message.splitlines()[0]
            )
            properties = {
                **_obj(rule.get("properties")),
                **_obj(result.get("properties")),
            }
            severity = properties.get("severity")
            if not severity:
                score = properties.get("security-severity")
                try:
                    number = float(score)
                except (TypeError, ValueError):
                    number = -1
                if 0 <= number <= 10:
                    severity = (
                        "critical"
                        if number >= 9
                        else "high"
                        if number >= 7
                        else "medium"
                        if number >= 4
                        else "low"
                        if number > 0
                        else "info"
                    )
                else:
                    level = result.get(
                        "level",
                        _obj(rule.get("defaultConfiguration")).get("level", "warning"),
                    )
                    severity = {
                        "error": "high",
                        "warning": "medium",
                        "note": "low",
                        "none": "info",
                    }.get(_text(level), "medium")
            category = _text(properties.get("category")) or _text(
                properties.get("owasp")
            )
            if not category:
                tags = _array(properties.get("tags"), "Rule tags")
                category = ", ".join(
                    tag
                    for tag in tags
                    if isinstance(tag, str) and re.search(r"owasp|cwe", tag, re.I)
                )
            location, evidence, traces = _sarif_locations(result, run)
            flows = _array(result.get("codeFlows"), "Code flows")
            if flows:
                evidence += "\n\nReported code flows:\n" + json.dumps(
                    flows, ensure_ascii=True
                )
            leads.append(
                ReportLead(
                    title=title[:500],
                    description=message,
                    severity=_severity(severity),
                    category=category[:500],
                    location=location,
                    evidence=evidence.strip(),
                    confidence=_confidence(properties.get("confidence")),
                    scanner=_text(component.get("name")) or driver["name"],
                    rule_id=rule_id,
                    trace={
                        "locations": traces,
                        "code_flows": flows,
                        "rule_id": rule_id,
                    },
                )
            )
    return leads, skipped


def _markdown_item(item: object) -> ReportLead:
    if not isinstance(item, dict) or not _text(item.get("title")):
        raise ReportImportError("Each Markdown finding must have a title.")
    return ReportLead(
        title=_text(item.get("title"))[:500],
        description=_text(item.get("description")) or _text(item.get("title")),
        severity=_severity(item.get("severity")),
        category=_text(item.get("category")),
        location=_text(item.get("location")),
        evidence=_text(item.get("evidence")),
        confidence=_confidence(item.get("confidence")),
        scanner=_text(item.get("scanner"))
        or _text(item.get("source"))
        or "Markdown report",
        rule_id=_text(item.get("rule_id")),
        suggested_endpoint=_text(item.get("suggested_endpoint")),
    )


def _markdown_leads(text: str) -> list[ReportLead]:
    embedded = re.search(r"<!--\s*aespa-sast-leads-json\s*\n(.*?)\n\s*-->", text, re.S)
    if embedded:
        try:
            items = json.loads(unquote(embedded[1].strip()))
        except (ValueError, RecursionError) as exc:
            raise ReportImportError(
                "The AESPA Markdown export contains invalid lead data."
            ) from exc
        if not isinstance(items, list) or len(items) > MAX_RESULTS:
            raise ReportImportError(
                f"The Markdown lead list must contain at most {MAX_RESULTS} items."
            )
        return [_markdown_item(item) for item in items]
    items, current, section, fence, content = [], None, "", "", []

    def save_section() -> None:
        nonlocal content
        if current is not None and section:
            current[section] = "\n".join(content).strip()
        content = []

    for line in text.splitlines():
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            if not fence:
                fence = marker[1]
            elif marker[1][0] == fence[0] and len(marker[1]) >= len(fence):
                fence = ""
            else:
                content.append(line)
            continue
        if fence:
            content.append(line)
            continue
        heading = re.match(r"^##\s+(.+?)\s*#*\s*$", line)
        if heading:
            save_section()
            if current and len(current) > 1:
                items.append(current)
            current = {"title": re.sub(r"^\d+[.)]\s+", "", heading[1])}
            section = ""
            if len(items) > MAX_RESULTS:
                raise ReportImportError(
                    f"Reports may contain at most {MAX_RESULTS} findings."
                )
            continue
        subsection = re.match(r"^#{3,4}\s+(.+?)\s*$", line)
        if subsection:
            save_section()
            section = {
                "description": "description",
                "details": "description",
                "evidence": "evidence",
                "code evidence": "evidence",
            }.get(subsection[1].lower(), "")
            continue
        metadata = re.match(r"^\s*[-*]\s+\**([\w ]+?)\**:\**\s*(.*?)\s*$", line)
        if metadata and current is not None and not section:
            key = metadata[1].strip().lower()
            key = {
                "rule id": "rule_id",
                "suggested endpoint": "suggested_endpoint",
            }.get(key, key)
            if key in {
                "severity",
                "category",
                "location",
                "confidence",
                "scanner",
                "source",
                "rule_id",
                "suggested_endpoint",
            }:
                current[key] = metadata[2].strip("`")
        elif section:
            content.append(line)
    save_section()
    if current and len(current) > 1:
        items.append(current)
    if len(items) > MAX_RESULTS:
        raise ReportImportError(f"Reports may contain at most {MAX_RESULTS} findings.")
    if not items:
        raise ReportImportError(
            "No Markdown findings found. Use a '## Finding title' heading with Severity and Location fields, or download the template."
        )
    return [_markdown_item(item) for item in items]


def parse_report(
    content: bytes, filename: str
) -> tuple[str, list[ReportLead], list[str], int]:
    if len(content) > MAX_REPORT_BYTES:
        raise ReportImportError("Reports must be 5 MiB or smaller.")
    if not content.strip():
        raise ReportImportError("The report is empty.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ReportImportError("Reports must use UTF-8 text encoding.") from exc
    suffix = PurePosixPath(filename.lower()).suffix
    if suffix in {".sarif", ".json"} or text.lstrip().startswith("{"):
        try:
            document = json.loads(text)
        except (ValueError, RecursionError) as exc:
            raise ReportImportError("The SARIF report is not valid JSON.") from exc
        report_format = "SARIF"
        leads, skipped = _sarif_leads(document)
    elif suffix in {".md", ".markdown"}:
        report_format = "Markdown"
        leads, skipped = _markdown_leads(text), 0
    else:
        raise ReportImportError(
            "Choose a SARIF (.sarif or .json) or Markdown (.md) report."
        )
    warnings = []
    missing = sum(not lead.location for lead in leads)
    if missing:
        warnings.append(
            f"{missing} lead(s) have no location; DAST may need more context."
        )
    unknown = sum(lead.confidence == 0 for lead in leads)
    if unknown:
        warnings.append(
            f"{unknown} lead(s) have no confidence score. No confidence is inferred."
        )
    if skipped:
        warnings.append(
            f"Skipped {skipped} suppressed, absent, or non-failure SARIF result(s)."
        )
    unique = {lead.fingerprint: lead for lead in leads}
    duplicates = len(leads) - len(unique)
    if duplicates:
        warnings.append(f"Skipped {duplicates} duplicate finding(s) within the report.")
    return report_format, list(unique.values()), warnings, skipped + duplicates


def import_report(
    session: Session,
    *,
    run_kind: str,
    run_id: int,
    content: bytes,
    filename: str,
    preview: bool = True,
) -> dict:
    model = ApiTestRun if run_kind == "api" else TestRun
    if session.get(model, run_id) is None:
        raise LookupError("Target run not found.")
    filename = PurePosixPath(filename.replace("\\", "/")).name[:255]
    report_format, leads, warnings, skipped = parse_report(content, filename)
    existing = set(
        session.exec(
            select(ScanLead.fingerprint).where(
                ScanLead.imported_into_run_type == run_kind,
                ScanLead.imported_into_run_id == run_id,
                ScanLead.producer_run_type == "external",
            )
        ).all()
    )
    new = [lead for lead in leads if lead.fingerprint not in existing]
    result = {
        "format": report_format,
        "filename": filename,
        "total": len(leads),
        "new_count": len(new),
        "already_imported": len(leads) - len(new),
        "skipped": skipped,
        "warnings": warnings,
        "items": [
            {
                "title": lead.title,
                "severity": lead.severity,
                "location": lead.location,
                "scanner": lead.scanner,
                "already_imported": lead.fingerprint in existing,
            }
            for lead in leads[:100]
        ],
        "preview_limit": 100,
        "imported": 0,
    }
    if preview:
        return result
    report_hash = hashlib.sha256(content).hexdigest()
    for lead in new:
        provenance = {
            "filename": filename,
            "format": report_format,
            "scanner": lead.scanner,
            "rule_id": lead.rule_id,
            "sha256": report_hash,
        }
        data = asdict(lead)
        for key in ("scanner", "rule_id", "trace"):
            data.pop(key)
        stored = ScanLead(
            **data,
            producer_run_type="external",
            producer_run_id=run_id,
            source=lead.scanner,
            fingerprint=lead.fingerprint,
            imported_into_run_type=run_kind,
            imported_into_run_id=run_id,
            status="open",
            validation_status="pending",
            reportable=True,
            source_trace_json=json.dumps(
                {**lead.trace, "external_report": provenance}, ensure_ascii=True
            ),
            provenance_json=json.dumps([provenance], ensure_ascii=False),
        )
        session.add(stored)
        session.flush()
        ensure_lead_reference(session, stored)
    session.commit()
    result["imported"] = len(new)
    return result
