"""Framework-neutral semantic state for SAST runs.

The semantic model is persisted both as normalized relational state and as a
bounded phase/report projection. This lets upgraded installations read old
runs while new scans retain queryable facts, edges, scenarios, obligations,
relationships, and telemetry. Functions in this module are deterministic and
side-effect free unless explicitly named ``persist_*`` by the caller.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from aespa.services.component_facts import extract_component_facts
from aespa.services.sast_parsers import extract_parser_facts

_MAX_NODES = 2_000
_MAX_SCENARIOS = 300
_MAX_OBLIGATIONS = 600
_TOKEN_RE = re.compile(r"[a-z0-9]{3,}")


def fingerprint(*parts: object) -> str:
    """Return a stable, privacy-preserving identity for a semantic fact."""

    value = "|".join(str(part or "").strip().casefold() for part in parts)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _location(value: object) -> str:
    return str(value or "")[:240]


def _tokens(value: object) -> set[str]:
    return set(_TOKEN_RE.findall(str(value or "").casefold()))


def _fact_kind(fact_type: str) -> str:
    return {
        "route": "operation",
        "ui_route": "operation",
        "http_call": "operation",
        "rpc_client": "operation",
        "rpc_server": "operation",
        "auth_boundary": "control",
        "datastore": "store",
        "queue": "operation",
        "framework": "dependency",
        "dependency": "dependency",
        "callable": "operation",
        "sensitive_operation": "sink",
    }.get(fact_type, "unknown")


def _node_from_fact(fact: dict[str, Any]) -> dict[str, Any]:
    fact_type = str(fact.get("fact_type") or "unknown")
    detail = fact.get("detail")
    if not isinstance(detail, dict):
        detail = {}
    path = fact.get("path")
    method = fact.get("method")
    name = fact.get("name")
    location = _location(fact.get("evidence_location"))
    node_id = fingerprint(
        fact_type,
        method,
        path,
        fact.get("host"),
        name,
    )
    return {
        "id": node_id,
        "kind": _fact_kind(fact_type),
        "type": fact_type,
        "name": str(name or "")[:240],
        "method": str(method or "").upper() or None,
        "path": str(path or "")[:500] or None,
        "component_key": str(fact.get("source") or location.split(":", 1)[0])[:240],
        "confidence": 0.85 if fact.get("provenance") in {"parser", "manifest"} else 0.7,
        "provenance": str(fact.get("provenance") or "pattern"),
        "evidence": [location] if location else [],
        "details": detail,
        "fingerprint": node_id,
    }


def build_repository_model(
    root: Path, *, facts: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Build a bounded normalized repository model from existing fact adapters."""

    parser_result = extract_parser_facts(root)
    if facts is None:
        try:
            facts = extract_component_facts(root)
        except Exception:
            facts = []
    facts = list(facts) + parser_result.facts
    nodes_by_id: dict[str, dict[str, Any]] = {}
    for fact in facts[: _MAX_NODES * 2]:
        if not isinstance(fact, dict):
            continue
        node = _node_from_fact(fact)
        previous = nodes_by_id.get(node["id"])
        if previous is None:
            nodes_by_id[node["id"]] = node
        else:
            previous["evidence"] = sorted(
                set(previous.get("evidence", [])) | set(node.get("evidence", []))
            )[:8]
            previous["confidence"] = max(previous["confidence"], node["confidence"])

    nodes = list(nodes_by_id.values())[:_MAX_NODES]
    warnings: list[dict[str, Any]] = []
    production_files = 0
    try:
        production_files = sum(
            1
            for path in root.rglob("*")
            if path.is_file()
            and ".git" not in path.parts
            and "node_modules" not in path.parts
        )
    except OSError:
        pass
    operations = [node for node in nodes if node["kind"] == "operation"]
    stores = [node for node in nodes if node["kind"] == "store"]
    controls = [node for node in nodes if node["kind"] == "control"]
    dependencies = [node for node in nodes if node["kind"] == "dependency"]
    if production_files and not operations:
        warnings.append(
            {
                "key": "no_reachable_operations",
                "severity": "high",
                "message": "Production source was found but no externally reachable operation was mapped.",
                "status": "unresolved",
            }
        )
    if stores and not operations:
        warnings.append(
            {
                "key": "store_without_operation",
                "severity": "medium",
                "message": "A datastore dependency was mapped without a reachable operation.",
                "status": "unresolved",
            }
        )
    if dependencies and not controls:
        warnings.append(
            {
                "key": "dependency_without_controls",
                "severity": "low",
                "message": "Dependencies were detected but no authentication or authorization boundary was mapped.",
                "status": "unresolved",
            }
        )
    for adapter_warning in parser_result.warnings[:100]:
        warnings.append(
            {
                "key": fingerprint("parser_warning", adapter_warning),
                "severity": "medium",
                "message": f"Parser coverage warning for {adapter_warning.get('path') or 'repository'}: {adapter_warning.get('reason')}",
                "status": "unresolved",
                "provenance": "parser",
            }
        )
    return {
        "model_version": 1,
        "source_root": "immutable-sast-snapshot",
        "nodes": nodes,
        "edges": _derive_edges(nodes),
        "warnings": warnings,
        "stats": {
            "nodes": len(nodes),
            "operations": len(operations),
            "stores": len(stores),
            "controls": len(controls),
            "dependencies": len(dependencies),
            "production_files": production_files,
            "truncated": len(nodes_by_id) > _MAX_NODES,
            "parser_files_seen": parser_result.files_seen,
            "parser_files_parsed": parser_result.files_parsed,
        },
    }


