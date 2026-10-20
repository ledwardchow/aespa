"""Shorter scan instructions used after an OpenAI cybersecurity refusal."""

from __future__ import annotations

from dataclasses import dataclass

from aespa.services.prompts.test_lead import (
    _THINKING_PENTEST_PLAYBOOK,
)


@dataclass(frozen=True)
class RefusalRecoveryPrompt:
    system: str
    initial_user: str
    template_id: str


_WEB_GUIDANCE = (
    "You are conducting the configured, authorized security assessment. Work from the "
    "supplied route and input inventory. Choose one endpoint and one test class at a "
    "time. Establish the expected baseline, run a bounded check with the available "
    "AESPA tools, and compare the result with the baseline. Test SQL injection and XSS "
    "as separate classes where the inputs support them. For XSS, distinguish reflected "
    "text from browser execution and check stored values in each relevant rendering "
    "view. For SQL injection, confirm the behavior before assessing database privileges "
    "or further impact. Use context_tool for saved scan data such as coverage_gaps, "
    "target_inventory, and traffic_search when needed. Write a finding only from direct "
    "tool evidence. Leave an untested coverage item open and explain the blocker."
)

_API_GUIDANCE = (
    "Work from the supplied API endpoint and input inventory. Choose one endpoint and "
    "one applicable OWASP API test class at a time. Compare a baseline with a bounded "
    "controlled check using the available tools. Keep the configured account, target "
    "scope, and request limits. Use context_tool for saved endpoint, traffic, coverage, "
    "and lead data when needed. Write findings only from direct tool evidence and leave "
    "unverified coverage open. Continue until the in-scope API work is complete."
)

_SQLI_GUIDANCE = (
    "Investigate SQL injection on the endpoint and parameters in your handoff. Keep the "
    "same configured account, target scope, request limits, and tool restrictions. First "
    "compare a normal request with a small controlled variation for each relevant input. "
    "Use response content, errors, or repeatable timing differences to confirm or rule "
    "out injection. Record the exact observations and use controls before treating a "
    "difference as proof. If injection is confirmed, assess the impact permitted by the "
    "scan policy, one capability at a time. Do not retrieve bulk records or personal "
    "data. Write a finding only when a tool result proves the behavior; otherwise report "
    "the remaining proof gap through done. Use context_tool only for saved scan data such "
    "as traffic_search and endpoint_detail. Use http_request for bounded verification."
)

_XSS_GUIDANCE = (
    "Investigate cross-site scripting on the exact endpoint and account in your handoff. "
    "The handoff may report reflected input; reflection alone does not prove browser "
    "execution. Use the browser tool to check the identified rendering view with the "
    "configured session. Record whether the canary appears as text, as a DOM value, or "
    "as an executed effect. Use dom_check for the exact canary attribute when the handoff "
    "provides one. For a stored value, inspect each relevant rendering view. Keep the "
    "assigned route and scope. Write a finding only from direct browser or request "
    "evidence; otherwise report the proof gap through done. Use context_tool only for "
    "saved scan data."
)


def test_lead_recovery_prompt(
    *,
    original_system: str,
    scoped_initial_user: str,
    is_api_run: bool,
) -> RefusalRecoveryPrompt | None:
    if is_api_run:
        start = original_system.find(
            "OWASP API Top 10 — test all applicable categories:"
        )
        end = original_system.find("Tool rules:\n", start)
        if start < 0 or end < 0:
            return None
        system = (
            original_system[:start] + _API_GUIDANCE + "\n\n" + original_system[end:]
        )
        template_id = "api-test-lead-v1"
    else:
        if _THINKING_PENTEST_PLAYBOOK not in original_system:
            return None
        start = original_system.find(
            "XSS is a primary objective, separate from SQL injection."
        )
        end = original_system.find(
            "Your conversation contains every prior tool result", start
        )
        if start < 0 or end < 0:
            return None
        system = (
            original_system[:start] + _WEB_GUIDANCE + "\n\n" + original_system[end:]
        )
        system = system.replace(_THINKING_PENTEST_PLAYBOOK, "", 1)
        template_id = "web-test-lead-v1"
    return RefusalRecoveryPrompt(
        system=system,
        initial_user=scoped_initial_user,
        template_id=template_id,
    )


def specialist_recovery_prompt(
    *, attack_class: str, initial_user: str
) -> RefusalRecoveryPrompt:
    guidance = {
        "sqli": _SQLI_GUIDANCE,
        "xss": _XSS_GUIDANCE,
    }.get(
        attack_class,
        (
            f"Investigate {attack_class} only for the assigned endpoint and account in "
            "your handoff. Choose one bounded verification step at a time. Keep the "
            "configured scope, request limits, and tool restrictions. Compare observations "
            "with a baseline, write a finding only from direct tool evidence, and report "
            "unresolved proof gaps through done. Use context_tool only for saved scan data."
        ),
    )
    return RefusalRecoveryPrompt(
        system=guidance,
        initial_user=(
            initial_user
            + "\n\nContinue this assigned test with one bounded confirmation step based on "
            "the handoff above. Keep its endpoint and account."
        ),
        template_id=f"web-specialist-{attack_class}-v1",
    )
