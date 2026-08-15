"""Adapter for the externally installed Codex app-server.

Codex is deliberately kept outside AESPA's Python dependencies.  The adapter
speaks the app-server JSONL protocol over stdin/stdout and keeps authentication
in the user's normal Codex CLI home.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import re
import shutil
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from aespa.config import get_settings
from aespa.models import LLMConfig

log = logging.getLogger("aespa.llm.codex")

TURN_TIMEOUT_S = 600.0
_INTERNAL_ACTION_ITEM_TYPES = {
    "collabAgentToolCall",
    "commandExecution",
    "fileChange",
    "imageGeneration",
    "imageView",
    "mcpToolCall",
    "sleep",
    "webSearch",
}
_ENV_ALLOWLIST = (
    "PATH",
    "HOME",
    "USERPROFILE",
    "APPDATA",
    "LOCALAPPDATA",
    "CODEX_HOME",
    "LANG",
    "LC_ALL",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "NODE_EXTRA_CA_CERTS",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "NO_PROXY",
)


class CodexUnavailableError(RuntimeError):
    """Codex is not installed, signed in, or compatible with AESPA."""


class CodexQuotaError(RuntimeError):
    """The ChatGPT/Codex allowance has been exhausted."""

    def __init__(
        self,
        message: str,
        *,
        reset_at: datetime | None = None,
        snapshot: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.reset_at = reset_at
        self.snapshot = snapshot or {}


class CodexRateLimitError(CodexQuotaError):
    """A transient upstream Codex rate limit that may succeed after a delay."""

    def __init__(
        self,
        message: str,
        *,
        retry_after_s: float | None = None,
        reset_at: datetime | None = None,
        snapshot: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, reset_at=reset_at, snapshot=snapshot)
        self.retry_after_s = retry_after_s


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _extract_reset_at(value: Any) -> datetime | None:
    """Extract the earliest allowance reset time from app-server data."""
    values: list[Any] = []

    def walk(item: Any) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                if str(key).lower() in {"resetsat", "reset_at", "resetat"}:
                    values.append(child)
                else:
                    walk(child)
        elif isinstance(item, list):
            for child in item:
                walk(child)

    walk(value)
    candidates: list[datetime] = []
    for raw in values:
        try:
            if isinstance(raw, (int, float)):
                candidates.append(datetime.fromtimestamp(float(raw), tz=timezone.utc))
            elif isinstance(raw, str):
                text = raw.strip().replace("Z", "+00:00")
                parsed = datetime.fromisoformat(text)
                candidates.append(
                    parsed.replace(tzinfo=timezone.utc)
                    if parsed.tzinfo is None
                    else parsed.astimezone(timezone.utc)
                )
        except (TypeError, ValueError, OverflowError):
            continue
    return min(candidates) if candidates else None


def _extract_retry_after(value: Any) -> float | None:
    """Extract a retry delay from structured or human-readable Codex errors."""
    if isinstance(value, dict):
        for key, raw in value.items():
            normalized = str(key).lower().replace("_", "")
            if normalized in {"retryafterms", "retryinms"}:
                try:
                    return max(0.0, float(raw) / 1000.0)
                except (TypeError, ValueError):
                    pass
            if normalized in {"retryafter", "retryin", "retryafterseconds"}:
                try:
                    return max(0.0, float(raw))
                except (TypeError, ValueError):
                    pass
            nested = _extract_retry_after(raw)
            if nested is not None:
                return nested
    elif isinstance(value, list):
        for item in value:
            nested = _extract_retry_after(item)
            if nested is not None:
                return nested

    text = json.dumps(value, default=str) if not isinstance(value, str) else value
    match = re.search(
        r"(?:try again|retry)\s+in\s+(\d+(?:\.\d+)?)\s*(milliseconds?|ms|seconds?|secs?|s)\b",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    amount = float(match.group(1))
    unit = match.group(2).lower()
    return (
        amount / 1000.0 if unit.startswith("ms") or unit.startswith("mill") else amount
    )


def _is_rate_limit_error(value: Any) -> bool:
    text = json.dumps(value, default=str).lower()
    return any(
        marker in text
        for marker in (
            "rate limit reached",
            "rate_limit_reached",
            "ratelimitreached",
            "tokens per min",
            "tokens per minute",
            "too many requests",
        )
    )


def _rate_limit_error_has_full_window(value: Any) -> bool:
    """Recognize Codex's human-readable ``Limit … Used …`` error details."""
    text = json.dumps(value, default=str)
    match = re.search(
        r"\blimit\s+([\d,]+).*?\bused\s+([\d,]+)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return False
    try:
        return float(match.group(2).replace(",", "")) >= float(
            match.group(1).replace(",", "")
        )
    except (TypeError, ValueError):
        return False


def _rate_limit_is_exhausted(value: Any) -> bool:
    """Return true when an app-server rate-limit snapshot has no capacity."""
    exhausted = False

    def number(raw: Any) -> float | None:
        if isinstance(raw, bool):
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    def walk(item: Any) -> None:
        nonlocal exhausted
        if exhausted:
            return
        if isinstance(item, dict):
            limits: list[float] = []
            used: list[float] = []
            remaining: list[float] = []
            for key, child in item.items():
                normalized = str(key).lower().replace("_", "")
                if (
                    normalized
                    in {
                        "ratelimitreached",
                        "limitreached",
                        "usagelimitexceeded",
                        "exhausted",
                    }
                    and child is True
                ):
                    exhausted = True
                    return
                if normalized in {
                    "usedpercent",
                    "usagepercent",
                    "utilizationpercent",
                }:
                    try:
                        if float(child) >= 100:
                            exhausted = True
                            return
                    except (TypeError, ValueError):
                        pass
                if normalized in {
                    "limit",
                    "maxtokens",
                    "capacity",
                    "limittokens",
                    "tokenlimit",
                }:
                    parsed = number(child)
                    if parsed is not None and parsed > 0:
                        limits.append(parsed)
                if normalized in {
                    "used",
                    "usage",
                    "consumed",
                    "usedtokens",
                    "tokenusage",
                }:
                    parsed = number(child)
                    if parsed is not None:
                        used.append(parsed)
                if normalized in {
                    "remaining",
                    "remainingtokens",
                    "tokensremaining",
                }:
                    parsed = number(child)
                    if parsed is not None:
                        remaining.append(parsed)
                if normalized == "remainingpercent":
                    try:
                        if float(child) <= 0:
                            exhausted = True
                            return
                    except (TypeError, ValueError):
                        pass
            if any(used_value >= limit for used_value in used for limit in limits):
                exhausted = True
                return
            if any(value <= 0 for value in remaining):
                exhausted = True
                return
            for child in item.values():
                walk(child)
        elif isinstance(item, list):
            for child in item:
                walk(child)

    walk(value)
    return exhausted


def _workspace() -> Path:
    root = Path(get_settings().data_dir) / "codex-workspaces"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _child_env() -> dict[str, str]:
    current = os.environ
    env = {key: current[key] for key in _ENV_ALLOWLIST if current.get(key)}
    env["PATH"] = current.get("PATH", os.defpath)
    return env


def resolve_executable(path: str | None = None) -> str | None:
    """Resolve a configured Codex executable or the user's PATH entry."""
    candidate = (path or "").strip()
    if candidate:
        resolved = Path(candidate).expanduser()
        if resolved.is_file() and os.access(resolved, os.X_OK):
            return str(resolved)
        return None
    return shutil.which("codex", path=_child_env().get("PATH"))


async def detect_installation(path: str | None = None) -> dict[str, Any]:
    executable = resolve_executable(path)
    if not executable:
        return {"installed": False, "executable": None, "version": None}
    try:
        proc = await asyncio.create_subprocess_exec(
            executable,
            "--version",
            cwd=str(_workspace()),
            env=_child_env(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
        version = (stdout or stderr).decode("utf-8", "replace").strip().splitlines()[0]
        if proc.returncode:
            raise RuntimeError(version or "Codex version command failed")
        return {"installed": True, "executable": executable, "version": version}
    except Exception as exc:
        return {
            "installed": True,
            "executable": executable,
            "version": None,
            "error": str(exc),
        }


@dataclass
class _Conversation:
    thread_id: str
    last_message_count: int
    pending_calls: dict[str, tuple[int, dict[str, Any]]] = field(default_factory=dict)
    events: asyncio.Queue[tuple[str, dict[str, Any]]] = field(
        default_factory=asyncio.Queue
    )
    text: list[str] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=dict)


class _JsonRpcClient:
    def __init__(self, executable: str):
        self.executable = executable
        self.process: asyncio.subprocess.Process | None = None
        self._reader_task: asyncio.Task | None = None
        self._stderr_task: asyncio.Task | None = None
        self._write_lock = asyncio.Lock()
        self._next_id = 1
        self._pending: dict[int, asyncio.Future] = {}
        self._notifications: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._conversations: dict[str, _Conversation] = {}
        self._stderr_tail: deque[str] = deque(maxlen=30)
        self.initialized = False

    async def start(self) -> None:
        if self.process and self.process.returncode is None:
            return
        self.process = await asyncio.create_subprocess_exec(
            self.executable,
            "app-server",
            "--listen",
            "stdio://",
            "--strict-config",
            cwd=str(_workspace()),
            env=_child_env(),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._reader_task = asyncio.create_task(self._read_stdout())
        self._stderr_task = asyncio.create_task(self._read_stderr())
        result = await self.request(
            "initialize",
            {
                "clientInfo": {
                    "name": "aespa",
                    "title": "AESPA",
                    "version": "0.1",
                },
                "capabilities": {"experimentalApi": True},
            },
        )
        await self.notify("initialized", {})
        self.initialized = True
        log.debug("Codex app-server initialized: %s", result)

    async def _read_stdout(self) -> None:
        assert self.process and self.process.stdout
        try:
            async for raw in self.process.stdout:
                try:
                    message = json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
                if "id" in message and ("result" in message or "error" in message):
                    future = self._pending.pop(int(message["id"]), None)
                    if future and not future.done():
                        if "error" in message:
                            future.set_exception(
                                CodexUnavailableError(str(message["error"]))
                            )
                        else:
                            future.set_result(message.get("result"))
                    continue
                params = message.get("params") or {}
                thread_id = str(params.get("threadId") or "")
                if message.get("method") == "item/tool/call" and thread_id:
                    conversation = self._conversations.get(thread_id)
                    if conversation is not None:
                        call_id = str(
                            params.get("callId")
                            or params.get("id")
                            or message.get("id")
                        )
                        if "id" in message:
                            conversation.pending_calls[call_id] = (
                                int(message["id"]),
                                params,
                            )
                        await conversation.events.put(("tool", params))
                    elif "id" in message:
                        await self._send_response(
                            int(message["id"]),
                            {
                                "success": False,
                                "contentItems": [
                                    {
                                        "type": "inputText",
                                        "text": "AESPA no longer has this tool call.",
                                    }
                                ],
                            },
                        )
                    continue
                if thread_id and (conversation := self._conversations.get(thread_id)):
                    kind = str(message.get("method") or "notification")
                    await conversation.events.put((kind, params))
                else:
                    await self._notifications.put(message)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.debug("Codex app-server stdout reader stopped: %s", exc)
        finally:
            error = CodexUnavailableError(
                "Codex app-server stopped unexpectedly"
                + (f": {list(self._stderr_tail)[-1]}" if self._stderr_tail else "")
            )
            for future in list(self._pending.values()):
                if not future.done():
                    future.set_exception(error)
            self._pending.clear()

    async def _read_stderr(self) -> None:
        if not self.process or not self.process.stderr:
            return
        try:
            async for raw in self.process.stderr:
                line = raw.decode("utf-8", "replace").strip()
                if line:
                    self._stderr_tail.append(line)
        except asyncio.CancelledError:
            raise

    async def _send(self, message: dict[str, Any]) -> None:
        if not self.process or not self.process.stdin:
            raise CodexUnavailableError("Codex app-server is not running")
        async with self._write_lock:
            self.process.stdin.write((json.dumps(message) + "\n").encode("utf-8"))
            await self.process.stdin.drain()

    async def _send_response(self, request_id: int, result: Any) -> None:
        await self._send({"jsonrpc": "2.0", "id": request_id, "result": result})

    async def request(self, method: str, params: dict[str, Any] | None = None) -> Any:
        request_id = self._next_id
        self._next_id += 1
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self._pending[request_id] = future
        await self._send(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params or {},
            }
        )
        return await asyncio.wait_for(future, timeout=TURN_TIMEOUT_S)

    async def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        await self._send({"jsonrpc": "2.0", "method": method, "params": params or {}})

    async def close(self) -> None:
        for task in (self._reader_task, self._stderr_task):
            if task:
                task.cancel()
        if self.process and self.process.returncode is None:
            self.process.terminate()
            with contextlib.suppress(ProcessLookupError, asyncio.TimeoutError):
                await asyncio.wait_for(self.process.wait(), timeout=3)
            if self.process.returncode is None:
                self.process.kill()
        for task in (self._reader_task, self._stderr_task):
            if task:
                with contextlib.suppress(asyncio.CancelledError):
                    await task
        self._reader_task = None
        self._stderr_task = None
        self.process = None
        self.initialized = False
        for future in self._pending.values():
            if not future.done():
                future.cancel()
        self._pending.clear()
        self._conversations.clear()


_client: _JsonRpcClient | None = None
_client_lock = asyncio.Lock()
_conversations: dict[int, _Conversation] = {}
_usage_callbacks: dict[int, Callable[..., None]] = {}


async def _get_client() -> _JsonRpcClient:
    global _client
    async with _client_lock:
        if (
            _client is None
            or not _client.process
            or _client.process.returncode is not None
        ):
            configured_path = None
            with contextlib.suppress(Exception):
                from sqlmodel import Session

                from aespa.db import get_engine
                from aespa.models import CodexIntegrationConfig

                with Session(get_engine()) as session:
                    row = session.get(CodexIntegrationConfig, 1)
                    configured_path = row.executable_path if row else None
            info = await detect_installation(configured_path)
            executable = info.get("executable")
            if not executable:
                raise CodexUnavailableError(
                    "Codex CLI is not installed. Install Codex separately and restart AESPA, "
                    "or set its executable path in Settings."
                )
            _client = _JsonRpcClient(executable)
            try:
                await _client.start()
            except Exception:
                await _client.close()
                _client = None
                raise
        return _client


def _tool_schema(tool: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "name": str(tool.get("name") or "tool"),
        "description": str(tool.get("description") or ""),
        "inputSchema": tool.get("input_schema")
        or tool.get("inputSchema")
        or {"type": "object"},
    }


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            str(block.get("text") or block.get("content") or "")
            for block in content
            if isinstance(block, dict)
        )
    return json.dumps(content, default=str)


def _event_text(params: dict[str, Any]) -> str:
    """Read assistant text from both flat and item-wrapped app-server events."""
    text = _content_text(params.get("text") or params.get("content") or "")
    if text:
        return text
    item = params.get("item")
    if isinstance(item, dict):
        return _content_text(item.get("text") or item.get("content") or "")
    return ""


def _merge_completed_text(conversation: _Conversation, completed: str) -> None:
    """Replace streamed deltas with the completed form without duplicating them."""
    if not completed:
        return
    streamed = "".join(conversation.text)
    if not streamed or completed.startswith(streamed):
        conversation.text[:] = [completed]
    elif not streamed.endswith(completed):
        conversation.text.append(completed)


def _take_conversation_text(conversation: _Conversation) -> str:
    text = "".join(conversation.text)
    conversation.text.clear()
    return text


def _internal_action_name(params: dict[str, Any]) -> str | None:
    """Name a Codex-owned action that AESPA cannot service as a scan tool."""
    item = params.get("item")
    if not isinstance(item, dict):
        return None
    item_type = str(item.get("type") or "")
    if item_type not in _INTERNAL_ACTION_ITEM_TYPES:
        return None
    return str(item.get("tool") or item_type)


def _conversation_prompt(system_message: str, messages: list[dict[str, Any]]) -> str:
    transcript = [system_message]
    for message in messages:
        transcript.append(
            f"[{str(message.get('role') or 'user').upper()}]\n{_content_text(message.get('content'))}"
        )
    return "\n\n".join(transcript)


def _usage_delta(conversation: _Conversation, params: dict[str, Any]) -> dict[str, int]:
    usage = params.get("usage") or params.get("tokenUsage") or params
    # Current app-server versions wrap cumulative thread counters in
    # ``tokenUsage.total`` and expose the most recent model call separately as
    # ``tokenUsage.last``. Older releases sent the counters directly, so keep
    # accepting that flat shape as well.
    if isinstance(usage, dict) and isinstance(usage.get("total"), dict):
        usage = usage["total"]
    if not isinstance(usage, dict):
        usage = {}
    totals: dict[str, int] = {}
    for key in (
        "inputTokens",
        "cachedInputTokens",
        "cacheWriteInputTokens",
        "outputTokens",
        "reasoningOutputTokens",
        "totalTokens",
    ):
        try:
            totals[key] = int(usage.get(key) or 0)
        except (TypeError, ValueError):
            totals[key] = 0
    delta = {
        key: max(0, value - conversation.usage.get(key, 0))
        for key, value in totals.items()
    }
    conversation.usage = totals
    return delta


def _emit_usage(
    callback: Callable[..., None] | None,
    model: str,
    delta: dict[str, int],
    quota: dict[str, Any] | None = None,
) -> None:
    if not callback:
        return
    token_count = sum(
        delta.get(key, 0)
        for key in (
            "inputTokens",
            "cachedInputTokens",
            "cacheWriteInputTokens",
            "outputTokens",
            "reasoningOutputTokens",
        )
    )
    if token_count <= 0 and not quota:
        return
    callback(
        model,
        delta.get("inputTokens", 0),
        # Codex reports reasoning output separately. Include it in the total
        # used to reconcile AESPA's local bucket; otherwise long reasoning turns
        # would be credited back as if they were cheaper than they were.
        delta.get("outputTokens", 0) + delta.get("reasoningOutputTokens", 0),
        delta.get("cachedInputTokens", 0),
        delta.get("cacheWriteInputTokens", 0),
        requests=1 if token_count > 0 else 0,
        codex_quota=quota,
    )


async def _start_thread(
    client: _JsonRpcClient,
    config: LLMConfig,
    system_message: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
) -> _Conversation:
    tool_rule = (
        "Call only the dynamic tools supplied by AESPA. Every tool-assisted "
        "step must use one of those dynamic tools."
        if tools
        else "Do not call any tool."
    )
    params: dict[str, Any] = {
        "model": config.model,
        "cwd": str(_workspace()),
        "sandbox": "read-only",
        "approvalPolicy": "never",
        "baseInstructions": (
            "You are embedded in AESPA as a model and tool caller, not as a "
            "coding agent. Never use Codex-owned tools such as exec, shell, "
            "wait, sleep, collaboration, file editing, MCP, or web search. " + tool_rule
        ),
        "developerInstructions": system_message,
        "serviceName": "aespa",
    }
    if tools:
        params["dynamicTools"] = [_tool_schema(tool) for tool in tools]
    try:
        result = await client.request("thread/start", params)
    except CodexUnavailableError as exc:
        if tools:
            raise CodexUnavailableError(
                "This Codex CLI does not support AESPA dynamic tools. "
                "Upgrade Codex CLI and try again. Details: " + str(exc)
            ) from exc
        raise
    thread_id = str((result or {}).get("thread", result or {}).get("id") or "")
    if not thread_id:
        raise CodexUnavailableError("Codex did not return a thread id")
    conversation = _Conversation(thread_id=thread_id, last_message_count=len(messages))
    client._conversations[thread_id] = conversation
    return conversation


async def _probe_dynamic_tools(client: _JsonRpcClient) -> None:
    """Verify the installed CLI exposes the experimental dynamic-tools field."""
    result = await client.request(
        "thread/start",
        {
            "model": "auto",
            "cwd": str(_workspace()),
            "sandbox": "read-only",
            "approvalPolicy": "never",
            "dynamicTools": [
                {
                    "type": "function",
                    "name": "aespa_capability_probe",
                    "description": "Capability probe; never call this tool.",
                    "inputSchema": {"type": "object"},
                }
            ],
        },
    )
    thread_id = str((result or {}).get("thread", result or {}).get("id") or "")
    if thread_id:
        with contextlib.suppress(Exception):
            await client.request("thread/delete", {"threadId": thread_id})


async def _send_turn(
    client: _JsonRpcClient,
    conversation: _Conversation,
    config: LLMConfig,
    prompt: str,
) -> None:
    params = {
        "threadId": conversation.thread_id,
        "input": [{"type": "text", "text": prompt}],
        "model": config.model,
    }
    if config.reasoning_effort:
        params["effort"] = config.reasoning_effort
    await client.request(
        "turn/start",
        params,
    )


async def _send_pending_tool_results(
    client: _JsonRpcClient,
    conversation: _Conversation,
    messages: list[dict],
    start_at: int,
) -> int:
    """Complete app-server callbacks represented by new tool-result blocks."""
    resolved = 0
    for message in messages[start_at:]:
        if message.get("role") != "user":
            continue
        for block in message.get("content") or []:
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            call_id = str(block.get("tool_use_id") or block.get("id") or "")
            pending = conversation.pending_calls.pop(call_id, None)
            if not pending:
                continue
            request_id, _params = pending
            result = block.get("content") or ""
            if not isinstance(result, str):
                result = json.dumps(result, default=str)
            await client._send_response(
                request_id,
                {
                    "success": not bool(block.get("is_error")),
                    "contentItems": [{"type": "inputText", "text": result}],
                },
            )
            resolved += 1
    return resolved


async def flush_pending_tool_results(messages: list[dict]) -> int:
    """Acknowledge completed dynamic tools without starting another model turn.

    Codex runs AESPA dynamic tools inside an exec cell. Delaying the callback
    response until the next model request makes that cell poll with ``wait`` and
    can deadlock if the owning loop stops first.
    """
    conversation = _conversations.get(id(messages))
    if conversation is None or _client is None:
        return 0
    resolved = await _send_pending_tool_results(
        _client,
        conversation,
        messages,
        conversation.last_message_count,
    )
    conversation.last_message_count = len(messages)
    if resolved:
        # Let the stdout reader consume the resulting completion notification
        # before close_conversation queues thread/delete on the same connection.
        await asyncio.sleep(0)
    return resolved


async def _completion_with_tools_once(
    config: LLMConfig,
    system_message: str,
    messages: list[dict],
    tools: list[dict],
    usage_callback: Callable[..., None],
    proxy_url: str | None = None,
) -> tuple[list[dict], str, list[dict]]:
    del proxy_url
    client = await _get_client()
    # The app-server exposes the current Codex window without consuming a
    # model request. Check it before starting a turn so a known-full window is
    # paused instead of repeatedly sending requests that will be rejected.
    try:
        rate_limits = await client.request("account/rateLimits/read", {})
    except Exception:
        rate_limits = None
    if rate_limits is not None and _rate_limit_is_exhausted(rate_limits):
        raise CodexRateLimitError(
            "Codex reports that its current rate-limit window is full. "
            "AESPA paused before sending this turn; resume after the window resets.",
            reset_at=_extract_reset_at(rate_limits),
            snapshot={"preflight": True, "rate_limits": rate_limits},
        )
    key = id(messages)
    conversation = _conversations.get(key)
    if conversation is None:
        conversation = await _start_thread(
            client, config, system_message, messages, tools
        )
        _conversations[key] = conversation
        _usage_callbacks[key] = usage_callback
        conversation.text.clear()
        await _send_turn(
            client,
            conversation,
            config,
            _conversation_prompt(system_message, messages),
        )
    else:
        # Resolve tool calls held open by the app-server until AESPA supplied a
        # result.  The server then continues the same turn.
        previous_message_count = conversation.last_message_count
        await _send_pending_tool_results(
            client,
            conversation,
            messages,
            previous_message_count,
        )

        user_messages = []
        for message in messages[previous_message_count:]:
            if message.get("role") != "user":
                continue
            content = message.get("content")
            if isinstance(content, str):
                user_messages.append(message)
            elif any(
                isinstance(block, dict) and block.get("type") != "tool_result"
                for block in content or []
            ):
                user_messages.append(message)
        conversation.last_message_count = len(messages)
        if user_messages:
            conversation.text.clear()
            await _send_turn(
                client,
                conversation,
                config,
                _content_text(user_messages[-1].get("content")),
            )

    while True:
        try:
            event_type, params = await asyncio.wait_for(
                conversation.events.get(), timeout=TURN_TIMEOUT_S
            )
        except TimeoutError as exc:
            raise CodexUnavailableError(
                f"Codex produced no usable AESPA response for {TURN_TIMEOUT_S:.0f} "
                "seconds. AESPA stopped the stalled turn."
            ) from exc
        if event_type in {"item/started", "item/completed"}:
            internal_action = _internal_action_name(params)
            if internal_action:
                raise CodexUnavailableError(
                    f"Codex tried to use its internal '{internal_action}' tool. "
                    "AESPA stopped the turn because only AESPA dynamic tools can "
                    "be used during a scan. Try a different Codex model if this "
                    "keeps happening."
                )
        if event_type in {"thread/tokenUsage/updated", "tokenUsage"}:
            delta = _usage_delta(conversation, params)
            quota = None
            with contextlib.suppress(Exception):
                quota = await read_rate_limits()
            _emit_usage(usage_callback, config.model, delta, quota)
            continue
        if event_type == "item/tool/call" or event_type == "tool":
            call_id = str(params.get("callId") or params.get("id") or "")
            arguments = params.get("arguments") or {}
            if isinstance(arguments, str):
                with contextlib.suppress(json.JSONDecodeError):
                    arguments = json.loads(arguments)
            tool_block = {
                "type": "tool_use",
                "id": call_id,
                "name": str(params.get("tool") or params.get("name") or ""),
                "input": arguments,
                "text": None,
            }
            # An agent-message item may precede a tool call within the same Codex
            # turn. Return both together so ALICE treats the message as
            # intermediate commentary rather than a separate tool-less turn.
            buffered_text = _take_conversation_text(conversation)
            blocks = []
            if buffered_text:
                blocks.append(
                    {
                        "type": "text",
                        "id": None,
                        "name": None,
                        "input": None,
                        "text": buffered_text,
                    }
                )
            blocks.append(tool_block)
            return blocks, "tool_use", blocks
        if "usageLimitExceeded" in json.dumps(params, default=str):
            raise CodexQuotaError(
                "ChatGPT/Codex allowance exhausted. Check the Codex allowance window and resume later.",
                reset_at=_extract_reset_at(params),
                snapshot=params,
            )
        if event_type == "item/agentMessage/completed":
            # This completes one message item, not the Codex turn. A dynamic
            # tool call can follow it, so keep waiting for a tool or turn event.
            _merge_completed_text(conversation, _event_text(params))
            continue
        if event_type in {"turn/completed", "turn/completion"}:
            _merge_completed_text(conversation, _event_text(params))
            output = _take_conversation_text(conversation)
            if output:
                block = {
                    "type": "text",
                    "id": None,
                    "name": None,
                    "input": None,
                    "text": output,
                }
                return [block], "end_turn", [block]
            continue
        if event_type in {"item/agentMessage/delta", "agentMessage/delta"}:
            delta_text = str(params.get("delta") or params.get("text") or "")
            if delta_text:
                conversation.text.append(delta_text)
            continue
        if event_type in {"turn/failed", "error"}:
            details = json.dumps(params, default=str)
            if "usageLimitExceeded" in details:
                raise CodexQuotaError(
                    "ChatGPT/Codex allowance exhausted. Check the Codex allowance window and resume later.",
                    reset_at=_extract_reset_at(params),
                    snapshot=params,
                )
            if _is_rate_limit_error(params):
                retry_after_s = _extract_retry_after(params)
                window_full = _rate_limit_error_has_full_window(params)
                rate_limits: dict[str, Any] = {}
                with contextlib.suppress(Exception):
                    rate_limits = await read_rate_limits()
                message = (
                    "Codex upstream TPM window is full. AESPA paused this turn; "
                    "resume after the rate-limit window resets."
                    if window_full
                    else "Codex upstream rate limit reached. AESPA will retry briefly; "
                    "if it persists, resume after the rate-limit window resets."
                )
                raise CodexRateLimitError(
                    message,
                    retry_after_s=retry_after_s,
                    reset_at=_extract_reset_at(rate_limits)
                    or _extract_reset_at(params),
                    snapshot={
                        "error": params,
                        "rate_limits": rate_limits,
                        "window_full": window_full,
                    },
                )
            raise CodexUnavailableError(details)


async def completion_with_tools(
    config: LLMConfig,
    system_message: str,
    messages: list[dict],
    tools: list[dict],
    usage_callback: Callable[..., None],
    proxy_url: str | None = None,
) -> tuple[list[dict], str, list[dict]]:
    """Run a turn, retrying short-lived upstream Codex rate limits safely."""
    max_retries = 3
    for attempt in range(max_retries + 1):
        try:
            return await _completion_with_tools_once(
                config,
                system_message,
                messages,
                tools,
                usage_callback,
                proxy_url,
            )
        except CodexRateLimitError as exc:
            if exc.snapshot.get("preflight") or exc.snapshot.get("window_full"):
                raise
            if attempt >= max_retries:
                raise CodexRateLimitError(
                    "Codex upstream rate limit persisted after AESPA retries. "
                    "AESPA's local TPM setting cannot reset this window; resume after the Codex rate-limit window resets.",
                    retry_after_s=exc.retry_after_s,
                    reset_at=exc.reset_at,
                    snapshot=exc.snapshot,
                ) from exc
            delay = max(0.25, exc.retry_after_s or 0.5) * (2**attempt)
            await close_conversation(messages)
            log.info(
                "Codex upstream rate limit; retrying AESPA turn in %.2fs (attempt %d/%d)",
                delay,
                attempt + 1,
                max_retries,
            )
            await asyncio.sleep(min(delay, 5.0))


async def plain_completion(
    config: LLMConfig,
    prompt: str,
    screenshot_b64: str | None,
    usage_callback: Callable[..., None],
    proxy_url: str | None = None,
) -> str:
    del proxy_url
    if screenshot_b64:
        raise CodexUnavailableError(
            "Codex image input is not available through the AESPA app-server adapter yet."
        )
    messages = [{"role": "user", "content": prompt}]
    try:
        blocks, _, _ = await completion_with_tools(
            config,
            "Return only the requested result. Do not use tools.",
            messages,
            [],
            usage_callback,
        )
        return "".join(str(block.get("text") or "") for block in blocks)
    finally:
        await close_conversation(messages)


async def close_conversation(messages: list[dict]) -> None:
    key = id(messages)
    conversation = _conversations.get(key)
    if conversation is None or _client is None:
        _conversations.pop(key, None)
        _usage_callbacks.pop(key, None)
        return
    # Deliver any results appended immediately before cancellation, a budget
    # stop, or another early exit. Then explicitly fail callbacks whose tool
    # execution never produced a result so no Codex exec cell remains waiting.
    with contextlib.suppress(Exception):
        await flush_pending_tool_results(messages)
    for call_id, (request_id, _params) in list(conversation.pending_calls.items()):
        with contextlib.suppress(Exception):
            await _client._send_response(
                request_id,
                {
                    "success": False,
                    "contentItems": [
                        {
                            "type": "inputText",
                            "text": "AESPA closed the agent turn before this tool completed.",
                        }
                    ],
                },
            )
        conversation.pending_calls.pop(call_id, None)
    _conversations.pop(key, None)
    _usage_callbacks.pop(key, None)
    _client._conversations.pop(conversation.thread_id, None)
    with contextlib.suppress(Exception):
        await _client.request("thread/delete", {"threadId": conversation.thread_id})


async def close_clients() -> None:
    global _client
    _conversations.clear()
    _usage_callbacks.clear()
    if _client is not None:
        await _client.close()
    _client = None


async def login_start() -> dict[str, Any]:
    client = await _get_client()
    return await client.request(
        "account/login/start",
        # Device-code auth keeps the login UX in AESPA.  The browser flow can
        # hand the URL to the installed ChatGPT app via macOS universal links,
        # which bypasses the AESPA Settings page and its login status polling.
        {"type": "chatgptDeviceCode"},
    )


async def login_cancel(login_id: str) -> dict[str, Any]:
    client = await _get_client()
    return await client.request("account/login/cancel", {"loginId": login_id})


async def logout() -> dict[str, Any]:
    client = await _get_client()
    return await client.request("account/logout", {})


async def status() -> dict[str, Any]:
    configured_path = None
    with contextlib.suppress(Exception):
        from sqlmodel import Session

        from aespa.db import get_engine
        from aespa.models import CodexIntegrationConfig

        with Session(get_engine()) as session:
            row = session.get(CodexIntegrationConfig, 1)
            configured_path = row.executable_path if row else None
    info = await detect_installation(configured_path)
    if not info.get("installed"):
        return info | {"running": False, "compatible": False, "account": None}
    try:
        client = await _get_client()
        account = await client.request("account/read", {})
        limits = await client.request("account/rateLimits/read", {})
        try:
            await _probe_dynamic_tools(client)
        except Exception as exc:
            return info | {
                "running": True,
                "compatible": False,
                "account": account,
                "rate_limits": limits,
                "error": "This Codex CLI does not support AESPA dynamic tools. Upgrade Codex CLI and try again. "
                + str(exc),
            }
        return info | {
            "running": True,
            "compatible": True,
            "account": account,
            "rate_limits": limits,
        }
    except Exception as exc:
        return info | {
            "running": False,
            "compatible": False,
            "account": None,
            "error": str(exc),
        }


async def discover_models() -> list[str]:
    return [item["id"] for item in await discover_model_options()]


async def discover_model_options() -> list[dict[str, Any]]:
    client = await _get_client()
    models: list[dict[str, Any]] = []
    cursor: str | None = None
    for _ in range(20):
        result = await client.request(
            "model/list", {"cursor": cursor} if cursor else {}
        )
        if not isinstance(result, dict):
            break
        rows = result.get("data", result.get("models", []))
        for row in rows:
            if (
                not isinstance(row, dict)
                or not row.get("id")
                or row.get("hidden", False)
            ):
                continue
            models.append(
                {
                    "id": str(row["id"]),
                    "supportedReasoningEfforts": row.get("supportedReasoningEfforts"),
                    "defaultReasoningEffort": row.get("defaultReasoningEffort"),
                }
            )
        next_cursor = result.get("nextCursor") or result.get("next_cursor")
        if not next_cursor or next_cursor == cursor:
            break
        cursor = str(next_cursor)
    unique = {}
    for item in models:
        unique.setdefault(item["id"], item)
    return list(unique.values())


async def read_rate_limits() -> dict[str, Any]:
    client = await _get_client()
    result = await client.request("account/rateLimits/read", {})
    return result if isinstance(result, dict) else {}
