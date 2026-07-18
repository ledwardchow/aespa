"""Bounded completion policy for the autonomous Test Lead loop.

The policy deliberately measures persisted scan facts instead of maintaining an
LLM-authored task graph.  Productive scans remain uncapped, while completion
challenges, repeated probes, and stretches without measurable progress are
strictly bounded.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Callable

from aespa.services.execution_monitor import ExecutionMonitor


def _fingerprint(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8", errors="replace")).hexdigest()[
        :16
    ]


@dataclass
class ScanCompletionPolicy:
    """State machine used by a single Test Lead scan."""

    repeat_limit: int = 3
    stagnation_warning_calls: int = 40
    stagnation_stop_calls: int = 50
    max_session_challenges: int = 1
    max_coverage_rounds: int = 2
    max_total_rejections: int = 3
    sessions: dict[str, dict[str, Any]] = field(default_factory=dict)
    probe_outcomes: dict[str, dict[str, Any]] = field(default_factory=dict)
    progress_keys: set[str] = field(default_factory=set)
    progress_generation: int = 0
    observed_generation: int = 0
    nonprogress_tool_calls: int = 0
    stagnation_warning_emitted: bool = False
    session_challenges: int = 0
    coverage_rounds: int = 0
    total_rejections: int = 0
    coverage_challenge_active: bool = False
    coverage_challenge_generation: int = 0
    termination_reason: str = ""

    execution_monitor: ExecutionMonitor = field(default_factory=ExecutionMonitor)

    @classmethod
    def from_state(cls, raw: dict[str, Any] | None) -> "ScanCompletionPolicy":
        policy = cls()
        if not isinstance(raw, dict):
            return policy
        policy.sessions = (
            raw.get("sessions") if isinstance(raw.get("sessions"), dict) else {}
        )
        policy.probe_outcomes = (
            raw.get("probe_outcomes")
            if isinstance(raw.get("probe_outcomes"), dict)
            else {}
        )
        policy.progress_keys = {
            str(item) for item in raw.get("progress_keys", []) if item is not None
        }
        for name in (
            "progress_generation",
            "observed_generation",
            "nonprogress_tool_calls",
            "session_challenges",
            "coverage_rounds",
            "total_rejections",
            "coverage_challenge_generation",
        ):
            try:
                setattr(policy, name, max(0, int(raw.get(name, 0))))
            except (TypeError, ValueError):
                pass
        policy.stagnation_warning_emitted = bool(
            raw.get("stagnation_warning_emitted", False)
        )
        policy.coverage_challenge_active = bool(
            raw.get("coverage_challenge_active", False)
        )
        policy.termination_reason = str(raw.get("termination_reason") or "")
        # A checkpoint is taken after a complete tool turn, so this is the correct
        # baseline for deciding whether the next tool produces new progress.
        policy.observed_generation = policy.progress_generation
        if "execution_monitor" in raw:
            policy.execution_monitor = ExecutionMonitor.from_state(
                raw.get("execution_monitor")
            )
        return policy

    def to_state(self) -> dict[str, Any]:
        return {
            "sessions": self.sessions,
            "probe_outcomes": self.probe_outcomes,
            "progress_keys": sorted(self.progress_keys),
            "progress_generation": self.progress_generation,
            "observed_generation": self.observed_generation,
            "nonprogress_tool_calls": self.nonprogress_tool_calls,
            "stagnation_warning_emitted": self.stagnation_warning_emitted,
            "session_challenges": self.session_challenges,
            "coverage_rounds": self.coverage_rounds,
            "total_rejections": self.total_rejections,
            "coverage_challenge_active": self.coverage_challenge_active,
            "coverage_challenge_generation": self.coverage_challenge_generation,
            "termination_reason": self.termination_reason,
            "execution_monitor": self.execution_monitor.to_state(),
        }

    def record_progress(self, key: str) -> bool:
        key = str(key or "").strip()
        if not key or key in self.progress_keys:
            return False
        self.progress_keys.add(key)
        self.progress_generation += 1
        return True

    def session_created(self, label: str | None) -> None:
        if not label:
            return
        label = str(label)
        self.sessions[label] = {
            "active": True,
            "attempted": False,
            "last_status": None,
        }

    def session_attempted(self, label: str | None, status: int) -> None:
        if not label:
            return
        label = str(label)
        state = self.sessions.setdefault(
            label, {"active": True, "attempted": False, "last_status": None}
        )
        first_attempt = not bool(state.get("attempted"))
        state["attempted"] = True
        state["last_status"] = int(status or 0)
        if status in (0, 401, 403):
            state["active"] = False
        if first_attempt:
            self.record_progress(f"session-attempt:{label}")

    def session_evicted(self, label: str | None, status: int = 0) -> None:
        if not label:
            return
        self.session_attempted(label, status)
        self.sessions[str(label)]["active"] = False

    def pending_session_labels(self) -> list[str]:
        return sorted(
            label
            for label, state in self.sessions.items()
            if state.get("active") and not state.get("attempted")
        )

    @staticmethod
    def probe_signature(
        *,
        method: str,
        url: str,
        body: Any,
        session_label: str | None,
        owasp_category: str,
        test_class: str = "",
    ) -> str:
        payload = json.dumps(
            {
                "method": (method or "GET").upper(),
                "url": str(url or "").strip(),
                "body": body,
                "session": session_label or "",
                "category": (owasp_category or "").upper(),
                "test_class": (test_class or "").lower(),
            },
            sort_keys=True,
            default=str,
            separators=(",", ":"),
        )
        return _fingerprint(payload)

    def repeated_probe_message(self, signature: str) -> str | None:
        state = self.probe_outcomes.get(signature) or {}
        if int(state.get("count") or 0) < self.repeat_limit:
            return None
        return (
            "[REPEATED PROBE SUPPRESSED] This exact request has already produced "
            f"the same outcome {state['count']} times (status "
            f"{state.get('status', 0)}). Change the route, payload, session, or "
            "OWASP category, or call done if no useful attack surface remains."
        )

    def record_probe_outcome(
        self, signature: str, status: int, response_body: str
    ) -> None:
        response_fingerprint = _fingerprint(response_body)
        previous = self.probe_outcomes.get(signature) or {}
        same = (
            int(previous.get("status") or 0) == int(status or 0)
            and previous.get("response_fingerprint") == response_fingerprint
        )
        self.probe_outcomes[signature] = {
            "status": int(status or 0),
            "response_fingerprint": response_fingerprint,
            "count": int(previous.get("count") or 0) + 1 if same else 1,
        }

    def observe_tool_result(self, result: str, *, executed: bool = True) -> str:
        """Update stagnation counters and append the one-time warning if needed."""
        if self.progress_generation > self.observed_generation:
            self.observed_generation = self.progress_generation
            self.nonprogress_tool_calls = 0
            self.stagnation_warning_emitted = False
            self.execution_monitor.finish_step(progress_made=True, executed=executed)
            return result

        self.nonprogress_tool_calls += 1
        self.execution_monitor.finish_step(progress_made=False, executed=executed)
        if (
            self.nonprogress_tool_calls >= self.stagnation_warning_calls
            and not self.stagnation_warning_emitted
        ):
            self.stagnation_warning_emitted = True
            return (
                result
                + "\n\n[SCAN STAGNATION] No new route/category coverage, finding, "
                "lead resolution, or session use has been recorded in "
                f"{self.nonprogress_tool_calls} tool calls. Switch to a genuinely "
                "different uncovered surface or call done. The Test Lead will stop "
                "automatically after 10 more calls without progress."
            )
        return result

    def check_termination(self) -> str | None:
        if self.termination_reason:
            return self.termination_reason
        monitor_reason = self.execution_monitor.check_termination()
        if monitor_reason:
            self.termination_reason = monitor_reason
            return self.termination_reason
        if self.nonprogress_tool_calls >= self.stagnation_stop_calls:
            self.termination_reason = (
                "Test Lead stopped after "
                f"{self.nonprogress_tool_calls} tool calls without measurable progress."
            )
            return self.termination_reason
        return None

    def check_done(
        self,
        coverage_gaps: Callable[[], dict[str, Any]] | None = None,
    ) -> tuple[bool, str, str]:
        """Return ``(allowed, model_feedback, log_message)`` for a done request."""
        pending = self.pending_session_labels()
        if pending:
            if (
                self.session_challenges < self.max_session_challenges
                and self.total_rejections < self.max_total_rejections
            ):
                self.session_challenges += 1
                self.total_rejections += 1
                labels = ", ".join(pending[:5])
                feedback = (
                    "Before finishing, exercise these active, never-attempted session "
                    f"labels once: {labels}. Use each label on one relevant authenticated "
                    "endpoint. A 401 or 403 still counts as an attempt and the invalid "
                    "session will be evicted; do not retry it."
                )
                return (
                    False,
                    feedback,
                    (
                        "Completion delayed for one bounded session-use challenge: "
                        + labels
                    ),
                )
            return True, "", "Completion accepted: session-use challenge was declined."

        # A coverage challenge is evaluated once. Lack of progress after it is an
        # exhaustion signal, not grounds to repeat the same demand indefinitely.
        if self.coverage_challenge_active:
            gained = self.progress_generation - self.coverage_challenge_generation
            self.coverage_challenge_active = False
            if gained < 3:
                return (
                    True,
                    "",
                    (
                        "Completion accepted: coverage challenge produced fewer than three "
                        f"new progress signals ({gained})."
                    ),
                )

        gaps = coverage_gaps() if coverage_gaps is not None else {}
        actions = list(gaps.get("next_actions") or [])
        if (
            actions
            and self.coverage_rounds < self.max_coverage_rounds
            and self.total_rejections < self.max_total_rejections
        ):
            self.coverage_rounds += 1
            self.total_rejections += 1
            self.coverage_challenge_active = True
            self.coverage_challenge_generation = self.progress_generation
            lines = []
            for action in actions[:6]:
                lines.append(
                    f"- {action.get('method', 'GET')} {action.get('url')} "
                    f"category={action.get('owasp_category')}"
                    + (
                        f" test_class={action.get('test_class')}"
                        if action.get("test_class")
                        else ""
                    )
                    + f" — {action.get('reason')}"
                )
            feedback = (
                f"Complete one bounded coverage round ({self.coverage_rounds}/"
                f"{self.max_coverage_rounds}) before finishing. Select targeted payloads "
                "for these live uncovered workprogram cells:\n"
                + "\n".join(lines)
                + "\nIf these probes are blocked or unproductive, call done again; "
                "completion will not be trapped."
            )
            return (
                False,
                feedback,
                (
                    f"Completion delayed: supplied {min(6, len(actions))} live coverage "
                    f"gaps (round {self.coverage_rounds}/{self.max_coverage_rounds})."
                ),
            )

        return True, "", "Completion accepted: bounded completion checks satisfied."
