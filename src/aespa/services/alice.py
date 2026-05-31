"""A.L.I.C.E. chat coordinator service."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncGenerator
from urllib.parse import urlparse

from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import CrawledPage, LLMConfig, Site, TestRun
from aespa.services import events as events_svc
from aespa.services import llm as llm_svc
from aespa.services.scope import check_scope
from aespa.services.settings import (
    get_llm_config_for_run,
    get_scanner_policy,
)
from aespa.services.prompts.alice import ALICE_SYSTEM_PROMPT
from aespa.services.prompts.specialist import get_specialist_tools, SPECIALIST_AGENT_TOOLS

log = logging.getLogger(__name__)


def _get_alice_timeout(run_id: int) -> float:  # noqa: ARG001
    """Return the configured request timeout, falling back to the scanner default."""
    from aespa.services.scanner import REQUEST_TIMEOUT
    try:
        with Session(get_engine()) as _s:
            return get_scanner_policy(_s).request_timeout_s
    except Exception:
        return REQUEST_TIMEOUT


# Hard step limit to prevent runaway loops regardless of model behaviour.
ALICE_MAX_STEPS = 40

# Tools available to A.L.I.C.E. — same as specialist but without agent_dispatch loops.
_ALICE_TOOL_NAMES = {
    "http_request", "browser", "context_tool",
    "write_finding", "forge_jwt", "decode_jwt",
    "credential_check", "register_account", "agent_dispatch", "done",
}


def _extract_user_directive(history: list[dict]) -> str:
    """Find the most recent user prompt in the chat history."""
    for item in reversed(history):
        if item.get("sender") == "user" and item.get("text"):
            return str(item["text"]).strip()
    return "Prioritize general penetration testing."


def _get_alice_tools() -> list[dict]:
    """Return the full THINKING_AGENT_TOOLS list filtered to ALICE's allowed set."""
    from aespa.services.prompts.test_lead import THINKING_AGENT_TOOLS
    return [t for t in THINKING_AGENT_TOOLS if t["name"] in _ALICE_TOOL_NAMES]


