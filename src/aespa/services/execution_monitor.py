"""Bounded supervision for the autonomous Test Lead tool loop."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any
from urllib.parse import parse_qs, parse_qsl, urlencode, urlparse, urlunparse

_DYNAMIC_QUERY_PARAMS = frozenset(
    {
        "_",
        "ts",
        "timestamp",
        "nonce",
        "cachebuster",
        "cb",
        "rnd",
        "random",
        "_t",
        "_ts",
        "_r",
    }
)
_VOLATILE_HEADERS = frozenset(
    {"date", "traceparent", "tracestate", "x-correlation-id", "x-request-id"}
)
_HOUSEKEEPING_TOOLS = frozenset(
    {
        "context_tool",
        "skip_coverage",
        "update_lead",
        "write_finding",
        "remove_finding",
        "done",
    }
)


def normalize_url(url: str, *, preserve_fragment: bool = False) -> str:
    """Canonicalize transport noise without collapsing meaningful route semantics."""
    if not isinstance(url, str) or not url:
        return ""
    try:
        parsed = urlparse(url.strip())
        grouped: dict[str, list[str]] = {}
        for key, value in parse_qsl(parsed.query, keep_blank_values=True):
            if key.lower() not in _DYNAMIC_QUERY_PARAMS:
                grouped.setdefault(key, []).append(value)
        # Sort keys while retaining repeated-value order: parameter-pollution order
        # can change server behaviour and must remain part of the signature.
        query = urlencode(
            [(key, value) for key in sorted(grouped) for value in grouped[key]],
            doseq=True,
        )
        return urlunparse(
            (
                parsed.scheme.lower(),
                parsed.netloc.lower(),
                parsed.path or "/",
                parsed.params,
                query,
                parsed.fragment if preserve_fragment else "",
            )
        )
    except Exception:
        return url.strip()


def _normalize_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key).strip(): _normalize_payload(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, list):
        return [_normalize_payload(item) for item in value]
    if isinstance(value, str):
        return value.rstrip()
    return value


def _normalize_body(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.rstrip()
        try:
            value = json.loads(stripped)
        except (json.JSONDecodeError, TypeError):
            return stripped
    return _normalize_payload(value)


def _normalize_headers(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {
        str(key).strip().lower(): str(item).strip()
        for key, item in sorted(value.items(), key=lambda pair: str(pair[0]).lower())
        if str(key).strip().lower() not in _VOLATILE_HEADERS
    }


def normalize_tool_signature(
    tool_name: str,
    tool_input: dict[str, Any] | None,
    *,
    browser_page_url: str | None = None,
) -> str:
    """Return a stable fingerprint for semantically equivalent tool calls."""
    source = tool_input if isinstance(tool_input, dict) else {}
    name = str(tool_name or "").strip().lower()
    cleaned = {
        key: value
        for key, value in source.items()
        if key != "strategy_pivot_justification"
    }

    if name == "http_request":
        signature_data = {
            "tool": name,
            "method": str(cleaned.get("method") or "GET").upper(),
            "url": normalize_url(str(cleaned.get("url") or "")),
            "headers": _normalize_headers(cleaned.get("headers")),
            "body": _normalize_body(cleaned.get("body")) if "body" in cleaned else None,
            "session": str(cleaned.get("use_session") or "").strip(),
            "category": str(cleaned.get("owasp_category") or "").upper(),
            "test_class": str(cleaned.get("test_class") or "").lower(),
        }
    elif name == "browser":
        signature_data = {
            "tool": name,
            "url": normalize_url(str(cleaned.get("url") or ""), preserve_fragment=True),
            # Browser operations are stateful. The same click or DOM check on two
            # different pages is not the same execution, even when the model omits
            # the optional top-level URL from its tool input.
            "page_url": normalize_url(
                str(browser_page_url or ""), preserve_fragment=True
            ),
            "steps": _normalize_payload(cleaned.get("steps")),
            "session": str(cleaned.get("use_session") or "").strip(),
            "capture_session": str(cleaned.get("capture_session") or "").strip(),
            "capture_username": str(cleaned.get("capture_username") or "").strip(),
            "category": str(cleaned.get("owasp_category") or "").upper(),
            "test_class": str(cleaned.get("test_class") or "").lower(),
        }
    else:
        signature_data = {"tool": name, "input": _normalize_payload(cleaned)}

    serialized = json.dumps(
        signature_data, sort_keys=True, separators=(",", ":"), default=str
    )
    return hashlib.sha256(serialized.encode("utf-8", errors="replace")).hexdigest()[:16]


def summarize_tool_action(tool_name: str, tool_input: dict[str, Any] | None) -> str:
    """Return a concise, non-secret action description suitable for scan logs."""
    source = tool_input if isinstance(tool_input, dict) else {}
    name = str(tool_name or "").strip().lower()
    if name != "browser":
        method = str(source.get("method") or "").upper()
        url = str(source.get("url") or "").strip()
        return " ".join(part for part in (name, method, url) if part)

    descriptions: list[str] = []
    steps = source.get("steps") if isinstance(source.get("steps"), list) else []
    for step in steps[:5]:
        if not isinstance(step, dict):
            continue
        op = str(step.get("op") or "unknown").strip().lower()
        attributes = []
        for key in ("selector", "url"):
            value = str(step.get(key) or "").strip()
            if value:
                attributes.append(f'{key}="{value}"')
        if op == "wait" and step.get("value") is not None:
            attributes.append(f"value={step['value']}")
        descriptions.append(f"{op}({', '.join(attributes)})" if attributes else op)
    return "browser " + ("; ".join(descriptions) if descriptions else "default action")


def add_strategy_justification_to_tools(tools: list[dict] | None) -> list[dict] | None:
    """Return tool schemas that permit an explicit, auditable contract override."""
    if tools is None:
        return None
    result = copy.deepcopy(tools)
    for tool in result:
        if tool.get("name") == "done":
            continue
        schema = tool.get("input_schema")
        if isinstance(schema, dict):
            properties = schema.setdefault("properties", {})
            properties.setdefault(
                "strategy_pivot_justification",
                {
                    "type": "string",
                    "description": (
                        "When a Mentor Strategy Shift Contract is active, explain specifically "
                        "why this different action is a better pivot than the suggested vectors."
                    ),
                },
            )
    return result


class InterventionState(str, Enum):
    NORMAL = "normal"
    INVOKE_MENTOR_DUPLICATE = "invoke_mentor_duplicate"
    INVOKE_MENTOR_STAGNATION = "invoke_mentor_stagnation"
    HARD_BLOCK_DUPLICATE = "hard_block_duplicate"
    ENFORCE_STRATEGY_SHIFT = "enforce_strategy_shift"


@dataclass
class StrategyVector:
    id: str
    title: str
    tool_names: list[str] = field(default_factory=list)
    route_patterns: list[str] = field(default_factory=list)
    owasp_categories: list[str] = field(default_factory=list)
    test_classes: list[str] = field(default_factory=list)
    parameter_names: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, value: dict[str, Any], index: int = 0) -> "StrategyVector":
        def strings(name: str) -> list[str]:
            raw = value.get(name) or []
            return (
                [str(item).strip() for item in raw if str(item).strip()]
                if isinstance(raw, list)
                else []
            )

        return cls(
            id=str(value.get("id") or f"vector-{index + 1}"),
            title=str(value.get("title") or value.get("id") or f"Vector {index + 1}"),
            tool_names=strings("tool_names"),
            route_patterns=strings("route_patterns"),
            owasp_categories=strings("owasp_categories"),
            test_classes=strings("test_classes"),
            parameter_names=strings("parameter_names"),
        )


@dataclass
class StrategyShiftContract:
    stagnation_step: int
    diagnosis: str
    suggested_vectors: list[StrategyVector] = field(default_factory=list)
    rejections_count: int = 0


def _route_matches(pattern: str, url: str) -> bool:
    path = urlparse(url).path.lower()
    raw = urlparse(pattern).path if "://" in pattern else pattern
    escaped = re.escape(raw.lower()).replace(r"\*", ".*")
    escaped = re.sub(r"\\\{[^}]+\\\}", r"[^/]+", escaped)
    return re.fullmatch(escaped, path) is not None or raw.lower() in path


def _input_parameter_names(tool_input: dict[str, Any]) -> set[str]:
    names = {
        key.lower()
        for key in parse_qs(urlparse(str(tool_input.get("url") or "")).query)
    }

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                names.add(str(key).lower())
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(tool_input.get("body"))
    visit(tool_input.get("steps"))
    visit(tool_input.get("extra_fields"))
    return names


@dataclass
class ExecutionMonitor:
    duplicate_mentor_threshold: int = 2
    duplicate_hard_block_threshold: int = 3
    stagnation_mentor_threshold: int = 8
    max_hard_block_rejections: int = 3
    max_contract_rejections: int = 3
    probe_signature_counts: dict[str, int] = field(default_factory=dict)
    last_signature: str | None = None
    last_step: int | None = None
    last_action_summary: str = ""
    last_browser_page_url: str = ""
    last_result_signature: str | None = None
    last_intervention_details: dict[str, Any] = field(default_factory=dict)
    consecutive_duplicate_count: int = 0
    hard_block_rejections: int = 0
    nonprogress_steps: int = 0
    stagnation_mentor_emitted: bool = False
    active_contract: StrategyShiftContract | None = None
    pending_contract_satisfaction: bool = False
    termination_reason: str = ""

    def to_state(self) -> dict[str, Any]:
        contract = None
        if self.active_contract:
            contract = {
                "stagnation_step": self.active_contract.stagnation_step,
                "diagnosis": self.active_contract.diagnosis,
                "suggested_vectors": [
                    asdict(vector) for vector in self.active_contract.suggested_vectors
                ],
                "rejections_count": self.active_contract.rejections_count,
            }
        return {
            "duplicate_mentor_threshold": self.duplicate_mentor_threshold,
            "duplicate_hard_block_threshold": self.duplicate_hard_block_threshold,
            "stagnation_mentor_threshold": self.stagnation_mentor_threshold,
            "max_hard_block_rejections": self.max_hard_block_rejections,
            "max_contract_rejections": self.max_contract_rejections,
            "probe_signature_counts": self.probe_signature_counts,
            "last_signature": self.last_signature,
            "last_step": self.last_step,
            "last_action_summary": self.last_action_summary,
            "last_browser_page_url": self.last_browser_page_url,
            "last_result_signature": self.last_result_signature,
            "consecutive_duplicate_count": self.consecutive_duplicate_count,
            "hard_block_rejections": self.hard_block_rejections,
            "nonprogress_steps": self.nonprogress_steps,
            "stagnation_mentor_emitted": self.stagnation_mentor_emitted,
            "active_contract": contract,
            "pending_contract_satisfaction": self.pending_contract_satisfaction,
            "termination_reason": self.termination_reason,
        }

    @classmethod
    def from_state(cls, raw: dict[str, Any] | None) -> "ExecutionMonitor":
        monitor = cls()
        if not isinstance(raw, dict):
            return monitor
        for name in (
            "duplicate_mentor_threshold",
            "duplicate_hard_block_threshold",
            "stagnation_mentor_threshold",
            "max_hard_block_rejections",
            "max_contract_rejections",
            "consecutive_duplicate_count",
            "hard_block_rejections",
            "nonprogress_steps",
        ):
            try:
                if name in raw:
                    setattr(monitor, name, max(0, int(raw[name])))
            except (TypeError, ValueError):
                pass
        monitor.probe_signature_counts = (
            raw.get("probe_signature_counts")
            if isinstance(raw.get("probe_signature_counts"), dict)
            else {}
        )
        monitor.last_signature = (
            str(raw["last_signature"]) if raw.get("last_signature") else None
        )
        try:
            monitor.last_step = int(raw["last_step"]) if raw.get("last_step") else None
        except (TypeError, ValueError):
            monitor.last_step = None
        monitor.last_action_summary = str(raw.get("last_action_summary") or "")
        monitor.last_browser_page_url = str(raw.get("last_browser_page_url") or "")
        monitor.last_result_signature = (
            str(raw["last_result_signature"])
            if raw.get("last_result_signature")
            else None
        )
        monitor.stagnation_mentor_emitted = bool(raw.get("stagnation_mentor_emitted"))
        monitor.pending_contract_satisfaction = bool(
            raw.get("pending_contract_satisfaction")
        )
        monitor.termination_reason = str(raw.get("termination_reason") or "")
        contract = raw.get("active_contract")
        if isinstance(contract, dict):
            vectors = []
            for index, value in enumerate(contract.get("suggested_vectors") or []):
                if isinstance(value, dict):
                    vectors.append(StrategyVector.from_dict(value, index))
                elif value:
                    vectors.append(
                        StrategyVector(id=f"legacy-{index + 1}", title=str(value))
                    )
            monitor.active_contract = StrategyShiftContract(
                stagnation_step=int(contract.get("stagnation_step") or 0),
                diagnosis=str(contract.get("diagnosis") or ""),
                suggested_vectors=vectors,
                rejections_count=int(contract.get("rejections_count") or 0),
            )
        return monitor

    def _reset_duplicate_sequence(self) -> None:
        self.last_signature = None
        self.last_step = None
        self.last_action_summary = ""
        self.last_browser_page_url = ""
        self.last_result_signature = None
        self.last_intervention_details = {}
        self.consecutive_duplicate_count = 0
        self.hard_block_rejections = 0

    def observe_tool_call(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        step: int,
        *,
        browser_page_url: str | None = None,
    ) -> tuple[InterventionState, str | None]:
        """Evaluate a proposed action before execution."""
        if tool_name in _HOUSEKEEPING_TOOLS:
            self._reset_duplicate_sequence()
            return InterventionState.NORMAL, None

        signature = normalize_tool_signature(
            tool_name, tool_input, browser_page_url=browser_page_url
        )
        previous_step = self.last_step
        previous_page_url = self.last_browser_page_url
        is_duplicate = signature == self.last_signature
        if is_duplicate:
            self.consecutive_duplicate_count += 1
        else:
            self.last_signature = signature
            self.consecutive_duplicate_count = 1
            self.hard_block_rejections = 0
            self.last_result_signature = None
        action_summary = summarize_tool_action(tool_name, tool_input)
        current_page_url = str(browser_page_url or "") if tool_name == "browser" else ""
        self.last_intervention_details = {
            "signature": signature,
            "occurrence": self.consecutive_duplicate_count,
            "previous_step": previous_step if is_duplicate else None,
            "current_step": step,
            "action_summary": action_summary,
            "previous_page_url": previous_page_url if is_duplicate else "",
            "current_page_url": current_page_url,
            "executable_input_changed": not is_duplicate,
            "result_comparison": "pending" if is_duplicate else "not_applicable",
        }
        self.last_step = step
        self.last_action_summary = action_summary
        self.last_browser_page_url = current_page_url
        self.probe_signature_counts[signature] = (
            self.probe_signature_counts.get(signature, 0) + 1
        )

        if self.active_contract is not None:
            is_pivot, reason = self.check_strategy_pivot(tool_name, tool_input)
            if not is_pivot:
                self.active_contract.rejections_count += 1
                if (
                    self.active_contract.rejections_count
                    >= self.max_contract_rejections
                ):
                    self.termination_reason = "Test Lead stopped after repeatedly refusing the active Mentor Strategy Shift Contract."
                vectors = ", ".join(
                    f"{vector.id}: {vector.title}"
                    for vector in self.active_contract.suggested_vectors
                )
                return InterventionState.ENFORCE_STRATEGY_SHIFT, (
                    "[STRATEGY SHIFT REJECTED] "
                    f"{reason}. Choose one of: {vectors}; or provide strategy_pivot_justification."
                )
            self.pending_contract_satisfaction = True

        if self.consecutive_duplicate_count >= self.duplicate_hard_block_threshold:
            self.hard_block_rejections += 1
            if self.hard_block_rejections >= self.max_hard_block_rejections:
                self.termination_reason = "Test Lead stopped after repeatedly retrying a hard-blocked duplicate action."
            return InterventionState.HARD_BLOCK_DUPLICATE, (
                "[EXECUTION MONITOR HARD BLOCK] The same normalized action was requested "
                f"{self.consecutive_duplicate_count} times in a row "
                f"(previous step {previous_step}, current step {step}): {action_summary}. "
                "Choose a different action."
            )

        if self.consecutive_duplicate_count == self.duplicate_mentor_threshold:
            return (
                InterventionState.INVOKE_MENTOR_DUPLICATE,
                "The same normalized action was requested twice in a row "
                f"(previous step {previous_step}, current step {step}): {action_summary}. "
                "Executable input changed: no; result comparison: pending execution.",
            )

        if (
            self.nonprogress_steps >= self.stagnation_mentor_threshold
            and not self.stagnation_mentor_emitted
        ):
            self.stagnation_mentor_emitted = True
            return InterventionState.INVOKE_MENTOR_STAGNATION, (
                f"{self.nonprogress_steps} consecutive completed steps produced no new progress signal."
            )
        return InterventionState.NORMAL, None

    def observe_executed_result(
        self, tool_name: str, result: str, step: int
    ) -> dict[str, Any] | None:
        """Compare the outcome of an executed duplicate with its predecessor."""
        if step != self.last_step:
            return None
        raw_result = str(result or "").split("\n\n<mentor_analysis>", 1)[0].rstrip()
        result_signature = hashlib.sha256(
            raw_result.encode("utf-8", errors="replace")
        ).hexdigest()[:16]
        comparison = None
        if self.consecutive_duplicate_count >= 2 and self.last_result_signature:
            comparison = {
                **self.last_intervention_details,
                "tool": tool_name,
                "result_changed": result_signature != self.last_result_signature,
                "result_comparison": "changed"
                if result_signature != self.last_result_signature
                else "unchanged",
            }
        self.last_result_signature = result_signature
        return comparison

    def finish_step(self, *, progress_made: bool, executed: bool) -> None:
        """Finalize every executed or rejected tool step exactly once."""
        if progress_made:
            self.nonprogress_steps = 0
            self.stagnation_mentor_emitted = False
        else:
            self.nonprogress_steps += 1
        if executed and self.pending_contract_satisfaction:
            self.active_contract = None
            self.pending_contract_satisfaction = False

    def record_progress(self, progress_made: bool) -> None:
        """Compatibility wrapper for isolated callers and older checkpoints."""
        self.finish_step(progress_made=progress_made, executed=True)

    def set_strategy_contract(
        self, step: int, diagnosis: str, suggested_vectors: list[StrategyVector]
    ) -> None:
        self.active_contract = StrategyShiftContract(step, diagnosis, suggested_vectors)
        self.pending_contract_satisfaction = False

    def check_strategy_pivot(
        self, tool_name: str, tool_input: dict[str, Any]
    ) -> tuple[bool, str]:
        if not self.active_contract:
            return True, "No active contract"
        justification = str(
            tool_input.get("strategy_pivot_justification") or ""
        ).strip()
        if justification:
            return True, f"Explicit justification supplied: {justification}"

        url = str(tool_input.get("url") or "")
        category = str(tool_input.get("owasp_category") or "").lower()
        test_class = str(tool_input.get("test_class") or "").lower()
        parameters = _input_parameter_names(tool_input)
        for vector in self.active_contract.suggested_vectors:
            constraints = 0
            matched = True
            if vector.tool_names:
                constraints += 1
                matched &= tool_name.lower() in {
                    item.lower() for item in vector.tool_names
                }
            if vector.route_patterns:
                constraints += 1
                matched &= any(
                    _route_matches(pattern, url) for pattern in vector.route_patterns
                )
            if vector.owasp_categories:
                constraints += 1
                matched &= category in {
                    item.lower() for item in vector.owasp_categories
                }
            if vector.test_classes:
                constraints += 1
                matched &= test_class in {item.lower() for item in vector.test_classes}
            if vector.parameter_names:
                constraints += 1
                matched &= bool(
                    parameters & {item.lower() for item in vector.parameter_names}
                )
            if matched and constraints:
                return True, f"Matches structured vector {vector.id}"
        return (
            False,
            "The proposed tool input does not match any structured Mentor vector",
        )

    def check_termination(self) -> str | None:
        return self.termination_reason or None
