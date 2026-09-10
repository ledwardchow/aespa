"""Framework-neutral semantic state for SAST runs.

The semantic SAST design intentionally keeps its first storage format in the
run's phase/report JSON.  This lets upgraded installations read old runs while
the richer graph tables are introduced independently.  The functions in this
module are deterministic, bounded, and side-effect free unless explicitly
named ``persist_*`` by the caller.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from aespa.services.component_facts import extract_component_facts

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

    if facts is None:
        try:
            facts = extract_component_facts(root)
        except Exception:
            facts = []
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
        },
    }


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
    for candidate in candidates:
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
    return output, {"input": len(candidates), "unique": len(output), "merged": merged}


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
