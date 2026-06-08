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
from aespa.services.prompts.alice import ALICE_SYSTEM_PROMPT, ALICE_API_SYSTEM_PROMPT
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


def _select_session(
    session_vault: dict[str, dict],
    use_session_label: str | None,
) -> dict | None:
    """Resolve the session to authenticate a request with.

    Honors an explicit ``use_session`` label (including ``"anonymous"`` to opt
    out of stored credentials); otherwise falls back to the run's primary
    session — ``configured_primary`` if present, else the first non-anonymous
    entry in the vault.
    """
    if use_session_label:
        return session_vault.get(use_session_label)
    primary = session_vault.get("configured_primary")
    if primary is not None:
        return primary
    for session in session_vault.values():
        if session.get("kind") != "anonymous":
            return session
    return None


async def _execute_alice_tool(
    run_id: int,
    llm_cfg: LLMConfig,
    base_url: str,
    site_id: int,
    tool_name: str,
    tool_input: dict,
    step: int,
    session_vault: dict[str, dict] | None = None,
    scope_check_fn=None,    # Optional override: scope_check_fn(url) -> str | None
    context_tool_fn=None,   # Optional override: context_tool_fn(tool_name, args) -> dict
) -> str:
    """Execute a single ALICE tool call and return the result string."""
    session_vault = session_vault or {}

    # ── http_request ─────────────────────────────────────────────────────────
    if tool_name == "http_request":
        from aespa.services.scanner import (
            _make_scanner_client,
            REQUEST_TIMEOUT,
        )
        from aespa.services import traffic as traffic_svc

        _url = str(tool_input.get("url") or base_url)
        scope_err = scope_check_fn(_url) if scope_check_fn else check_scope(_url, site_id, run_id)
        if scope_err:
            return f"[SCOPE BLOCK] {scope_err}"

        method = str(tool_input.get("method") or "GET").upper()
        headers = dict(tool_input.get("headers") or {})
        body = tool_input.get("body")

        # Carry the run's stored authenticated session by default; an explicit
        # use_session label (e.g. "anonymous") overrides the selection.
        use_session_label = tool_input.get("use_session") if isinstance(tool_input.get("use_session"), str) else None
        selected = _select_session(session_vault, use_session_label)
        req_cookies = (selected or {}).get("cookies") or {}
        req_headers = {
            "User-Agent": "Mozilla/5.0 (compatible; ALICE/1.0)",
            **((selected or {}).get("extra_headers") or {}),
            **headers,
        }

        timeout = _get_alice_timeout(run_id)

        async with _make_scanner_client(
            cookies=req_cookies,
            headers=req_headers,
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
        ctx_tool = str(tool_input.get("tool") or "")
        ctx_args = tool_input.get("args") if isinstance(tool_input.get("args"), dict) else {}
        try:
            if context_tool_fn is not None:
                output = context_tool_fn(ctx_tool, ctx_args)
            else:
                from aespa.services.scanner import (
                    _load_findings_snapshot,
                    _run_thinking_context_tool,
                )
                with Session(get_engine()) as s:
                    pages = s.exec(select(CrawledPage).where(CrawledPage.test_run_id == run_id)).all()
                    pages_snapshot = [p.model_dump() for p in pages]
                output = _run_thinking_context_tool(
                    ctx_tool, ctx_args,
                    pages_snapshot=pages_snapshot,
                    findings_snapshot=_load_findings_snapshot(run_id),
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
            # Surface the new session to later steps in this same turn.
            session_vault[label] = {
                "label": label,
                "kind": "bearer",
                "cookies": {},
                "extra_headers": {"Authorization": f"Bearer {jwt_token}"},
            }
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
        scope_err = scope_check_fn(reg_url) if scope_check_fn else check_scope(reg_url, site_id, run_id)
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
                    # Surface the new session to later steps in this same turn.
                    session_vault[store_as] = {
                        "label": store_as,
                        "kind": "cookie",
                        "cookies": dict(resp.cookies),
                        "extra_headers": {},
                    }
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

        scope_err = scope_check_fn(url) if scope_check_fn else check_scope(url, site_id, run_id)
        if scope_err:
            return f"[SCOPE BLOCK] {scope_err}"

        use_session_label = tool_input.get("use_session") if isinstance(tool_input.get("use_session"), str) else None
        selected = _select_session(session_vault, use_session_label)
        req_cookies = (selected or {}).get("cookies") or {}

        timeout = _get_alice_timeout(run_id)
        async with _make_scanner_client(
            cookies=req_cookies,
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                **((selected or {}).get("extra_headers") or {}),
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

    # Load the per-run session vault so ALICE carries stored authenticated
    # sessions (configured credentials, registered/forged tokens) instead of
    # probing anonymously. Keyed by label for use_session selection.
    from aespa.services import scanner_sessions as session_svc
    try:
        session_vault = session_svc.load_session_vault(run_id)
    except Exception:
        log.warning("ALICE: failed to load session vault for run_id=%s", run_id, exc_info=True)
        session_vault = {}

    # Register run context so LLM calls attribute token usage to this run.
    llm_svc.set_run_context(run_id, lambda evt: events_svc.emit(run_id, evt))

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
                        session_vault=session_vault,
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
    llm_svc.clear_run_context()


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


# ── API-collection ALICE helpers ──────────────────────────────────────────────

def _check_api_scope(url: str, collection) -> str | None:
    """Host-level scope check for API collections (no DB read needed).

    Derives allowed hosts from the collection's ``base_url`` and ``servers``
    list.  Returns a rejection message or ``None`` if the URL is in scope.
    """
    from urllib.parse import urlparse as _up
    import json as _json

    parsed = _up(url)
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return None

    # Explicit scope_hosts list takes precedence when configured.
    explicit: list[str] = _json.loads(collection.scope_hosts or "[]")
    if explicit:
        if hostname not in explicit:
            allowed = ", ".join(explicit)
            return (
                f"Host '{hostname}' is outside the API collection scope "
                f"(allowed: {allowed})."
            )
        return None

    # Fall back to base_url host + any additional servers.
    base_host = (_up(collection.base_url).hostname or "").lower()
    server_hosts = [
        (_up(s).hostname or "").lower()
        for s in _json.loads(collection.servers or "[]")
        if s
    ]
    allowed_hosts = {h for h in [base_host, *server_hosts] if h}
    if allowed_hosts and hostname not in allowed_hosts:
        return (
            f"Host '{hostname}' is outside the API collection scope "
            f"(allowed: {', '.join(sorted(allowed_hosts))})."
        )
    return None


def _run_api_context_tool(
    collection_id: int,
    run_id: int,
    tool_name: str,
    args: dict,
) -> dict:
    """Handle context_tool calls for API test runs.

    Exposes ``endpoint_list``, ``endpoint_detail``, ``collection_info``, and
    ``finding_list`` instead of the crawl-oriented site_map / page_detail tools.
    """
    from aespa.models import ApiCollection, ApiCredential, ApiEndpoint
    from sqlmodel import select as _sel

    tool_name = (tool_name or "").strip()
    try:
        limit = max(1, min(200, int(args.get("limit") or 50)))
    except (TypeError, ValueError):
        limit = 50
    search = str(args.get("search") or "").lower()

    # ── endpoint_list ─────────────────────────────────────────────────────────
    if tool_name == "endpoint_list":
        method_filter = str(args.get("method") or "").upper()
        auth_filter = args.get("auth_required")
        scope_filter = args.get("in_scope")

        with Session(get_engine()) as s:
            query = _sel(ApiEndpoint).where(ApiEndpoint.collection_id == collection_id)
            if method_filter:
                query = query.where(ApiEndpoint.method == method_filter)
            if auth_filter is not None:
                query = query.where(ApiEndpoint.auth_required == bool(auth_filter))
            if scope_filter is not False:
                query = query.where(ApiEndpoint.in_scope == True)  # noqa: E712
            endpoints = list(s.exec(
                query.order_by(ApiEndpoint.path, ApiEndpoint.method)
            ).all())

        matches = []
        for ep in endpoints:
            if search:
                haystack = f"{ep.method} {ep.path} {ep.summary or ''} {ep.operation_id or ''}".lower()
                if search not in haystack:
                    continue
            try:
                tags = json.loads(ep.tags_json or "[]")
            except Exception:
                tags = []
            matches.append({
                "id": ep.id,
                "method": ep.method,
                "path": ep.path,
                "base_url": ep.base_url,
                "operation_id": ep.operation_id,
                "summary": ep.summary,
                "auth_required": ep.auth_required,
                "tags": tags,
                "can_test": ep.prereq_can_test,
                "can_test_auth": ep.prereq_can_test_auth,
            })

        return {
            "tool": "endpoint_list",
            "count": len(matches),
            "endpoints": matches[:limit],
            "truncated": len(matches) > limit,
        }

    # ── endpoint_detail ───────────────────────────────────────────────────────
    if tool_name == "endpoint_detail":
        ep_id = args.get("endpoint_id")
        method = str(args.get("method") or "").upper()
        path = str(args.get("path") or "")

        with Session(get_engine()) as s:
            ep = None
            if ep_id is not None:
                ep = s.get(ApiEndpoint, int(ep_id))
                if ep and ep.collection_id != collection_id:
                    ep = None
            if ep is None and method and path:
                ep = s.exec(
                    _sel(ApiEndpoint)
                    .where(ApiEndpoint.collection_id == collection_id)
                    .where(ApiEndpoint.method == method)
                    .where(ApiEndpoint.path == path)
                ).first()

        if ep is None:
            return {
                "tool": "endpoint_detail",
                "error": "endpoint not found",
                "hint": "Call endpoint_list first to get valid endpoint_id values.",
            }

        def _safe_json(val: str, default):
            try:
                return json.loads(val) if val else default
            except Exception:
                return default

        return {
            "tool": "endpoint_detail",
            "id": ep.id,
            "method": ep.method,
            "path": ep.path,
            "base_url": ep.base_url,
            "operation_id": ep.operation_id,
            "summary": ep.summary,
            "auth_required": ep.auth_required,
            "tags": _safe_json(ep.tags_json, []),
            "parameters": _safe_json(ep.parameters_json, []),
            "request_body_schema": _safe_json(ep.request_body_schema_json, {}),
            "response_schema": _safe_json(ep.response_schema_json, {}),
            "security": _safe_json(ep.security_json, []),
            "sample_request": _safe_json(ep.sample_request_json, {}),
            "prereq_notes": _safe_json(ep.prereq_notes, []),
            "can_test": ep.prereq_can_test,
            "can_test_auth": ep.prereq_can_test_auth,
        }

    # ── collection_info ───────────────────────────────────────────────────────
    if tool_name == "collection_info":
        with Session(get_engine()) as s:
            coll = s.get(ApiCollection, collection_id)
            if coll is None:
                return {"tool": "collection_info", "error": "collection not found"}
            creds = list(s.exec(
                _sel(ApiCredential).where(ApiCredential.collection_id == collection_id)
            ).all())

        def _safe_json(val, default):
            try:
                return json.loads(val) if val else default
            except Exception:
                return default

        return {
            "tool": "collection_info",
            "name": coll.name,
            "base_url": coll.base_url,
            "description": coll.description,
            "servers": _safe_json(coll.servers, []),
            "scope_hosts": _safe_json(coll.scope_hosts, []),
            "auth_summary": _safe_json(coll.auth_summary_json, {}),
            "readiness": _safe_json(coll.readiness_json, {}),
            "credentials": [
                {
                    "label": c.label or c.scheme,
                    "scheme": c.scheme,
                    "name": c.name,
                    "scope": c.scope,
                    "auth_endpoint": c.auth_endpoint,
                }
                for c in creds
            ],
        }

    # ── finding_list ──────────────────────────────────────────────────────────
    if tool_name == "finding_list":
        from aespa.services.scanner import _load_findings_snapshot
        findings = _load_findings_snapshot(run_id)
        severity = str(args.get("severity") or "").lower()
        matches = []
        for f in findings:
            if severity and str(f.get("severity") or "").lower() != severity:
                continue
            if search:
                haystack = json.dumps(f, default=str).lower()
                if search not in haystack:
                    continue
            matches.append(f)
        return {"tool": "finding_list", "count": len(matches), "findings": matches[:limit]}

    return {
        "tool": tool_name,
        "error": "unknown tool",
        "available_tools": ["endpoint_list", "endpoint_detail", "collection_info", "finding_list"],
    }


async def run_api_alice_turn_stream(
    api_run_id: int,
    user_instruction: str,
    history: list[dict],
) -> AsyncGenerator[str, None]:
    """Execute an interactive API security testing turn for A.L.I.C.E.

    Mirrors ``run_alice_turn_stream`` but operates against an ``ApiTestRun`` /
    ``ApiCollection`` instead of a ``TestRun`` / ``Site``.  The context_tool
    exposes the parsed endpoint inventory rather than crawled pages.
    """
    log.info("ALICE API turn started for api_run_id=%s instruction=%r", api_run_id, user_instruction)

    from aespa.models import ApiCollection, ApiTestRun
    from aespa.services.settings import get_llm_config_for_run

    with Session(get_engine()) as s:
        api_run = s.get(ApiTestRun, api_run_id)
        if api_run is None:
            raise ValueError(f"ApiTestRun {api_run_id} not found")
        collection = s.get(ApiCollection, api_run.collection_id)
        if collection is None:
            raise ValueError(f"ApiCollection {api_run.collection_id} not found")
        llm_cfg = get_llm_config_for_run(s, api_run)  # type: ignore[arg-type]
        if llm_cfg is None:
            raise RuntimeError("No LLM configuration configured in Settings.")
        collection_name = collection.name
        base_url = str(collection.base_url or "").strip()
        # Capture a snapshot so the closure below is not DB-session-bound.
        collection_id = collection.id
        collection_scope_hosts = collection.scope_hosts
        collection_servers = collection.servers

    # Load stored API credentials into the session vault so http_request
    # can carry authentication automatically.
    from aespa.models import ApiCredential
    from sqlmodel import select as _sel
    session_vault: dict[str, dict] = {}
    with Session(get_engine()) as s:
        creds = list(s.exec(
            _sel(ApiCredential).where(ApiCredential.collection_id == collection_id)
        ).all())
    for cred in creds:
        label = cred.label or cred.scheme
        entry: dict = {"label": label, "kind": cred.scheme, "cookies": {}, "extra_headers": {}}
        if cred.scheme in ("bearer", "apikey"):
            entry["extra_headers"] = {cred.name: f"Bearer {cred.value}" if cred.scheme == "bearer" else cred.value}
        elif cred.scheme == "header":
            entry["extra_headers"] = {cred.name: cred.value}
        elif cred.scheme == "cookie":
            entry["cookies"] = {cred.name: cred.value}
        elif cred.scheme == "basic":
            import base64 as _b64
            encoded = _b64.b64encode(cred.value.encode()).decode()
            entry["extra_headers"] = {"Authorization": f"Basic {encoded}"}
        session_vault[label] = entry
        # Mark the first credential as the default primary session.
        if "configured_primary" not in session_vault:
            session_vault["configured_primary"] = entry

    llm_svc.set_run_context(api_run_id, lambda evt: events_svc.emit(api_run_id, evt))

    # Scope-check closure uses a minimal copy of collection data (no DB session).
    import json as _json

    class _CollProxy:
        def __init__(self):
            self.base_url = base_url
            self.servers = collection_servers
            self.scope_hosts = collection_scope_hosts

    _coll_proxy = _CollProxy()
    _scope_fn = lambda url: _check_api_scope(url, _coll_proxy)  # noqa: E731
    _ctx_fn = lambda tool_name, args: _run_api_context_tool(collection_id, api_run_id, tool_name, args)  # noqa: E731

    yield f"data: {json.dumps({'type': 'thinking_chunk', 'delta': '[A.L.I.C.E. API Mode] Loading API collection endpoint inventory...\n'})}\n\n"
    await asyncio.sleep(0.01)

    # Build the system prompt.
    system_message = ALICE_API_SYSTEM_PROMPT.format(
        collection_name=collection_name,
        base_url=base_url,
        user_directive=user_instruction,
    )

    # Convert history to Anthropic-format messages.
    messages: list[dict] = []
    for h in history:
        sender = h.get("sender")
        text = h.get("text", "")
        if sender and text:
            role = "user" if sender == "user" else "assistant"
            messages.append({"role": role, "content": text})
    messages.append({"role": "user", "content": user_instruction})

    alice_tools = _get_alice_tools()
    accumulated_thought = ""
    accumulated_message = ""
    step_count = 0
    consecutive_text_only = 0

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
                log.exception("ALICE API loop: LLM call failed at step %d", step_count)
                err = f"LLM error at step {step_count}: {exc}"
                yield f"data: {json.dumps({'type': 'message_chunk', 'delta': f'\n\n⚠️ {err}'})}\n\n"
                break

            messages.append({"role": "assistant", "content": raw_content})

            tool_use_blocks = [b for b in content_blocks if b.get("type") == "tool_use"]
            text_blocks = [b for b in content_blocks if b.get("type") == "text" and b.get("text")]
            thinking_blocks = [b for b in content_blocks if b.get("type") == "thinking" and b.get("thinking")]

            for tb in thinking_blocks:
                think_text = tb.get("thinking") or ""
                if think_text:
                    accumulated_thought += think_text
                    yield f"data: {json.dumps({'type': 'thinking_chunk', 'delta': think_text})}\n\n"
                    await asyncio.sleep(0)

            import re as _re
            for tb in text_blocks:
                text_content = tb.get("text") or ""
                if not text_content:
                    continue
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

            if not tool_use_blocks:
                consecutive_text_only += 1
                if consecutive_text_only >= 3:
                    log.warning("ALICE API: %d consecutive text-only turns; ending loop", consecutive_text_only)
                    break
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "text",
                        "text": (
                            "Your previous response did not call a tool. "
                            "Please continue by calling exactly one tool now — "
                            "http_request, context_tool, write_finding, forge_jwt, "
                            "decode_jwt, credential_check, register_account, agent_dispatch, or done."
                        ),
                    }],
                })
                continue

            consecutive_text_only = 0
            tool_results = []
            session_done = False

            for block in tool_use_blocks:
                tool_name = block.get("name") or ""
                tool_input = block.get("input") or {}
                tool_use_id = block.get("id") or ""

                if tool_name == "done":
                    summary = str(tool_input.get("summary") or "Assessment complete.")
                    log.info("ALICE API done at step %d: %s", step_count, summary[:200])
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
                        run_id=api_run_id,
                        llm_cfg=llm_cfg,
                        base_url=base_url,
                        site_id=-1,             # unused — scope_check_fn overrides
                        tool_name=tool_name,
                        tool_input=tool_input,
                        step=step_count,
                        session_vault=session_vault,
                        scope_check_fn=_scope_fn,
                        context_tool_fn=_ctx_fn,
                    )
                except Exception as exc:
                    log.warning("ALICE API tool %r step %d failed: %s", tool_name, step_count, exc)
                    result_str = f"Tool execution error: {exc}"

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
        log.exception("ALICE API agentic loop failed")
        err_msg = f"I encountered an error in the agentic loop: {exc}"
        yield f"data: {json.dumps({'type': 'message_chunk', 'delta': err_msg})}\n\n"
        accumulated_message += err_msg

    yield f"data: {json.dumps({'type': 'done', 'thought': accumulated_thought.strip(), 'message': accumulated_message.strip()})}\n\n"
    llm_svc.clear_run_context()
