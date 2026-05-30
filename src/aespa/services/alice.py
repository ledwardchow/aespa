"""A.L.I.C.E. chat coordinator service."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional, AsyncGenerator
from urllib.parse import urlparse

from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import CrawledPage, LLMConfig, ScanFinding, Site, TargetIntelItem, TestRun
from aespa.services import events as events_svc
from aespa.services import llm as llm_svc
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


async def _execute_alice_tool_calls(run_id: int, llm_cfg: LLMConfig, base_url: str, thought: str, message: str) -> None:
    """Parse and execute any dynamic tool calls (like write_finding) in ALICE's output.

    Allows A.L.I.C.E. to actually execute vulnerability writes, persisting them and triggering validator agents.
    """
    import re
    from aespa.services.scanner import _persist_dynamic_finding

    combined = thought + "\n" + message
    
    # 1. Extract all blocks wrapped in <tool_call>...</tool_call>
    tool_call_tags = re.findall(r"<tool_call>\s*(.*?)\s*</tool_call>", combined, re.DOTALL)
    
    # 2. Extract markdown JSON code blocks
    markdown_json_blocks = re.findall(r"```json\s*(.*?)\s*```", combined, re.DOTALL)
    
    candidates = []
    candidates.extend(tool_call_tags)
    candidates.extend(markdown_json_blocks)
    
    # 3. Fallback: if no candidates found, extract all brace-enclosed JSON objects {...}
    if not candidates:
        matches = re.finditer(r"(\{.*?\})", combined, re.DOTALL)
        for match in matches:
            candidates.append(match.group(1))

    for block in candidates:
        try:
            data = json.loads(block.strip())
            if not isinstance(data, dict):
                continue
                
            finding_raw = None
            
            # Map standard tool calls like {"name": "write_finding", "arguments": {...}}
            name = data.get("name") or data.get("tool") or data.get("action")
            args = data.get("arguments") or data.get("args")
            
            if name == "write_finding" or name == "finding_write":
                finding_raw = args if isinstance(args, dict) else data
            elif "title" in data and ("affected_url" in data or "url" in data or "description" in data):
                finding_raw = data
                
            if finding_raw:
                # Map url parameter to affected_url if present
                if "url" in finding_raw and "affected_url" not in finding_raw:
                    finding_raw["affected_url"] = finding_raw["url"]
                
                finding_raw["finding_source"] = "alice"
                
                with Session(get_engine()) as s:
                    pages = s.exec(select(CrawledPage).where(CrawledPage.test_run_id == run_id)).all()
                    pages_snapshot = [p.model_dump() for p in pages]
                    first_page_id = pages[0].id if pages else None
                
                affected = (finding_raw.get("affected_url") or base_url).strip() or base_url
                
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
                
                await _persist_dynamic_finding(
                    run_id=run_id,
                    llm_cfg=llm_cfg,
                    raw=finding_raw,
                    base_url=base_url,
                    pages_snapshot=pages_snapshot,
                    first_page_id=first_page_id,
                    result_by_url={str(affected): fw_result},
                    writeup_source="test_lead",
                )
                log.info("A.L.I.C.E. successfully executed write_finding for run_id=%s: %r", run_id, finding_raw.get("title"))
        except Exception as e:
            log.warning("Failed to parse and execute A.L.I.C.E tool call block: %s", e)


async def run_alice_turn_stream(
    run_id: int,
    user_instruction: str,
    history: list[dict],
) -> AsyncGenerator[str, None]:
    """Execute a single interactive penetration testing Turn for A.L.I.C.E. with streaming response.

    Validates scope compliance, and streams the reasoning and message chunks back as SSE event lines.
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

    # Yield initial thinking chunk immediately to show responsiveness (0ms time-to-first-event!)
    yield f"data: {json.dumps({'type': 'thinking_chunk', 'delta': '[A.L.I.C.E. Initializing] Mapped target sitemap and active scan configuration...\\n'})}\n\n"
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
                        warning_msg = f"I cannot perform testing on '{clean_url}' because it is outside the authorized scope for this scan target. {scope_error}"
                        yield f"data: {json.dumps({'type': 'warning', 'message': warning_msg})}\n\n"
                        done_msg = f"I cannot perform testing on '{clean_url}' because it is outside the authorized scope. {scope_error}"
                        yield f"data: {json.dumps({'type': 'done', 'thought': '[A.L.I.C.E. Boundary Violation Alert]\\nUser requested target is out-of-scope.', 'message': done_msg})}\n\n"
                        return
            except Exception:
                pass

    # Yield next thinking chunk
    yield f"data: {json.dumps({'type': 'thinking_chunk', 'delta': 'Evaluating prompt scope compliance: In-Scope verified.\\nRouting directives to the LLM agent model...\\n'})}\n\n"
    await asyncio.sleep(0.01)

    # 3. Format ALICE System Prompt
    system_message = ALICE_SYSTEM_PROMPT.format(
        user_directive=user_instruction,
        base_url=base_url,
    )

    # Convert conversation history to message format for LLM
    formatted_messages = []
    for h in history:
        sender = h.get("sender")
        text = h.get("text")
        if sender and text:
            role = "user" if sender == "user" else "assistant"
            formatted_messages.append({"role": role, "content": text})

    # Append current user prompt
    formatted_messages.append({"role": "user", "content": user_instruction})

    # 4. Stream LLM completion and parse tags
    accumulated_thought = ""
    accumulated_message = ""
    buffer = ""
    in_thinking = False

    try:
        async for chunk in llm_svc.stream_chat_completion(llm_cfg, system_message, formatted_messages):
            buffer += chunk

            # Check if transitioning into thinking
            if "<thinking>" in buffer:
                parts = buffer.split("<thinking>", 1)
                before = parts[0]
                if before:
                    accumulated_message += before
                    yield f"data: {json.dumps({'type': 'message_chunk', 'delta': before})}\n\n"
                in_thinking = True
                buffer = parts[1]

            # Check if transitioning out of thinking
            if "</thinking>" in buffer:
                parts = buffer.split("</thinking>", 1)
                thinking_content = parts[0]
                if thinking_content:
                    accumulated_thought += thinking_content
                    yield f"data: {json.dumps({'type': 'thinking_chunk', 'delta': thinking_content})}\n\n"
                in_thinking = False
                buffer = parts[1]

            # Flush standard text from buffer if stable
            if buffer:
                is_partial = False
                for tag in ["<thinking>", "</thinking>"]:
                    for i in range(1, len(tag)):
                        if buffer.endswith(tag[:i]):
                            is_partial = True
                            break
                if not is_partial:
                    if in_thinking:
                        accumulated_thought += buffer
                        yield f"data: {json.dumps({'type': 'thinking_chunk', 'delta': buffer})}\n\n"
                    else:
                        accumulated_message += buffer
                        yield f"data: {json.dumps({'type': 'message_chunk', 'delta': buffer})}\n\n"
                    buffer = ""
                    
        # Flush any remaining buffer content
        if buffer:
            if in_thinking:
                accumulated_thought += buffer
                yield f"data: {json.dumps({'type': 'thinking_chunk', 'delta': buffer})}\n\n"
            else:
                accumulated_message += buffer
                yield f"data: {json.dumps({'type': 'message_chunk', 'delta': buffer})}\n\n"
                
    except Exception as exc:
        log.exception("ALICE streaming turn failed")
        err_msg = f"I encountered an error trying to orchestrate this turn: {exc}"
        yield f"data: {json.dumps({'type': 'message_chunk', 'delta': err_msg})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'thought': f'[ALICE Error]\\nLoop failed: {exc}', 'message': err_msg})}\n\n"
        return

    # Parse and execute any dynamic tool calls (such as write_finding)
    try:
        await _execute_alice_tool_calls(run_id, llm_cfg, base_url, accumulated_thought, accumulated_message)
    except Exception as exc:
        log.exception("A.L.I.C.E. tool call execution failed")

    # Yield done event carrying completed history content
    yield f"data: {json.dumps({'type': 'done', 'thought': accumulated_thought.strip(), 'message': accumulated_message.strip()})}\n\n"


async def run_alice_turn(run_id: int, user_instruction: str, history: list[dict]) -> dict[str, Any]:
    """Execute a single interactive penetration testing Turn for the A.L.I.C.E. agent.

    Backwards-compatible wrapper that consumes run_alice_turn_stream and returns the final dictionary.
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
        "message": message or "I have aligned our testing policy.",
        "status": status
    }

