"""Senior Security Mentor adviser for stalled Test Lead scans."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from sqlmodel import Session

from aespa.db import get_engine
from aespa.models import ApiTestRun, CodeExecutionConfig, TestRun
from aespa.services import events as events_svc
from aespa.services import llm as llm_svc
from aespa.services.execution_monitor import StrategyVector
from aespa.services.prompts.mentor import MENTOR_DEBUG_SYSTEM_PROMPT
from aespa.services.settings import get_llm_config_for_role

log = logging.getLogger("aespa.mentor")


@dataclass
class MentorAdvice:
    diagnosis: str
    suggested_vectors: list[StrategyVector] = field(default_factory=list)
    tactical_advice: str = ""
    failure_class: str = "unknown"
    recovery_kind: str = "pivot"
    raw_response: str = ""

    def format_xml_block(self) -> str:
        def vector_line(vector: StrategyVector) -> str:
            constraints = []
            for label, values in (
                ("tools", vector.tool_names),
                ("routes", vector.route_patterns),
                ("categories", vector.owasp_categories),
                ("classes", vector.test_classes),
                ("parameters", vector.parameter_names),
            ):
                if values:
                    constraints.append(f"{label}={','.join(values)}")
            suffix = f" ({'; '.join(constraints)})" if constraints else ""
            return f"- {vector.id}: {vector.title}{suffix}"

        vectors = (
            "\n".join(vector_line(vector) for vector in self.suggested_vectors)
            or "- No enforceable vector was produced; choose a clearly different untried action."
        )
        return (
            "<mentor_analysis>\n"
            f"FAILURE CLASS: {self.failure_class}\n"
            f"DIAGNOSIS:\n{self.diagnosis}\n\n"
            f"RECOVERY KIND: {self.recovery_kind}\n\n"
            f"STRATEGY SHIFT CONTRACT — Required Pivot Vectors:\n{vectors}\n\n"
            f"TACTICAL ADVICE:\n{self.tactical_advice}\n"
            "</mentor_analysis>"
        )


def _json_object(text: str) -> dict[str, Any] | None:
    candidate = text.strip()
    fenced = re.search(
        r"```(?:json)?\s*(\{.*?\})\s*```", candidate, re.DOTALL | re.IGNORECASE
    )
    if fenced:
        candidate = fenced.group(1)
    else:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start >= 0 and end > start:
            candidate = candidate[start : end + 1]
    try:
        value = json.loads(candidate)
    except (json.JSONDecodeError, TypeError):
        return None
    return value if isinstance(value, dict) else None


_SENSITIVE_KEYS = (
    "authorization",
    "cookie",
    "password",
    "secret",
    "token",
    "api-key",
    "apikey",
)
_FAILURE_CLASSES = {
    "browser_obstruction",
    "stale_element",
    "selector_mismatch",
    "authentication",
    "unchanged_response",
    "tool_limit",
    "target_blocker",
    "unknown",
}
_RECOVERY_KINDS = {
    "inspect_browser",
    "recover_browser",
    "reauthenticate",
    "switch_http",
    "execute_python",
    "pivot",
}


def _redact_and_bound(value: Any, *, key: str = "", depth: int = 0) -> Any:
    """Retain failure evidence without copying credentials or unbounded bodies."""
    if any(marker in key.casefold() for marker in _SENSITIVE_KEYS):
        return "[redacted]"
    if depth >= 5:
        return "[truncated]"
    if isinstance(value, dict):
        return {
            str(item_key)[:120]: _redact_and_bound(
                item_value, key=str(item_key), depth=depth + 1
            )
            for item_key, item_value in list(value.items())[:50]
        }
    if isinstance(value, list):
        return [
            _redact_and_bound(item, key=key, depth=depth + 1)
            for item in value[:30]
        ]
    if isinstance(value, str):
        text = re.sub(
            r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b",
            "[redacted-jwt]",
            value,
        )
        text = re.sub(
            r"(?i)(bearer\s+)[A-Za-z0-9._~+/-]+", r"\1[redacted]", text
        )
        return text[:4000]
    return value


def _recent_incident_history(history_snippet: list[dict]) -> list[dict[str, Any]]:
    recent = []
    for item in history_snippet[-8:]:
        recent.append(
            {
                "step": item.get("step"),
                "tool": item.get("tool") or item.get("method"),
                "url": item.get("url") or item.get("target"),
                "status": item.get("response_status") or item.get("status"),
                "note": item.get("note") or item.get("desc"),
                "request": _redact_and_bound(
                    {
                        "headers": item.get("request_headers") or {},
                        "body": item.get("request_body"),
                    }
                ),
                "result": _redact_and_bound(
                    {
                        "headers": item.get("response_headers") or {},
                        "body": item.get("response_body") or item.get("result"),
                    }
                ),
                "owasp_category": item.get("owasp_category"),
                "test_class": item.get("test_class"),
            }
        )
    return recent


def parse_mentor_response(
    text: str, *, available_tools: set[str] | None = None
) -> MentorAdvice:
    """Parse and validate the Mentor's structured response without guessing vectors."""
    payload = _json_object(text)
    if payload is None:
        return MentorAdvice(
            diagnosis="The Mentor returned an invalid structured response.",
            tactical_advice="Choose a clearly different untried route or attack class.",
            raw_response=text,
        )

    vectors: list[StrategyVector] = []
    raw_vectors = payload.get("suggested_vectors")
    if isinstance(raw_vectors, list):
        for index, raw in enumerate(raw_vectors[:3]):
            if not isinstance(raw, dict):
                continue
            vector = StrategyVector.from_dict(raw, index)
            if available_tools is not None:
                requested_tools = list(vector.tool_names)
                vector.tool_names = [
                    name for name in vector.tool_names if name in available_tools
                ]
                if requested_tools and not vector.tool_names:
                    continue
            if any(
                (
                    vector.tool_names,
                    vector.route_patterns,
                    vector.owasp_categories,
                    vector.test_classes,
                    vector.parameter_names,
                )
            ):
                vectors.append(vector)

    failure_class = str(payload.get("failure_class") or "unknown").strip()
    recovery_kind = str(payload.get("recovery_kind") or "pivot").strip()
    if available_tools is not None and recovery_kind == "execute_python":
        if "execute_python" not in available_tools:
            recovery_kind = "pivot"
    return MentorAdvice(
        diagnosis=str(
            payload.get("diagnosis") or "Execution progress stalled."
        ).strip(),
        suggested_vectors=vectors,
        tactical_advice=str(
            payload.get("tactical_advice") or "Pivot to an untried surface."
        ).strip(),
        failure_class=(
            failure_class if failure_class in _FAILURE_CLASSES else "unknown"
        ),
        recovery_kind=(
            recovery_kind if recovery_kind in _RECOVERY_KINDS else "pivot"
        ),
        raw_response=text,
    )