def _version_tuple(value: object) -> tuple[int, ...] | None:
    match = re.search(r"\d+(?:\.\d+){0,5}", str(value or ""))
    return tuple(map(int, match.group().split("."))) if match else None


def _affected(version: object, specifier: str) -> bool:
    parsed = _version_tuple(version)
    bound = _version_tuple(specifier)
    if parsed is None or bound is None:
        return False
    width = max(len(parsed), len(bound))
    left = parsed + (0,) * (width - len(parsed))
    right = bound + (0,) * (width - len(bound))
    if specifier.startswith("<="):
        return left <= right
    if specifier.startswith("<"):
        return left < right
    if specifier.startswith(">="):
        return left >= right
    if specifier.startswith(">"):
        return left > right
    return left == right


def deterministic_dependency_analysis(
    model: dict[str, Any], advisory_db: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Inventory resolved dependency versions without asking an LLM to guess advisories."""

    dependencies = []
    for node in model.get("nodes", []):
        if node.get("kind") != "dependency":
            continue
        details = node.get("details") if isinstance(node.get("details"), dict) else {}
        dependencies.append(
            {
                "name": node.get("name"),
                "version": details.get("version") or "unresolved",
                "scope": details.get("scope") or "runtime_or_unknown",
                "evidence": node.get("evidence", []),
                "confidence": node.get("confidence", 0.5),
            }
        )
    if advisory_db is None:
        advisory_path = Path(__file__).with_name("data") / "offline_advisories.json"
        try:
            advisory_db = json.loads(advisory_path.read_text("utf-8"))
        except (OSError, ValueError):
            advisory_db = {"updated_at": None, "advisories": []}
    matches = []
    by_name = {
        str(item["name"]).casefold(): item for item in dependencies if item.get("name")
    }
    for advisory in advisory_db.get("advisories", [])[:100_000]:
        if not isinstance(advisory, dict):
            continue
        dependency = by_name.get(str(advisory.get("package") or "").casefold())
        if dependency and _affected(
            dependency.get("version"), str(advisory.get("affected") or "")
        ):
            matches.append(
                {
                    "advisory_id": advisory.get("id"),
                    "package": dependency["name"],
                    "version": dependency["version"],
                    "affected": advisory.get("affected"),
                    "severity": advisory.get("severity", "unknown"),
                    "evidence": dependency["evidence"],
                    "confidence": dependency["confidence"],
                }
            )
    updated_at = advisory_db.get("updated_at")
    advisory_count = len(advisory_db.get("advisories", []))
    if not updated_at:
        database_status = "not_configured"
    elif not advisory_count:
        database_status = "empty"
    else:
        database_status = "available"
    warnings = []
    if dependencies and database_status == "not_configured":
        warnings.append(
            "No offline advisory database is configured; versions were inventoried but not vulnerability-matched."
        )
    elif dependencies and database_status == "empty":
        warnings.append(
            "The bundled offline advisory snapshot contains no records; versions were inventoried but not vulnerability-matched."
        )
    return {
        "analyzer_version": 1,
        "advisory_database_updated_at": updated_at,
        "advisory_database_status": database_status,
        "advisory_count": advisory_count,
        "dependencies": dependencies,
        "matches": matches,
        "warnings": warnings,
    }


def deterministic_security_candidates(root: Path) -> list[dict[str, Any]]:
    """Emit high-signal, source-anchored candidates for independent validation."""

    rules = (
        (
            re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
            "Hard-coded private key material",
            "A02",
            "high",
            "credential material is stored in source",
            "exploitable",
        ),
        (
            re.compile(r"\bverify\s*=\s*False\b|rejectUnauthorized\s*:\s*false", re.I),
            "TLS certificate verification disabled",
            "A02",
            "medium",
            "transport authentication is explicitly disabled",
            "conditional",
        ),
        (
            re.compile(r"\bDEBUG\s*=\s*True\b|debug\s*:\s*true", re.I),
            "Debug mode enabled by source configuration",
            "A05",
            "medium",
            "debug behavior is enabled in configuration",
            "conditional",
        ),
        (
            re.compile(r"\b(?:pickle|yaml)\.loads?\s*\("),
            "Potential unsafe deserialization",
            "A08",
            "high",
            "a general-purpose deserializer is invoked",
            "conditional",
        ),
    )
    candidates: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*"))[:4_000]:
        if not path.is_file() or ".git" in path.parts or "node_modules" in path.parts:
            continue
        try:
            if path.stat().st_size > 2 * 1024 * 1024:
                continue
            lines = path.read_text("utf-8", errors="replace").splitlines()
        except OSError:
            continue
        relative = path.relative_to(root).as_posix()
        for line_no, line in enumerate(lines, 1):
            for pattern, title, category, severity, root_cause, classification in rules:
                if not pattern.search(line):
                    continue
                location = f"{relative}:{line_no}"
                candidates.append(
                    {
                        "title": title,
                        "category": category,
                        "severity": severity,
                        "classification": classification,
                        "location": location,
                        "description": f"Deterministic analysis found that {root_cause}. Reachability and effective controls require independent validation.",
                        "evidence": f"High-signal construct at {location}; literal values are redacted.",
                        "source_trace": {"path": relative, "line": line_no},
                        "sink_trace": {"path": relative, "line": line_no},
                        "controls": [],
                        "proof_gaps": [
                            "Confirm production reachability and compensating controls."
                        ],
                        "root_causes": [root_cause],
                        "discovery_strategy": "deterministic",
                        "confidence": 0.8,
                        "validation_status": "pending",
                        "validation_reasoning": "",
                        "counterevidence": [],
                        "attack_path": {},
                        "reportable": False,
                        "provenance": ["deterministic"],
                        "locations": [location],
                    }
                )
                if len(candidates) >= 500:
                    return candidates
    return candidates


def dependency_match_candidates(analysis: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = []
    for match in analysis.get("matches", []):
        location = str((match.get("evidence") or ["dependency manifest"])[0])
        candidates.append(
            {
                "title": f"{match.get('package')} {match.get('version')} matches {match.get('advisory_id')}",
                "category": "vulnerable_dependency",
                "severity": str(match.get("severity") or "medium").casefold(),
                "classification": "conditional",
                "location": location,
                "description": f"The resolved dependency version matches offline advisory {match.get('advisory_id')}. Deployment and reachability require independent validation.",
                "evidence": f"Manifest evidence: {location}; offline advisory range: {match.get('affected')}",
                "source_trace": {"path": location.split(":", 1)[0]},
                "sink_trace": {},
                "controls": [],
                "proof_gaps": [
                    "Confirm the affected component is included in the deployed artifact and the vulnerable feature is reachable."
                ],
                "root_causes": [
                    "deployed dependency version falls in an affected advisory range"
                ],
                "discovery_strategy": "deterministic_dependency",
                "confidence": float(match.get("confidence") or 0.7),
                "validation_status": "pending",
                "validation_reasoning": "",
                "counterevidence": [],
                "attack_path": {},
                "reportable": False,
                "provenance": ["offline_advisory_database"],
                "locations": [location],
            }
        )
    return candidates


def persist_semantic_state(
    sast_run_id: int,
    model: dict[str, Any],
    threat_model: dict[str, Any],
    planning: dict[str, Any],
) -> dict[str, int]:
    """Project checkpoint JSON into relational, exportable semantic tables."""

    from sqlmodel import Session, delete, select

    from aespa.db import get_engine
    from aespa.models import (
        SastCoverageObligation,
        SastSurfaceEdge,
        SastSurfaceItem,
        SastThreatModel,
        SastThreatScenario,
    )

    now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    with Session(get_engine()) as session:
        session.exec(
            delete(SastSurfaceEdge).where(SastSurfaceEdge.sast_run_id == sast_run_id)
        )
        existing = list(
            session.exec(
                select(SastSurfaceItem).where(
                    SastSurfaceItem.sast_run_id == sast_run_id
                )
            )
        )
        by_fingerprint = {row.fingerprint: row for row in existing}
        for node in model.get("nodes", []):
            row = by_fingerprint.get(node.get("fingerprint"))
            if row is None:
                row = SastSurfaceItem(
                    sast_run_id=sast_run_id,
                    kind=str(node.get("kind") or "unknown"),
                    category=str(node.get("type") or ""),
                    name=str(node.get("name") or ""),
                    path=str(node.get("component_key") or ""),
                    line=None,
                    symbol=str((node.get("details") or {}).get("symbol") or ""),
                    details_json=json.dumps(node.get("details") or {}),
                    provenance=str(node.get("provenance") or "deterministic"),
                    fingerprint=str(node.get("fingerprint")),
                )
            row.confidence = float(node.get("confidence") or 0)
            row.review_status = "source_backed"
            row.component_key = str(node.get("component_key") or "")
            session.add(row)
            session.flush()
            by_fingerprint[row.fingerprint] = row
        for edge in model.get("edges", []):
            source = by_fingerprint.get(edge.get("source"))
            target = by_fingerprint.get(edge.get("target"))
            if source is None or target is None:
                continue
            session.add(
                SastSurfaceEdge(
                    sast_run_id=sast_run_id,
                    source_surface_id=source.id,
                    target_surface_id=target.id,
                    edge_kind=str(edge.get("kind") or "related"),
                    confidence=float(edge.get("confidence") or 0),
                    provenance=str(edge.get("provenance") or "deterministic"),
                    evidence_json=json.dumps(edge.get("evidence") or []),
                    fingerprint=str(
                        edge.get("id")
                        or fingerprint(source.id, target.id, edge.get("kind"))
                    ),
                )
            )
        threat_row = session.exec(
            select(SastThreatModel).where(SastThreatModel.sast_run_id == sast_run_id)
        ).first()
        if threat_row is None:
            threat_row = SastThreatModel(sast_run_id=sast_run_id)
        threat_row.summary = str(threat_model.get("summary") or "")
        threat_row.assets_json = json.dumps(threat_model.get("assets") or [])
        threat_row.trust_boundaries_json = json.dumps(
            threat_model.get("trust_boundaries") or []
        )
        threat_row.attacker_capabilities_json = json.dumps(
            threat_model.get("attacker_capabilities") or []
        )
        threat_row.security_objectives_json = json.dumps(
            threat_model.get("security_objectives") or []
        )
        threat_row.assumptions_json = json.dumps(threat_model.get("assumptions") or [])
        threat_row.open_questions_json = json.dumps(
            threat_model.get("open_questions") or []
        )
        threat_row.model_version = int(threat_model.get("model_version") or 1)
        threat_row.updated_at = now
        session.add(threat_row)
        existing_scenarios = {
            row.scenario_key: row
            for row in session.exec(
                select(SastThreatScenario).where(
                    SastThreatScenario.sast_run_id == sast_run_id
                )
            )
        }
        scenario_ids: dict[str, int] = {}
        for scenario in threat_model.get("scenarios", []):
            scenario_key = str(scenario.get("scenario_key"))
            row = existing_scenarios.get(scenario_key) or SastThreatScenario(
                sast_run_id=sast_run_id, scenario_key=scenario_key
            )
            for attr, value in {
                "title": str(scenario.get("title") or ""),
                "actor": str(scenario.get("actor") or ""),
                "controlled_input_or_state_json": json.dumps(
                    scenario.get("controlled_input_or_state") or []
                ),
                "entry_surface_ids_json": json.dumps(
                    scenario.get("entry_surface_ids") or []
                ),
                "boundary_surface_ids_json": json.dumps(
                    scenario.get("boundary_surface_ids") or []
                ),
                "asset_surface_ids_json": json.dumps(
                    scenario.get("asset_surface_ids") or []
                ),
                "expected_control_surface_ids_json": json.dumps(
                    scenario.get("expected_control_surface_ids") or []
                ),
                "sensitive_operation_surface_ids_json": json.dumps(
                    scenario.get("sensitive_operation_surface_ids") or []
                ),
                "security_objective": str(scenario.get("security_objective") or ""),
                "capability_gain": str(scenario.get("capability_gain") or ""),
                "impact": str(scenario.get("impact") or ""),
                "prerequisites_json": json.dumps(scenario.get("prerequisites") or []),
                "evidence_json": json.dumps(scenario.get("evidence") or []),
                "priority": str(scenario.get("priority") or "medium"),
                "confidence": float(scenario.get("confidence") or 0),
                "status": str(scenario.get("status") or "planned"),
                "updated_at": now,
            }.items():
                setattr(row, attr, value)
            session.add(row)
            session.flush()
            scenario_ids[row.scenario_key] = int(row.id)
        existing_obligations = {
            row.obligation_key: row
            for row in session.exec(
                select(SastCoverageObligation).where(
                    SastCoverageObligation.sast_run_id == sast_run_id
                )
            )
        }
        for obligation in planning.get("obligations", []):
            obligation_key = str(obligation.get("obligation_key"))
            row = existing_obligations.get(obligation_key) or SastCoverageObligation(
                sast_run_id=sast_run_id,
                obligation_key=obligation_key,
                obligation_type=str(obligation.get("obligation_type") or "unknown"),
            )
            for attr, value in {
                "obligation_type": str(obligation.get("obligation_type") or "unknown"),
                "title": str(obligation.get("title") or ""),
                "security_question": str(obligation.get("security_question") or ""),
                "priority": str(obligation.get("priority") or "medium"),
                "source_scenario_id": scenario_ids.get(
                    str(obligation.get("source_scenario_key") or "")
                ),
                "primary_surface_ids_json": json.dumps(
                    obligation.get("primary_surface_ids") or []
                ),
                "related_surface_ids_json": json.dumps(
                    obligation.get("related_surface_ids") or []
                ),
                "required_evidence_json": json.dumps(
                    obligation.get("required_evidence") or []
                ),
                "status": str(obligation.get("status") or "pending"),
                "disposition": str(obligation.get("disposition") or ""),
                "reasoning": str(obligation.get("reasoning") or ""),
                "evidence_json": json.dumps(obligation.get("evidence") or []),
                "controls_json": json.dumps(obligation.get("controls") or []),
                "open_questions_json": json.dumps(
                    obligation.get("open_questions") or []
                ),
                "updated_at": now,
            }.items():
                setattr(row, attr, value)
            session.add(row)
        session.commit()
        return {
            "nodes": len(by_fingerprint),
            "edges": len(model.get("edges", [])),
            "scenarios": len(scenario_ids),
            "obligations": len(planning.get("obligations", [])),
        }


def persist_scan_telemetry(
    sast_run_id: int,
    phase_state: dict[str, Any],
    planning: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Persist auditable phase counters from durable scanner state."""

    from datetime import datetime

    from sqlmodel import Session, delete, select

    from aespa.db import get_engine
    from aespa.models import SastDiscoveryTelemetry, SastEvidenceReceipt

    rows: list[dict[str, Any]] = []
    with Session(get_engine()) as session:
        session.exec(
            delete(SastDiscoveryTelemetry).where(
                SastDiscoveryTelemetry.sast_run_id == sast_run_id
            )
        )
        receipts = list(
            session.exec(
                select(SastEvidenceReceipt).where(
                    SastEvidenceReceipt.sast_run_id == sast_run_id
                )
            )
        )
        for phase, state in phase_state.items():
            if not isinstance(state, dict):
                continue
            elapsed_ms = 0
            try:
                if state.get("started_at") and state.get("completed_at"):
                    elapsed_ms = int(
                        (
                            datetime.fromisoformat(state["completed_at"])
                            - datetime.fromisoformat(state["started_at"])
                        ).total_seconds()
                        * 1000
                    )
            except (TypeError, ValueError):
                pass
            phase_receipts = [receipt for receipt in receipts if receipt.phase == phase]
            data = state.get("data") if isinstance(state.get("data"), dict) else {}
            facts_value = data.get("nodes") or data.get("facts_created") or 0
            facts_created = (
                len(facts_value)
                if isinstance(facts_value, (list, dict))
                else int(facts_value)
            )
            row_data = {
                "phase": phase,
                "strategy": str(data.get("strategy") or ""),
                "elapsed_ms": elapsed_ms,
                "files_read": len(
                    {receipt.path for receipt in phase_receipts if receipt.path}
                ),
                "unique_spans_read": len(
                    {
                        (receipt.path, receipt.start_line, receipt.end_line)
                        for receipt in phase_receipts
                        if receipt.path
                    }
                ),
                "facts_created": facts_created,
                "obligations_created": len(planning.get("obligations", []))
                if phase == "planning"
                else 0,
                "obligations_resolved": sum(
                    item.get("status")
                    not in {"pending", "in_review", "blocked", "unreviewed"}
                    for item in planning.get("obligations", [])
                )
                if phase in {"discovery", "closure"}
                else 0,
                "candidates_emitted": len(candidates) if phase == "discovery" else 0,
                "candidates_merged": int(data.get("merged") or 0),
                "candidates_split": int(data.get("split") or 0),
                "candidates_confirmed": sum(
                    item.get("validation_status") == "confirmed" for item in candidates
                )
                if phase == "validation"
                else 0,
                "candidates_dismissed": sum(
                    item.get("validation_status") == "dismissed" for item in candidates
                )
                if phase == "validation"
                else 0,
                "adjacent_concerns": sum(
                    len(item.get("adjacent_concerns", [])) for item in candidates
                )
                if phase == "closure"
                else 0,
                "duplicate_validations_avoided": int(data.get("merged") or 0)
                if phase == "reconciliation"
                else 0,
                "caps_json": json.dumps(
                    [
                        warning
                        for warning in data.get("warnings", [])
                        if "cap" in str(warning).casefold()
                    ]
                ),
            }
            session.add(SastDiscoveryTelemetry(sast_run_id=sast_run_id, **row_data))
            rows.append(row_data)
        session.commit()
    return rows


def _derive_edges(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Create conservative relationships without pretending to have a call graph."""

    edges: list[dict[str, Any]] = []
    by_file: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in nodes:
        by_file[node.get("component_key") or ""].append(node)
    for members in by_file.values():
        for source in members:
            for target in members:
                if source["id"] == target["id"] or source["kind"] == target["kind"]:
                    continue
                edge_kind = "controls" if target["kind"] == "control" else "related"
                edges.append(
                    {
                        "id": fingerprint(source["id"], target["id"], edge_kind),
                        "source": source["id"],
                        "target": target["id"],
                        "kind": edge_kind,
                        "confidence": 0.45,
                        "provenance": "same_source_file",
                        "evidence": sorted(
                            set(source.get("evidence", []))
                            | set(target.get("evidence", []))
                        )[:4],
                    }
                )
                if len(edges) >= _MAX_NODES * 2:
                    return edges
    return edges


def build_threat_model(
    model: dict[str, Any], *, user_context: str = ""
) -> dict[str, Any]:
    """Derive source-backed threat scenarios; this does not assert findings."""

    nodes = model.get("nodes") if isinstance(model.get("nodes"), list) else []
    operations = [node for node in nodes if node.get("kind") == "operation"]
    stores = [node for node in nodes if node.get("kind") == "store"]
    controls = [node for node in nodes if node.get("kind") == "control"]
    scenarios: list[dict[str, Any]] = []
    for operation in operations[:_MAX_SCENARIOS]:
        path = operation.get("path") or operation.get("name") or "operation"
        actor = "anonymous or authenticated caller"
        security_objective = "preserve authorization and input/output integrity"
        if controls:
            actor = "caller subject to mapped authentication and authorization controls"
        if stores:
            security_objective = (
                "prevent unauthorized access or mutation of stored assets"
            )
        scenario_key = fingerprint("operation", operation["id"], security_objective)
        scenarios.append(
            {
                "scenario_key": scenario_key,
                "title": f"Protect {path}",
                "actor": actor,
                "controlled_input_or_state": [operation["id"]],
                "boundary_surface_ids": [node["id"] for node in controls[:8]],
                "asset_surface_ids": [node["id"] for node in stores[:8]],
                "expected_control_surface_ids": [node["id"] for node in controls[:8]],
                "sensitive_operation_surface_ids": [operation["id"]],
                "security_objective": security_objective,
                "capability_gain": "unauthorized read, mutation, or external side effect",
                "impact": "loss of confidentiality, integrity, or availability depending on the operation",
                "prerequisites": [
                    "reachable operation",
                    "attacker-controlled request or message",
                ],
                "evidence": operation.get("evidence", [])[:4],
                "priority": "high" if stores else "medium",
                "confidence": operation.get("confidence", 0.5),
                "status": "planned",
            }
        )
    if not scenarios and model.get("warnings"):
        for warning in model["warnings"][:20]:
            scenarios.append(
                {
                    "scenario_key": fingerprint("warning", warning.get("key")),
                    "title": warning.get("message", "Resolve repository-model warning"),
                    "actor": "external caller",
                    "controlled_input_or_state": [],
                    "boundary_surface_ids": [],
                    "asset_surface_ids": [],
                    "expected_control_surface_ids": [],
                    "sensitive_operation_surface_ids": [],
                    "security_objective": "resolve repository-model uncertainty",
                    "capability_gain": "unknown",
                    "impact": "coverage may be incomplete",
                    "prerequisites": [],
                    "evidence": [],
                    "priority": warning.get("severity", "medium"),
                    "confidence": 0.4,
                    "status": "unreviewed",
                }
            )
    return {
        "model_version": 1,
        "summary": f"{len(scenarios)} source-backed threat scenario(s) derived from the repository model.",
        "actors": sorted({scenario["actor"] for scenario in scenarios}),
        "assets": [node for node in stores[:40]],
        "assumptions": [user_context[:500]] if user_context.strip() else [],
        "open_questions": [warning["message"] for warning in model.get("warnings", [])],
        "scenarios": scenarios[:_MAX_SCENARIOS],
    }


def plan_semantic_obligations(
    model: dict[str, Any], threat_model: dict[str, Any]
) -> dict[str, Any]:
    """Convert threat scenarios and model warnings into auditable obligations."""

    obligations: list[dict[str, Any]] = []
    for scenario in threat_model.get("scenarios", [])[:_MAX_OBLIGATIONS]:
        obligations.append(
            {
                "obligation_key": fingerprint("scenario", scenario.get("scenario_key")),
                "obligation_type": "threat_scenario",
                "title": scenario.get("title", "Review threat scenario"),
                "security_question": f"Is it possible to achieve {scenario.get('capability_gain', 'an unauthorized capability')} on this operation?",
                "priority": scenario.get("priority", "medium"),
                "source_scenario_key": scenario.get("scenario_key"),
                "primary_surface_ids": scenario.get(
                    "sensitive_operation_surface_ids", []
                ),
                "related_surface_ids": scenario.get("asset_surface_ids", []),
                "required_evidence": scenario.get("evidence", []),
                "status": "pending",
                "disposition": "",
                "reasoning": "",
                "evidence": [],
                "controls": scenario.get("expected_control_surface_ids", []),
                "open_questions": scenario.get("prerequisites", []),
            }
        )
    for warning in model.get("warnings", [])[:100]:
        obligations.append(
            {
                "obligation_key": fingerprint("warning", warning.get("key")),
                "obligation_type": "model_completeness",
                "title": warning.get("message", "Resolve model warning"),
                "security_question": warning.get(
                    "message", "Is repository coverage complete?"
                ),
                "priority": warning.get("severity", "medium"),
                "source_scenario_key": None,
                "primary_surface_ids": [],
                "related_surface_ids": [],
                "required_evidence": [],
                "status": "pending",
                "disposition": "",
                "reasoning": "",
                "evidence": [],
                "controls": [],
                "open_questions": [warning.get("key", "")],
            }
        )
    return {
        "model_version": 1,
        "strategies": [
            "independent_baseline",
            "threat_directed",
            "deterministic",
            "sink_first",
            "coverage_reconciliation",
        ],
        "obligations": obligations[:_MAX_OBLIGATIONS],
        "workers": _packetize_obligations(obligations),
        "summary": {
            "total": len(obligations),
            "high_priority": sum(
                item.get("priority") == "high" for item in obligations
            ),
            "model_warnings": len(model.get("warnings", [])),
        },
    }


def _packetize_obligations(
    obligations: list[dict[str, Any]], size: int = 20
) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    for offset in range(0, len(obligations), size):
        group = obligations[offset : offset + size]
        packets.append(
            {
                "worker_key": f"semantic:{offset // size + 1}",
                "obligation_keys": [item["obligation_key"] for item in group],
                "focus": sorted({item["obligation_type"] for item in group}),
            }
        )
    return packets


def obligation_payload(
    planning: dict[str, Any], obligation_keys: set[str] | list[str]
) -> dict[str, Any]:
    """Return the bounded semantic obligations assigned to one worker."""

    keys = set(obligation_keys)
    obligations = [
        item
        for item in planning.get("obligations", [])
        if item.get("obligation_key") in keys
    ]
    return {
        "strategy": "threat_directed",
        "obligations": obligations,
        "instructions": (
            "Resolve each item with record_semantic_disposition. A candidate "
            "must also be recorded with write_lead and independently validated."
        ),
    }


def record_obligation_disposition(
    planning: dict[str, Any],
    obligation_key: str,
    *,
    status: str,
    reasoning: str,
    evidence: list[Any] | None = None,
    controls: list[Any] | None = None,
) -> tuple[bool, str]:
    """Apply an evidence-backed terminal or blocked semantic disposition."""

    allowed = {"assessed_safe", "candidate", "not_applicable", "blocked"}
    if status not in allowed:
        return False, f"status must be one of {', '.join(sorted(allowed))}"
    obligation = next(
        (
            item
            for item in planning.get("obligations", [])
            if item.get("obligation_key") == obligation_key
        ),
        None,
    )
    if obligation is None:
        return False, "semantic obligation was not found"
    if not reasoning.strip():
        return False, "reasoning is required"
    obligation.update(
        {
            "status": status,
            "disposition": status,
            "reasoning": reasoning[:4000],
            "evidence": list(evidence or [])[:20],
            "controls": list(controls or [])[:20],
        }
    )
    return True, f"Semantic obligation {obligation_key} recorded as {status}."


def reconcile_candidates(
    candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Merge repeated hypotheses while retaining all worker provenance/evidence."""

    clusters: dict[str, dict[str, Any]] = {}
    merged = 0
    expanded: list[dict[str, Any]] = []
    split_count = 0
    for candidate in candidates:
        roots = candidate.get("root_causes")
        if (
            isinstance(roots, list)
            and len([root for root in roots if str(root).strip()]) > 1
        ):
            for root in roots:
                if not str(root).strip():
                    continue
                part = dict(candidate)
                part["description"] = (
                    f"{candidate.get('description', '')}\n\nDistinct root cause: {root}".strip()
                )
                part["root_causes"] = [root]
                part["split_from_candidate_id"] = candidate.get("candidate_id")
                expanded.append(part)
            split_count += len(roots) - 1
        else:
            expanded.append(candidate)
    for candidate in expanded:
        if not isinstance(candidate, dict):
            continue
        trace = candidate.get("source_trace") or {}
        sink = candidate.get("sink_trace") or {}
        key = fingerprint(
            candidate.get("category"),
            trace.get("path") or candidate.get("location"),
            sink.get("path") or candidate.get("location"),
            " ".join(sorted(_tokens(candidate.get("description")))),
        )
        current = clusters.get(key)
        if current is None:
            current = dict(candidate)
            current["reconciliation_key"] = key
            current["provenance"] = list(candidate.get("provenance") or [])
            current["locations"] = (
                [candidate.get("location")] if candidate.get("location") else []
            )
            clusters[key] = current
            continue
        merged += 1
        current["provenance"] = list(
            dict.fromkeys(
                current.get("provenance", [])
                + list(candidate.get("provenance") or [])
                + [candidate.get("candidate_id")]
            )
        )
        current["locations"] = list(
            dict.fromkeys(
                current.get("locations", [])
                + ([candidate.get("location")] if candidate.get("location") else [])
            )
        )[:20]
        current["evidence"] = "\n\n".join(
            dict.fromkeys(
                filter(None, [current.get("evidence"), candidate.get("evidence")])
            )
        )[:12000]
        current["proof_gaps"] = list(
            dict.fromkeys(
                list(current.get("proof_gaps") or [])
                + list(candidate.get("proof_gaps") or [])
            )
        )[:20]
        current["confidence"] = max(
            current.get("confidence") or 0, candidate.get("confidence") or 0
        )
    output = list(clusters.values())
    for index, candidate in enumerate(output):
        candidate["candidate_id"] = index
        candidate["merged_candidate_ids"] = candidate.get("provenance", [])
    stats = {
        "input": len(candidates),
        "unique": len(output),
        "merged": merged,
    }
    if split_count:
        stats["split"] = split_count
    return output, stats


def closure_assurance(
    model: dict[str, Any],
    threat_model: dict[str, Any],
    planning: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute semantic completion without treating file reads as coverage."""

    reportable = [candidate for candidate in candidates if candidate.get("reportable")]
    adjacent = [
        concern
        for candidate in candidates
        for concern in candidate.get("adjacent_concerns", [])
        if isinstance(concern, dict) and concern.get("status") != "resolved"
    ]
    unresolved = [
        item
        for item in planning.get("obligations", [])
        if item.get("status") in {"pending", "in_review", "blocked", "unreviewed"}
    ]
    warnings = [
        warning
        for warning in model.get("warnings", [])
        if warning.get("status") not in {"resolved", "accepted_low_risk"}
    ]
    reasons: list[str] = []
    if unresolved:
        reasons.append(f"{len(unresolved)} semantic obligation(s) remain unresolved.")
    if warnings:
        reasons.append(
            f"{len(warnings)} repository-model completeness warning(s) remain unresolved."
        )
    if any(
        candidate.get("validation_status") in {"pending", "inconclusive"}
        for candidate in candidates
    ):
        reasons.append(
            "Not every candidate received a conclusive independent validation result."
        )
    if adjacent:
        reasons.append(f"{len(adjacent)} adjacent concern(s) require closure review.")
    return {
        "status": "full" if not reasons else "partial",
        "reasons": reasons,
        "obligations_total": len(planning.get("obligations", [])),
        "obligations_unresolved": len(unresolved),
        "warnings_unresolved": len(warnings),
        "reportable_candidates": len(reportable),
        "adjacent_concerns": len(adjacent),
        "coverage_basis": "semantic_obligations_and_threat_scenarios",
    }


def json_size(value: Any) -> int:
    """Useful for callers enforcing bounded phase checkpoints."""

    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


def _json_object(raw: str) -> dict[str, Any] | None:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I | re.S)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        value = json.loads(text[start : end + 1])
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


async def reconcile_repository_model_with_llm(
    llm_svc: Any, llm_config: Any, model: dict[str, Any], system_prompt: str
) -> dict[str, Any]:
    """Resolve completeness warnings with a bounded, non-finding LLM pass."""

    if not model.get("warnings"):
        return model
    prompt = (
        "Return JSON only with keys nodes, edges, resolved_warning_keys, open_warnings. "
        "Only add facts supported by an evidence value already present in the model. "
        "Do not report vulnerabilities. Model:\n"
        + json.dumps(model, ensure_ascii=False)[:120_000]
    )
    raw = await llm_svc.plain_completion(
        llm_config, prompt, system_prompt=system_prompt
    )
    proposal = _json_object(raw)
    if proposal is None:
        model.setdefault("reconciliation", {})["status"] = "invalid_response"
        return model
    known_evidence = {
        str(anchor)
        for node in model.get("nodes", [])
        for anchor in node.get("evidence", [])
    }
    known_ids = {node.get("id") for node in model.get("nodes", [])}
    accepted = 0
    for node in proposal.get("nodes", [])[:200]:
        if not isinstance(node, dict) or not (
            set(map(str, node.get("evidence", []))) & known_evidence
        ):
            continue
        node = dict(node)
        node["id"] = node["fingerprint"] = fingerprint(
            "llm_reconciliation",
            node.get("kind"),
            node.get("name"),
            node.get("evidence"),
        )
        node["provenance"] = "llm_reconciliation"
        node["confidence"] = min(0.75, float(node.get("confidence") or 0.5))
        model["nodes"].append(node)
        known_ids.add(node["id"])
        accepted += 1
    for edge in proposal.get("edges", [])[:400]:
        if (
            isinstance(edge, dict)
            and edge.get("source") in known_ids
            and edge.get("target") in known_ids
        ):
            edge = dict(edge)
            edge["id"] = fingerprint(
                edge.get("source"), edge.get("target"), edge.get("kind")
            )
            edge["provenance"] = "llm_reconciliation"
            model["edges"].append(edge)
    resolved = set(map(str, proposal.get("resolved_warning_keys", [])))
    for warning in model.get("warnings", []):
        if str(warning.get("key")) in resolved:
            warning["status"] = "resolved"
    model["reconciliation"] = {
        "status": "complete",
        "facts_accepted": accepted,
        "open_warnings": proposal.get("open_warnings", [])[:100],
    }
    return model


async def enrich_threat_model_with_llm(
    llm_svc: Any,
    llm_config: Any,
    model: dict[str, Any],
    threat_model: dict[str, Any],
    system_prompt: str,
) -> dict[str, Any]:
    """Run a dedicated threat analyst and accept only source-anchored scenarios."""

    prompt = (
        "Return JSON only with keys summary, trust_boundaries, attacker_capabilities, security_objectives, assumptions, open_questions, scenarios. "
        "Each scenario must use existing surface IDs and is a security question, not a finding.\nRepository model:\n"
        + json.dumps(model, ensure_ascii=False)[:100_000]
    )
    raw = await llm_svc.plain_completion(
        llm_config, prompt, system_prompt=system_prompt
    )
    proposal = _json_object(raw)
    if proposal is None:
        threat_model["llm_status"] = "invalid_response"
        return threat_model
    known_ids = {node.get("id") for node in model.get("nodes", [])}
    accepted = []
    for scenario in proposal.get("scenarios", [])[:_MAX_SCENARIOS]:
        if not isinstance(scenario, dict):
            continue
        referenced = set()
        for key in (
            "controlled_input_or_state",
            "entry_surface_ids",
            "boundary_surface_ids",
            "asset_surface_ids",
            "expected_control_surface_ids",
            "sensitive_operation_surface_ids",
        ):
            referenced.update(
                scenario.get(key, []) if isinstance(scenario.get(key), list) else []
            )
        if referenced and not referenced <= known_ids:
            continue
        scenario = dict(scenario)
        scenario["scenario_key"] = fingerprint(
            "llm_threat", scenario.get("title"), sorted(referenced)
        )
        scenario.setdefault("status", "planned")
        scenario.setdefault("priority", "medium")
        scenario["confidence"] = min(0.8, float(scenario.get("confidence") or 0.5))
        accepted.append(scenario)
    existing = {
        scenario.get("scenario_key") for scenario in threat_model.get("scenarios", [])
    }
    threat_model["scenarios"].extend(
        s for s in accepted if s.get("scenario_key") not in existing
    )
    for key in (
        "trust_boundaries",
        "attacker_capabilities",
        "security_objectives",
        "assumptions",
        "open_questions",
    ):
        values = proposal.get(key)
        if isinstance(values, list):
            threat_model[key] = list(
                dict.fromkeys(
                    [str(value)[:1000] for value in threat_model.get(key, []) + values]
                )
            )[:100]
    threat_model["llm_status"] = "complete"
    threat_model["llm_scenarios_accepted"] = len(accepted)
    return threat_model