async def _execute_alice_tool(
    run_id: int,
    llm_cfg: LLMConfig,
    base_url: str,
    site_id: int,
    tool_name: str,
    tool_input: dict,
    step: int,
) -> str:
    """Execute a single ALICE tool call and return the result string."""

    # ── http_request ─────────────────────────────────────────────────────────
    if tool_name == "http_request":
        from aespa.services.scanner import (
            _make_scanner_client,
            REQUEST_TIMEOUT,
        )
        from aespa.services import traffic as traffic_svc

        _url = str(tool_input.get("url") or base_url)
        scope_err = check_scope(_url, site_id, run_id)
        if scope_err:
            return f"[SCOPE BLOCK] {scope_err}"

        method = str(tool_input.get("method") or "GET").upper()
        headers = dict(tool_input.get("headers") or {})
        body = tool_input.get("body")

        timeout = _get_alice_timeout(run_id)

        async with _make_scanner_client(
            cookies={},
            headers={"User-Agent": "Mozilla/5.0 (compatible; ALICE/1.0)"},
            timeout=timeout,
            follow_redirects=True,
            verify=False,
            event_hooks=traffic_svc.make_httpx_hooks(run_id, username="alice"),
        ) as hx:
            try:
                kwargs: dict = {}
                if body is not None:
                    if isinstance(body, dict):
                        kwargs["json"] = body
                    else:
                        kwargs["content"] = str(body).encode()
                if headers:
                    kwargs["headers"] = headers
                resp = await hx.request(method, _url, **kwargs)
                resp_body = resp.text[:8192]
                return (
                    f"HTTP {resp.status_code} {method} {_url}\n"
                    f"Response Headers: {dict(resp.headers)}\n"
                    f"Response Body ({len(resp_body)} chars):\n{resp_body}"
                )
            except Exception as exc:
                return f"Request failed: {exc}"

    # ── context_tool ─────────────────────────────────────────────────────────
    if tool_name == "context_tool":
        from aespa.services.scanner import _run_thinking_context_tool

        ctx_tool = str(tool_input.get("tool") or "")
        ctx_args = tool_input.get("args") if isinstance(tool_input.get("args"), dict) else {}
        try:
            with Session(get_engine()) as s:
                pages = s.exec(select(CrawledPage).where(CrawledPage.test_run_id == run_id)).all()
                pages_snapshot = [p.model_dump() for p in pages]

            output = _run_thinking_context_tool(
                ctx_tool, ctx_args,
                pages_snapshot=pages_snapshot,
                findings_snapshot=[],
                history=[],
                run_id=run_id,
                base_url=base_url,
            )
            result = json.dumps(output, separators=(",", ":"), default=str)
            return result[:8192]
        except Exception as exc:
            return f"Context tool error: {exc}"

    # ── write_finding ─────────────────────────────────────────────────────────
    if tool_name == "write_finding":
        from aespa.services.scanner import _persist_dynamic_finding

        finding_raw = dict(tool_input)
        finding_raw["finding_source"] = "alice"

        if "url" in finding_raw and "affected_url" not in finding_raw:
            finding_raw["affected_url"] = finding_raw.pop("url")

        affected = (finding_raw.get("affected_url") or base_url).strip() or base_url

        with Session(get_engine()) as s:
            pages = s.exec(select(CrawledPage).where(CrawledPage.test_run_id == run_id)).all()
            pages_snapshot = [p.model_dump() for p in pages]
            first_page_id = pages[0].id if pages else None

        events_svc.emit(run_id, {
            "type": "agent_status",
            "agent_id": "reporting",
            "role": "Reporting",
            "status": "active",
            "current_task": f"A.L.I.C.E. Writing: {finding_raw.get('title', 'Untitled')}",
            "outcome": None,
            "_persist": True,
        })

        fw_result = {
            "source": "finding_write",
            "desc": finding_raw.get("description", "A.L.I.C.E. dynamic finding"),
            "url": affected,
            "status": 200,
            "headers": {"content-type": "application/json"},
            "body": str(finding_raw.get("evidence") or "")[:1000],
            "request_evidence": str(finding_raw.get("request_evidence") or ""),
            "response_evidence": str(finding_raw.get("response_evidence") or ""),
        }

        try:
            saved = await _persist_dynamic_finding(
                run_id=run_id,
                llm_cfg=llm_cfg,
                raw=finding_raw,
                base_url=base_url,
                pages_snapshot=pages_snapshot,
                first_page_id=first_page_id,
                result_by_url={str(affected): fw_result},
                writeup_source="test_lead",
                skip_normalize=True,
            )
            log.info("A.L.I.C.E. write_finding run_id=%s title=%r", run_id, finding_raw.get("title"))
            if saved is not None:
                from aespa.services import validator as _validator_svc
                asyncio.create_task(
                    _validator_svc.validate_finding_inline(
                        run_id,
                        saved.id,
                        llm_cfg=llm_cfg,
                    )
                )
            events_svc.emit(run_id, {
                "type": "agent_status",
                "agent_id": "reporting",
                "role": "Reporting",
                "status": "idle",
                "current_task": f"A.L.I.C.E. Wrote: {finding_raw.get('title', 'Untitled')}",
                "outcome": (
                    f"Saved [{finding_raw.get('severity', '?')}] {finding_raw.get('title', 'Untitled')} (ID: {saved.id})"
                    if saved else
                    f"Duplicate skipped: {finding_raw.get('title', 'Untitled')}"
                ),
                "_persist": True,
            })
            return f"Finding '{finding_raw.get('title')}' recorded successfully."
        except Exception as exc:
            log.warning("A.L.I.C.E. write_finding failed: %s", exc)
            events_svc.emit(run_id, {
                "type": "agent_status",
                "agent_id": "reporting",
                "role": "Reporting",
                "status": "idle",
                "current_task": "A.L.I.C.E. Write failed",
                "outcome": f"Error: {exc}",
                "_persist": True,
            })
            return f"write_finding failed: {exc}"

    # ── forge_jwt ─────────────────────────────────────────────────────────────
    if tool_name == "forge_jwt":
        from aespa.services.scanner import _sign_hs256_jwt, _record_session, _session_label, _mark_session_pending
        import time

        jwt_secret = str(tool_input.get("secret") or "")
        jwt_claims = tool_input.get("claims") if isinstance(tool_input.get("claims"), dict) else {}
        jwt_header = tool_input.get("header") if isinstance(tool_input.get("header"), dict) else None
        store_as = tool_input.get("store_as")

        try:
            jwt_token = _sign_hs256_jwt(jwt_secret, jwt_claims, jwt_header)
            label = store_as or f"alice_jwt_{step}"
            _record_session(
                run_id,
                label=label,
                session_data={
                    "label": label,
                    "kind": "bearer",
                    "username": f"sub:{jwt_claims.get('sub')}" if jwt_claims.get("sub") is not None else None,
                    "source": "forge_jwt tool",
                    "extra_headers": {"Authorization": f"Bearer {jwt_token}"},
                    "cookies": {},
                },
                source="alice_jwt_action",
                metadata={"claims": jwt_claims, "header": jwt_header or {"typ": "JWT", "alg": "HS256"}},
            )
            _mark_session_pending(label)
            return json.dumps({"store_as": label, "claims": jwt_claims, "token": jwt_token[:80] + "..."})
        except Exception as exc:
            return f"JWT signing failed: {exc}"

    # ── decode_jwt ─────────────────────────────────────────────────────────────
    if tool_name == "decode_jwt":
        import base64 as _b64

        token = str(tool_input.get("token") or "")
        parts = token.split(".")
        if len(parts) < 2:
            return "Invalid JWT: expected at least 2 parts separated by '.'"
        decoded = {}
        for i, part_name in enumerate(["header", "payload"]):
            try:
                padding = "=" * (-len(parts[i]) % 4)
                decoded[part_name] = json.loads(_b64.urlsafe_b64decode(parts[i] + padding))
            except Exception as exc:
                decoded[part_name] = f"decode error: {exc}"
        return json.dumps(decoded)

    # ── credential_check ──────────────────────────────────────────────────────
    if tool_name == "credential_check":
        from aespa.services.scanner import _make_scanner_client, REQUEST_TIMEOUT
        from aespa.services import traffic as traffic_svc

        cred_url = str(tool_input.get("url") or base_url)
        scope_err = check_scope(cred_url, site_id, run_id)
        if scope_err:
            return f"[SCOPE BLOCK] {scope_err}"

        method = str(tool_input.get("method") or "POST").upper()
        candidates = tool_input.get("candidates") or []
        username_field = str(tool_input.get("username_field") or "username")
        password_field = str(tool_input.get("password_field") or "password")
        req_headers = dict(tool_input.get("headers") or {})
        success_statuses = set(tool_input.get("success_statuses") or [200, 201, 302])

        results = []
        timeout = _get_alice_timeout(run_id)

        async with _make_scanner_client(
            cookies={},
            headers={"User-Agent": "Mozilla/5.0 (compatible; ALICE/1.0)"},
            timeout=timeout,
            follow_redirects=False,
            verify=False,
            event_hooks=traffic_svc.make_httpx_hooks(run_id, username="alice"),
        ) as hx:
            for cand in candidates[:20]:
                body = {
                    username_field: cand.get("username", ""),
                    password_field: cand.get("password", ""),
                }
                try:
                    if "application/json" in req_headers.get("Content-Type", ""):
                        resp = await hx.request(method, cred_url, json=body, headers=req_headers)
                    else:
                        resp = await hx.request(method, cred_url, data=body, headers=req_headers)
                    success = resp.status_code in success_statuses
                    results.append({
                        "username": cand.get("username"),
                        "password": cand.get("password"),
                        "status": resp.status_code,
                        "success": success,
                        "location": resp.headers.get("location", ""),
                        "set_cookie": resp.headers.get("set-cookie", "")[:200],
                        "body_excerpt": resp.text[:300],
                    })
                except Exception as exc:
                    results.append({"username": cand.get("username"), "error": str(exc)})

        hits = [r for r in results if r.get("success")]
        summary = f"{len(hits)}/{len(results)} succeeded"
        return json.dumps({"summary": summary, "results": results[:20]}, default=str)

    # ── register_account ──────────────────────────────────────────────────────
    if tool_name == "register_account":
        from aespa.services.scanner import (
            _make_scanner_client, REQUEST_TIMEOUT,
            _session_label, _record_session, _mark_session_pending,
        )
        from aespa.services import traffic as traffic_svc
        import secrets as _secrets

        reg_url = str(tool_input.get("url") or base_url)
        scope_err = check_scope(reg_url, site_id, run_id)
        if scope_err:
            return f"[SCOPE BLOCK] {scope_err}"

        method = str(tool_input.get("method") or "POST").upper()
        body_format = str(tool_input.get("body_format") or "json")
        username_field = str(tool_input.get("username_field") or "username")
        email_field = str(tool_input.get("email_field") or "email")
        password_field = str(tool_input.get("password_field") or "password")
        store_as = tool_input.get("store_as") or _session_label("alice_user", {})
        rand_suffix = _secrets.token_hex(4)
        req_headers = dict(tool_input.get("headers") or {})
        extra_fields = dict(tool_input.get("extra_fields") or {})

        body: dict = {**extra_fields}
        if tool_input.get("include_username", True):
            body[username_field] = f"alice_test_{rand_suffix}"
        if tool_input.get("include_email", True):
            body[email_field] = f"alice_{rand_suffix}@pentest.invalid"
        body[password_field] = f"AliceTest1!{rand_suffix}"

        success_statuses = set(tool_input.get("success_statuses") or [200, 201])
        timeout = _get_alice_timeout(run_id)

        async with _make_scanner_client(
            cookies={},
            headers={"User-Agent": "Mozilla/5.0 (compatible; ALICE/1.0)"},
            timeout=timeout,
            follow_redirects=True,
            verify=False,
            event_hooks=traffic_svc.make_httpx_hooks(run_id, username="alice"),
        ) as hx:
            try:
                if body_format == "json":
                    resp = await hx.request(method, reg_url, json=body, headers=req_headers)
                else:
                    resp = await hx.request(method, reg_url, data=body, headers=req_headers)
                success = resp.status_code in success_statuses
                session_data: dict = {
                    "label": store_as,
                    "kind": "cookie",
                    "username": body.get(username_field) or body.get(email_field),
                    "source": "register_account tool",
                    "extra_headers": {},
                    "cookies": dict(resp.cookies),
                }
                if success:
                    _record_session(run_id, label=store_as, session_data=session_data, source="alice_register")
                    _mark_session_pending(store_as)
                return json.dumps({
                    "success": success,
                    "status": resp.status_code,
                    "store_as": store_as if success else None,
                    "body_excerpt": resp.text[:500],
                }, default=str)
            except Exception as exc:
                return f"Registration failed: {exc}"

    # ── agent_dispatch ────────────────────────────────────────────────────────
    if tool_name == "agent_dispatch":
        from aespa.services.scanner import dispatch_specialist_agent

        attack_class = str(tool_input.get("attack_class") or "")
        target_url = str(tool_input.get("target_url") or base_url)
        rationale = str(tool_input.get("rationale") or "")
        priority = int(tool_input.get("priority") or 7)

        try:
            agent_id = dispatch_specialist_agent(
                run_id=run_id,
                attack_class=attack_class,
                target_url=target_url,
                rationale=rationale,
                priority=priority,
            )
            if agent_id:
                return f"Specialist agent {agent_id} dispatched for {attack_class} on {target_url}."
            return f"Specialist agent for {attack_class} was not dispatched (gated by policy or at capacity)."
        except Exception as exc:
            return f"agent_dispatch error: {exc}"

    # ── browser ───────────────────────────────────────────────────────────────
    if tool_name == "browser":
        from aespa.services.scanner import _make_scanner_client
        from aespa.services import traffic as traffic_svc

        url = str(tool_input.get("url") or base_url)

        scope_err = check_scope(url, site_id, run_id)
        if scope_err:
            return f"[SCOPE BLOCK] {scope_err}"

        timeout = _get_alice_timeout(run_id)
        async with _make_scanner_client(
            cookies={},
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
            timeout=timeout,
            follow_redirects=True,
            verify=False,
            event_hooks=traffic_svc.make_httpx_hooks(run_id, username="alice"),
        ) as hx:
            try:
                resp = await hx.get(url)
                body = resp.text[:8192]
                return (
                    f"Page: {url}\n"
                    f"Status: {resp.status_code}\n"
                    f"Headers: {dict(resp.headers)}\n"
                    f"Body ({len(resp.text)} chars):\n{body}"
                )
            except Exception as exc:
                return f"Browser fetch failed: {exc}"

    return f"Tool '{tool_name}' is not supported in the A.L.I.C.E. context."


