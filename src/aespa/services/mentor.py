"""Senior Security Mentor adviser for stalled Test Lead scans."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from sqlmodel import Session

from aespa.db import get_engine
from aespa.models import ApiTestRun, TestRun
from aespa.services import events as events_svc
from aespa.services import llm as llm_svc
from aespa.services.execution_monitor import StrategyVector
from aespa.services.prompts.mentor import MENTOR_SYSTEM_PROMPT
from aespa.services.settings import get_llm_config_for_role

log = logging.getLogger("aespa.mentor")


@dataclass
class MentorAdvice:
    diagnosis: str
    suggested_vectors: list[StrategyVector] = field(default_factory=list)
    tactical_advice: str = ""
    raw_response: str = ""

    def format_xml_block(self) -> str:
        vectors = (
            "\n".join(
                f"- {vector.id}: {vector.title}" for vector in self.suggested_vectors
            )
            or "- No enforceable vector was produced; choose a clearly different untried action."
        )
        return (
            "<mentor_analysis>\n"
            f"DIAGNOSIS:\n{self.diagnosis}\n\n"
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


def parse_mentor_response(text: str) -> MentorAdvice:
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

    return MentorAdvice(
        diagnosis=str(
            payload.get("diagnosis") or "Execution progress stalled."
        ).strip(),
        suggested_vectors=vectors,
        tactical_advice=str(
            payload.get("tactical_advice") or "Pivot to an untried surface."
        ).strip(),
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
        if llm_cfg is None:
            terminal_status = "warning"
            log.warning(
                "Mentor invoked for run_id=%s without a resolvable model", run_id
            )
            return advice

        recent_history = []
        for item in history_snippet[-8:]:
            recent_history.append(
                {
                    "step": item.get("step"),
                    "tool": item.get("tool") or item.get("method"),
                    "url": item.get("url") or item.get("target"),
                    "status": item.get("response_status") or item.get("status"),
                    "note": item.get("note") or item.get("desc"),
                    "owasp_category": item.get("owasp_category"),
                    "test_class": item.get("test_class"),
                }
            )
        incident = {
            "target_url": target_url,
            "trigger_reason": trigger_reason,
            "recent_history": recent_history,
            "scan_context": loop_context or {},
        }
        raw_text = await llm_svc.plain_completion(
            llm_cfg,
            json.dumps(incident, sort_keys=True, default=str),
            system_prompt=MENTOR_SYSTEM_PROMPT,
        )
        advice = parse_mentor_response(raw_text)
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
                constraints.append(
                    f"categories={','.join(vector.owasp_categories)}"
                )
            if vector.test_classes:
                constraints.append(f"classes={','.join(vector.test_classes)}")
            if vector.parameter_names:
                constraints.append(f"parameters={','.join(vector.parameter_names)}")
            detail = f" — {'; '.join(constraints)}" if constraints else ""
            vector_lines.append(
                f"{index}. {vector.title} [{vector.id}]{detail}"
            )
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
