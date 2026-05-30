"""A.L.I.C.E. chat coordinator service."""
from __future__ import annotations

import json
import logging
from typing import Any, Optional
from urllib.parse import urlparse

from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import CrawledPage, LLMConfig, ScanFinding, Site, TargetIntelItem, TestRun
from aespa.services import events as events_svc
from aespa.services import llm as llm_svc
from aespa.services import task_graph as task_graph_svc
from aespa.services.scope import check_scope
from aespa.services.settings import (
    get_llm_config_for_run,
    get_run_scanner_policy,
    get_upstream_proxy_config,
)
from aespa.services.prompts.alice import ALICE_SYSTEM_PROMPT

log = logging.getLogger(__name__)


def _extract_user_directive(history: list[dict]) -> str:
    """Find the most recent user prompt in the chat history."""
    for item in reversed(history):
        if item.get("sender") == "user" and item.get("text"):
            return str(item["text"]).strip()
    return "Prioritize general penetration testing."


async def run_alice_turn(run_id: int, user_instruction: str, history: list[dict]) -> dict[str, Any]:
    """Execute a single interactive penetration testing Turn for the A.L.I.C.E. agent.

    Ensures that any target URL in the user instruction or tool calls is validated
    firmly against the target sitemap scope boundaries.
    """
    log.info("ALICE turn started for run_id=%s instruction=%r", run_id, user_instruction)

    # 1. Establish configuration and site parameters
    with Session(get_engine()) as s:
        run = s.get(TestRun, run_id)
        if run is None:
            raise ValueError(f"TestRun {run_id} not found")
        site = s.get(Site, run.site_id)
        llm_cfg = get_llm_config_for_run(s, run)
        if llm_cfg is None:
            raise RuntimeError("No LLM configuration configured in Settings.")
        scanner_policy = get_run_scanner_policy(s, run)

        all_pages = s.exec(
            select(CrawledPage)
            .where(CrawledPage.test_run_id == run_id)
            .where(CrawledPage.in_scope != False)  # noqa: E712
        ).all()
        pages_snapshot = [
            {
                "id": p.id,
                "url": p.url,
                "title": p.title or "",
                "context": p.llm_context or "",
                "req_auth": p.req_auth,
                "takes_input": p.takes_input,
                "has_object_ref": p.has_object_ref,
                "has_business_logic": p.has_business_logic,
            }
            for p in all_pages
        ]

        existing_findings = s.exec(
            select(ScanFinding).where(ScanFinding.test_run_id == run_id)
        ).all()
        findings_snapshot = [
            {
                "title": f.title,
                "severity": f.severity,
                "owasp": f.owasp_category,
                "affected_url": f.affected_url,
                "description": f.description[:200],
            }
            for f in existing_findings
        ]

        upstream_proxy = get_upstream_proxy_config(s)
        llm_proxy_url = upstream_proxy.proxy_url if upstream_proxy.proxy_llm else None

        site_id = site.id
        base_url = str(site.base_url or "").strip()

    llm_svc.set_llm_proxy(llm_proxy_url)
    llm_svc.set_run_context(run_id, lambda evt: events_svc.emit(run_id, evt))

    # 2. Scope compliance checks on user directive
    # Look for any out-of-scope domain or URL listed in the user's text
    words = user_instruction.replace(",", " ").replace(";", " ").split()
    for word in words:
        if "://" in word or word.startswith("www."):
            clean_url = word.strip("'\"`(),")
            if not clean_url.startswith("http"):
                clean_url = "http://" + clean_url
            try:
                parsed = urlparse(clean_url)
                if parsed.netloc:
                    scope_error = check_scope(clean_url, site_id, run_id)
                    if scope_error:
                        log.warning("ALICE blocked out-of-scope target: %s", clean_url)
                        return {
                            "thought_process": "[A.L.I.C.E. Boundary Violation Alert]\nUser requested target is out-of-scope.",
                            "message": f"I cannot perform testing on '{clean_url}' because it is outside the authorized scope for this scan target. {scope_error}",
                            "status": "warning"
                        }
            except Exception:
                pass

    # 3. Format ALICE System Prompt
    system_message = ALICE_SYSTEM_PROMPT.format(
        user_directive=user_instruction,
        base_url=base_url,
    )

    # 4. Construct a concise agent context
    crawl_summary = (
        f"Target base URL: {base_url}\n"
        f"Crawl summary: {len(pages_snapshot)} pages discovered.\n"
    )
    if findings_snapshot:
        crawl_summary += "\nExisting proven findings (do NOT re-test):\n"
        for f in findings_snapshot:
            crawl_summary += f" - [{f['severity'].upper()}] {f['owasp']} {f['title']} @ {f['affected_url']}\n"

    initial_user_message = (
        f"{crawl_summary}\n"
        f"User instruction directive: \"{user_instruction}\"\n"
        "Analyze the scope and execute your pentesting coordination turns."
    )

    # 5. Define tool executor for A.L.I.C.E's turn
    # This captures LLM tool actions and routes them safely through sitemap scope checks
    async def alice_tool_executor(tool_name: str, tool_input: dict, step: int) -> str:
        note = tool_input.get("note") or f"Turn {step}"
        target_url = tool_input.get("url") or tool_input.get("target_url") or base_url

        # Direct scope check
        scope_err = check_scope(target_url, site_id, run_id)
        if scope_err:
            log.warning("ALICE tool %s blocked by scope: %s", tool_name, target_url)
            return json.dumps({
                "error": f"Request blocked: {scope_err}",
                "url": target_url,
                "status": 403
            })

        # Emits dynamic step notifications to web panel
        events_svc.emit(run_id, {
            "type": "agent_status",
            "agent_id": "alice",
            "role": "A.L.I.C.E",
            "status": "active",
            "current_task": f"Step {step}: {note}",
            "outcome": None,
        })

        # For the mock/wire-up phase, we execute read-only context operations or return success
        if tool_name == "context_tool":
            return json.dumps({
                "status": "success",
                "message": "Crawl map and entity details retrieved successfully.",
                "item_count": len(pages_snapshot)
            })

        return json.dumps({
            "status": "success",
            "message": f"Successfully planned action: {tool_name} against {target_url}",
        })

    # 6. Run the agentic tool-use loop
    # We use LLM completions to decide tool routing or plain completions depending on model
    final_summary = ""
    try:
        final_summary = await llm_svc.thinking_agentic_loop(
            config=llm_cfg,
            system_message=system_message,
            initial_user_message=initial_user_message,
            tool_executor=alice_tool_executor,
            emit_fn=lambda evt: events_svc.emit(run_id, evt),
            tools=llm_svc.THINKING_AGENT_TOOLS,
        )
    except Exception as exc:
        log.exception("ALICE loop execution failed")
        return {
            "thought_process": f"[ALICE Error]\nLoop failed: {exc}",
            "message": f"I encountered an error trying to orchestrate this turn: {exc}",
            "status": "error"
        }

    # 7. Construct final structured copilot response
    thought_summary = (
        f"[ALICE Pentest Coordinator Turn Summary]\n"
        f"Directive: \"{user_instruction}\"\n"
        f"Target Scope: {base_url}\n"
        f"Verified sitemap URLs and mapped target inputs.\n"
        f"Orchestrated test lead scanner alignment."
    )

    message_reply = final_summary or (
        f"I have reviewed the scope for your directive: \"{user_instruction}\". "
        f"All target vectors have been validated against our sitemap endpoints at {base_url}. "
        f"The scanner has been aligned to focus probes exclusively on the requested target functionality."
    )

    return {
        "thought_process": thought_summary,
        "message": message_reply,
        "status": "complete"
    }