def _summarize_content(content: object, max_len: int = 600) -> str:
    """Return a JSON-serializable, truncated text representation of a message content value."""
    if isinstance(content, str):
        return (content[:max_len] + f"\n…[{len(content) - max_len} more chars]") if len(content) > max_len else content

    if not isinstance(content, list):
        try:
            s = str(content)
            return (s[:max_len] + "…") if len(s) > max_len else s
        except Exception:
            return "[non-serializable]"

    parts: list[str] = []
    for item in content:
        t = item.get("type", "unknown") if isinstance(item, dict) else getattr(item, "type", "unknown")
        if t == "text":
            text = (item.get("text", "") if isinstance(item, dict) else getattr(item, "text", "")) or ""
            if text:
                parts.append(str(text)[:300])
        elif t == "tool_use":
            name = (item.get("name", "") if isinstance(item, dict) else getattr(item, "name", "")) or ""
            inp = (item.get("input", {}) if isinstance(item, dict) else getattr(item, "input", {})) or {}
            try:
                inp_str = json.dumps(inp)[:200]
            except Exception:
                inp_str = str(inp)[:200]
            parts.append(f"[tool_call: {name}] {inp_str}")
        elif t == "tool_result":
            tc = (item.get("content", "") if isinstance(item, dict) else getattr(item, "content", "")) or ""
            if isinstance(tc, list):
                tc = " ".join(
                    (c.get("text", "") if isinstance(c, dict) else getattr(c, "text", "")) or ""
                    for c in tc
                )
            parts.append(f"[tool_result] {str(tc)[:300]}")
        elif t == "thinking":
            think = (item.get("thinking", "") if isinstance(item, dict) else getattr(item, "thinking", "")) or ""
            if think:
                parts.append(f"[thinking] {str(think)[:100]}…")
        else:
            try:
                s = json.dumps(item) if isinstance(item, dict) else str(item)
                parts.append(f"[{t}] {s[:100]}")
            except Exception:
                parts.append(f"[{t}]")

    combined = "\n".join(parts)
    return (combined[:max_len] + "\n…[truncated]") if len(combined) > max_len else combined