async def run_mentor_adviser(
    run_id: int,
    trigger_reason: str,
    target_url: str,
    history_snippet: list[dict],
    is_api_run: bool = False,
    loop_context: dict[str, Any] | None = None,
) -> MentorAdvice:
    """Invoke the run-scoped Mentor model and always emit a terminal status event."""
    run_kind = "api" if is_api_run else "web"
    events_svc.emit(
        run_id,
        {
            "type": "agent_status",
            "agent_id": "mentor",
            "role": "Mentor",
            "status": "active",
            "current_task": "Diagnosing stalled execution",
            "outcome": None,
            "_persist": True,
            "_run_kind": run_kind,
        },
    )
    events_svc.emit(
        run_id,
        {
            "type": "scanner_phase",
            "phase": "mentor_guidance",
            "status": "start",
            "message": f"Mentor Agent — analysing Execution Monitor intervention: {trigger_reason}",
            "data": {
                "emitter": "Mentor Agent",
                "trigger_reason": trigger_reason,
            },
            "_run_kind": run_kind,
        },
    )

    advice = MentorAdvice(
        diagnosis=f"Execution Monitor trigger: {trigger_reason}",
        tactical_advice="Choose a clearly different untried route or attack class.",
    )
    terminal_status = "complete"
    try:
        with Session(get_engine()) as session:
            run = session.get(ApiTestRun if is_api_run else TestRun, run_id)
            llm_cfg = get_llm_config_for_role(session, run, "mentor") if run else None
            code_config = session.get(CodeExecutionConfig, 1)
        if llm_cfg is None:
            terminal_status = "warning"
            log.warning(
                "Mentor invoked for run_id=%s without a resolvable model", run_id
            )
            return advice

        available_tools = {
            "context_tool",
            "http_request",
            "write_finding",
            "update_lead",
        }
        if not is_api_run:
            available_tools.update({"browser", "reauthenticate"})
        try:
            python_roles = set(json.loads(code_config.allowed_roles_json or "[]"))
        except (AttributeError, TypeError, json.JSONDecodeError):
            python_roles = set()
        python_configured = bool(
            code_config and code_config.enabled and "test_lead" in python_roles
        )
        if python_configured:
            available_tools.add("execute_python")
        incident = {
            "target_url": target_url,
            "trigger_reason": trigger_reason,
            "recent_history": _recent_incident_history(history_snippet),
            "scan_context": _redact_and_bound(loop_context or {}),
            "available_tools": sorted(available_tools),
            "python_sandbox": {
                "configured": python_configured,
                "browser_or_dom_access": False,
                "network_access": "AESPA broker only",
            },
        }
        raw_text = await llm_svc.plain_completion(
            llm_cfg,
            json.dumps(incident, sort_keys=True, default=str),
            system_prompt=MENTOR_DEBUG_SYSTEM_PROMPT,
        )
        advice = parse_mentor_response(raw_text, available_tools=available_tools)
        if not advice.suggested_vectors:
            terminal_status = "warning"
    except Exception as exc:
        terminal_status = "warning"
        log.warning("Mentor LLM call failed for run_id=%s: %s", run_id, exc)
    finally:
        vector_lines = []
        for index, vector in enumerate(advice.suggested_vectors, start=1):
            constraints = []
            if vector.tool_names:
                constraints.append(f"tools={','.join(vector.tool_names)}")
            if vector.route_patterns:
                constraints.append(f"routes={','.join(vector.route_patterns)}")
            if vector.owasp_categories:
                constraints.append(f"categories={','.join(vector.owasp_categories)}")
            if vector.test_classes:
                constraints.append(f"classes={','.join(vector.test_classes)}")
            if vector.parameter_names:
                constraints.append(f"parameters={','.join(vector.parameter_names)}")
            detail = f" — {'; '.join(constraints)}" if constraints else ""
            vector_lines.append(f"{index}. {vector.title} [{vector.id}]{detail}")
        alternatives = (
            "\n".join(vector_lines)
            if vector_lines
            else "No enforceable alternate vector was returned."
        )
        events_svc.emit(
            run_id,
            {
                "type": "scanner_phase",
                "phase": "mentor_guidance",
                "status": terminal_status,
                "message": (
                    "Mentor Alternate Instructions — "
                    f"Diagnosis: {advice.diagnosis}\n"
                    f"Suggested alternatives:\n{alternatives}\n"
                    f"Tactical next step: {advice.tactical_advice}"
                ),
                "data": {
                    "emitter": "Mentor Agent",
                    "trigger_reason": trigger_reason,
                    "failure_class": advice.failure_class,
                    "recovery_kind": advice.recovery_kind,
                    "diagnosis": advice.diagnosis,
                    "suggested_vectors": [
                        asdict(vector) for vector in advice.suggested_vectors
                    ],
                    "tactical_advice": advice.tactical_advice,
                },
                "_persist": True,
                "_run_kind": run_kind,
            },
        )
        events_svc.emit(
            run_id,
            {
                "type": "agent_status",
                "agent_id": "mentor",
                "role": "Mentor",
                "status": terminal_status,
                "current_task": "Mentor analysis finished",
                "outcome": advice.diagnosis[:150],
                "_persist": True,
                "_run_kind": run_kind,
            },
        )
    return advice