def _build_step_messages(messages: list[dict], max_msgs: int = 4) -> list[dict]:
    """Serialize the last N messages into a JSON-safe list for step_llm_call events."""
    result = []
    for m in messages[-max_msgs:]:
        role = m.get("role", "")
        content = m.get("content", "")
        result.append({"role": role, "content": _summarize_content(content)})
    return result


async def run_alice_turn_stream(
    run_id: int,
    user_instruction: str,
    history: list[dict],
) -> AsyncGenerator[str, None]:
    """Execute an interactive penetration testing turn for A.L.I.C.E. with streaming response.

    Runs a proper multi-turn agentic loop: each LLM response is checked for
    tool_use blocks, those tools are executed, and the results are fed back into
    the next turn.  Text blocks are streamed immediately as message_chunk SSE
    events.  The loop terminates when the model calls `done`, when ALICE_MAX_STEPS
    is reached, or when a scope violation is detected.
    """
    log.info("ALICE streaming turn started for run_id=%s instruction=%r", run_id, user_instruction)

    # 1. Establish configuration and site parameters
    with Session(get_engine()) as s:
        run = s.get(TestRun, run_id)
        if run is None:
            raise ValueError(f"TestRun {run_id} not found")
        site = s.get(Site, run.site_id)
        llm_cfg = get_llm_config_for_run(s, run)
        if llm_cfg is None:
            raise RuntimeError("No LLM configuration configured in Settings.")

        site_id = site.id
        base_url = str(site.base_url or "").strip()

    # Yield initial thinking chunk immediately (0ms time-to-first-event!)
    yield f"data: {json.dumps({'type': 'thinking_chunk', 'delta': '[A.L.I.C.E. Initializing] Mapped target sitemap and active scan configuration...\n'})}\n\n"
    await asyncio.sleep(0.01)

    # 2. Scope compliance checks on user directive
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
                        warning_msg = f"I cannot perform testing on '{clean_url}' because it is outside the authorized scope. {scope_error}"
                        yield f"data: {json.dumps({'type': 'warning', 'message': warning_msg})}\n\n"
                        done_msg = warning_msg
                        yield f"data: {json.dumps({'type': 'done', 'thought': '[A.L.I.C.E. Boundary Violation]', 'message': done_msg})}\n\n"
                        return
            except Exception:
                pass

    yield f"data: {json.dumps({'type': 'thinking_chunk', 'delta': 'Scope compliance verified. Starting agentic assessment loop...\n'})}\n\n"
    await asyncio.sleep(0.01)

    # 3. Build system prompt and initial message list
    system_message = ALICE_SYSTEM_PROMPT.format(
        user_directive=user_instruction,
        base_url=base_url,
    )

    # Convert conversation history to Anthropic-format messages.
    # History items from the chat UI have sender/text; convert to role/content.
    messages: list[dict] = []
    for h in history:
        sender = h.get("sender")
        text = h.get("text", "")
        if sender and text:
            role = "user" if sender == "user" else "assistant"
            messages.append({"role": role, "content": text})

    # Append the current instruction as the latest user message.
    messages.append({"role": "user", "content": user_instruction})

    alice_tools = _get_alice_tools()

    accumulated_thought = ""
    accumulated_message = ""
    step_count = 0
    consecutive_text_only = 0

    # 4. Agentic loop
    try:
        while step_count < ALICE_MAX_STEPS:
            step_count += 1

            yield f"data: {json.dumps({'type': 'thinking_chunk', 'delta': f'[Step {step_count}] Calling LLM...\n'})}\n\n"
            try:
                yield f"data: {json.dumps({'type': 'step_llm_call', 'step': step_count, 'messages': _build_step_messages(messages)})}\n\n"
            except Exception:
                pass

            try:
                content_blocks, stop_reason, raw_content = await llm_svc._call_with_tools(
                    llm_cfg, system_message, messages, tools=alice_tools
                )
            except Exception as exc:
                log.exception("ALICE agentic loop: LLM call failed at step %d", step_count)
                err = f"LLM error at step {step_count}: {exc}"
                yield f"data: {json.dumps({'type': 'message_chunk', 'delta': f'\n\n⚠️ {err}'})}\n\n"
                break

            # Append assistant turn to the growing conversation
            messages.append({"role": "assistant", "content": raw_content})

            # Extract text and tool blocks
            tool_use_blocks = [b for b in content_blocks if b.get("type") == "tool_use"]
            text_blocks = [b for b in content_blocks if b.get("type") == "text" and b.get("text")]
            thinking_blocks = [b for b in content_blocks if b.get("type") == "thinking" and b.get("thinking")]

            # Stream thinking blocks (Claude extended thinking)
            for tb in thinking_blocks:
                think_text = tb.get("thinking") or ""
                if think_text:
                    accumulated_thought += think_text
                    yield f"data: {json.dumps({'type': 'thinking_chunk', 'delta': think_text})}\n\n"
                    await asyncio.sleep(0)

            # Stream text blocks
            import re as _re
            for tb in text_blocks:
                text_content = tb.get("text") or ""
                if not text_content:
                    continue

                # Parse out <thinking>...</thinking> from text if model embeds it there
                think_match = _re.search(r"<thinking>(.*?)</thinking>", text_content, _re.DOTALL)
                if think_match:
                    think_part = think_match.group(1).strip()
                    outer_text = _re.sub(r"<thinking>.*?</thinking>", "", text_content, flags=_re.DOTALL).strip()
                    if think_part:
                        accumulated_thought += think_part
                        yield f"data: {json.dumps({'type': 'thinking_chunk', 'delta': think_part})}\n\n"
                    if outer_text:
                        if accumulated_message and not accumulated_message.endswith("\n"):
                            accumulated_message += "\n\n"
                            yield f"data: {json.dumps({'type': 'message_chunk', 'delta': '\n\n'})}\n\n"
                        accumulated_message += outer_text
                        yield f"data: {json.dumps({'type': 'message_chunk', 'delta': outer_text})}\n\n"
                else:
                    if accumulated_message and not accumulated_message.endswith("\n"):
                        accumulated_message += "\n\n"
                        yield f"data: {json.dumps({'type': 'message_chunk', 'delta': '\n\n'})}\n\n"
                    accumulated_message += text_content
                    yield f"data: {json.dumps({'type': 'message_chunk', 'delta': text_content})}\n\n"
                await asyncio.sleep(0)

            # Handle no tool use (text-only turn)
            if not tool_use_blocks:
                consecutive_text_only += 1
                if consecutive_text_only >= 3:
                    log.warning("ALICE: %d consecutive text-only turns; ending loop", consecutive_text_only)
                    break
                # Nudge the model back to using tools
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "text",
                        "text": (
                            "Your previous response did not call a tool. "
                            "Please continue by calling exactly one tool now — "
                            "http_request, context_tool, write_finding, forge_jwt, "
                            "decode_jwt, credential_check, browser, agent_dispatch, or done."
                        ),
                    }],
                })
                continue

            consecutive_text_only = 0

            # Execute each tool call
            tool_results = []
            session_done = False

            for block in tool_use_blocks:
                tool_name = block.get("name") or ""
                tool_input = block.get("input") or {}
                tool_use_id = block.get("id") or ""

                if tool_name == "done":
                    summary = str(tool_input.get("summary") or "Assessment complete.")
                    log.info("ALICE done at step %d: %s", step_count, summary[:200])
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": "Assessment complete.",
                    })
                    session_done = True
                    break

                yield f"data: {json.dumps({'type': 'thinking_chunk', 'delta': f'[Step {step_count}] Executing tool: {tool_name}\n'})}\n\n"
                try:
                    tool_input_safe = json.loads(json.dumps(tool_input, default=str))
                    yield f"data: {json.dumps({'type': 'step_tool_call', 'step': step_count, 'tool': tool_name, 'input': tool_input_safe})}\n\n"
                except Exception:
                    pass

                try:
                    result_str = await _execute_alice_tool(
                        run_id=run_id,
                        llm_cfg=llm_cfg,
                        base_url=base_url,
                        site_id=site_id,
                        tool_name=tool_name,
                        tool_input=tool_input,
                        step=step_count,
                    )
                except Exception as exc:
                    log.warning("ALICE tool %r step %d failed: %s", tool_name, step_count, exc)
                    result_str = f"Tool execution error: {exc}"

                # Cap result length to avoid blowing up context
                if len(result_str) > 16000:
                    omitted = len(result_str) - 16000
                    result_str = result_str[:16000] + f"\n[{omitted} chars omitted]"

                yield f"data: {json.dumps({'type': 'thinking_chunk', 'delta': f'[Step {step_count}] Tool result ({len(result_str)} chars)\n'})}\n\n"
                try:
                    result_preview = result_str[:3000] + (f"\n…[{len(result_str) - 3000} more chars]" if len(result_str) > 3000 else "")
                    yield f"data: {json.dumps({'type': 'step_tool_result', 'step': step_count, 'tool': tool_name, 'result': result_preview})}\n\n"
                except Exception:
                    pass

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": result_str,
                })

            if tool_results:
                messages.append({"role": "user", "content": tool_results})

            if session_done:
                break

    except Exception as exc:
        log.exception("ALICE agentic loop failed")
        err_msg = f"I encountered an error in the agentic loop: {exc}"
        yield f"data: {json.dumps({'type': 'message_chunk', 'delta': err_msg})}\n\n"
        accumulated_message += err_msg

    # 5. Emit done event
    yield f"data: {json.dumps({'type': 'done', 'thought': accumulated_thought.strip(), 'message': accumulated_message.strip()})}\n\n"


async def run_alice_turn(run_id: int, user_instruction: str, history: list[dict]) -> dict[str, Any]:
    """Execute a single interactive penetration testing turn for A.L.I.C.E.

    Backwards-compatible wrapper that consumes run_alice_turn_stream and returns
    the final dictionary.
    """
    thought = ""
    message = ""
    status = "complete"

    async for sse_line in run_alice_turn_stream(run_id, user_instruction, history):
        if sse_line.startswith("data: "):
            try:
                data = json.loads(sse_line[6:].strip())
                if data.get("type") == "done":
                    thought = data.get("thought", "")
                    message = data.get("message", "")
                elif data.get("type") == "warning":
                    status = "warning"
            except Exception:
                pass

    return {
        "thought_process": thought or "[ALICE Pentest Coordinator Turn Summary]\nCompleted Turn.",
        "message": message or "I have completed the assessment step.",
        "status": status,
    }
