"""Factory Droid SDK adapter using the user's existing Droid CLI login."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import secrets
import shutil
import tempfile
from collections import deque
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from aespa.models import LLMConfig

log = logging.getLogger("aespa.llm.droid")
logging.getLogger("droid_sdk.client").setLevel(logging.INFO)

DROID_TURN_TIMEOUT_S = 600.0
_ENV_ALLOWLIST = (
    "PATH",
    "HOME",
    "USERPROFILE",
    "APPDATA",
    "LOCALAPPDATA",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "TMPDIR",
    "LANG",
    "LC_ALL",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "NODE_EXTRA_CA_CERTS",
)


class _IsolatedProcessTransport:
    """Droid SDK transport that does not inherit AESPA/target environment secrets."""

    def __init__(self, *, cwd: str, env: dict[str, str]):
        self.cwd = cwd
        self.env = env
        self.process: asyncio.subprocess.Process | None = None
        self._write_lock = asyncio.Lock()
        self._stderr_tail: deque[str] = deque(maxlen=20)
        self._stderr_task: asyncio.Task | None = None

    async def connect(self) -> None:
        executable = shutil.which("droid", path=self.env.get("PATH"))
        if not executable:
            raise RuntimeError("Droid CLI was not found. Install and sign in to Droid first.")
        self.process = await asyncio.create_subprocess_exec(
            executable,
            "exec",
            "--input-format",
            "stream-jsonrpc",
            "--output-format",
            "stream-jsonrpc",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.cwd,
            env=self.env,
            limit=10 * 1024 * 1024,
        )
        self._stderr_task = asyncio.create_task(self._drain_stderr(self.process))

    async def _drain_stderr(self, process: asyncio.subprocess.Process) -> None:
        if not process.stderr:
            return
        while line := await process.stderr.readline():
            self._stderr_tail.append(line.decode(errors="replace").strip())

    async def send(self, message: str) -> None:
        if not self.process or not self.process.stdin:
            raise RuntimeError("Droid CLI is not connected")
        async with self._write_lock:
            self.process.stdin.write((message + "\n").encode())
            await self.process.stdin.drain()

    async def read_messages(self) -> AsyncIterator[dict[str, Any]]:
        if not self.process or not self.process.stdout:
            return
        while line := await self.process.stdout.readline():
            text = line.decode(errors="replace").strip()
            if text.startswith(("{", "[")):
                try:
                    yield json.loads(text)
                except json.JSONDecodeError:
                    log.debug("Ignoring malformed Droid JSON-RPC output")
        if self.process.returncode not in (None, 0):
            if self._stderr_task:
                await self._stderr_task
            detail = "\n".join(self._stderr_tail)
            raise RuntimeError(
                f"Droid CLI exited with code {self.process.returncode}: {detail[:500]}"
            )

    async def close(self) -> None:
        process, self.process = self.process, None
        if not process:
            return
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), 5)
            except TimeoutError:
                process.kill()
                await process.wait()
        if self._stderr_task:
            await self._stderr_task
            self._stderr_task = None


@dataclass
class _PendingTool:
    future: asyncio.Future[tuple[str, bool]]
    writer: asyncio.StreamWriter


@dataclass
class _Conversation:
    client: Any
    transport: _IsolatedProcessTransport
    directory: Path
    server: asyncio.AbstractServer
    token: str
    events: asyncio.Queue[tuple[str, Any]] = field(default_factory=asyncio.Queue)
    pending: dict[str, _PendingTool] = field(default_factory=dict)
    drain_task: asyncio.Task | None = None
    last_message_count: int = 0
    usage: Any = None
    factory_credits: float = 0
    recorded_usage: tuple[int, int, int, int, float] = (0, 0, 0, 0, 0)
    unsubscribe_usage: Callable[[], None] | None = None


_conversations: dict[int, _Conversation] = {}


def _workspace_directory() -> Path:
    # ponytail: one empty cwd keeps Factory sessions in one project; split only
    # if per-run project grouping becomes useful.
    directory = Path(tempfile.gettempdir()) / "aespa-droid-workspace"
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    return directory


def _child_env(proxy_url: str | None = None) -> dict[str, str]:
    env = {name: os.environ[name] for name in _ENV_ALLOWLIST if name in os.environ}
    if proxy_url:
        env["HTTP_PROXY"] = proxy_url
        env["HTTPS_PROXY"] = proxy_url
    return env


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for block in content or []:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            parts.append(str(block.get("text") or ""))
        elif block.get("type") == "tool_use":
            parts.append(
                f"[Tool call: {block.get('name') or 'unknown'} "
                f"{json.dumps(block.get('input') or {}, default=str)}]"
            )
        elif block.get("type") == "tool_result":
            parts.append(
                f"[Tool result: {block.get('tool_use_id') or 'unknown'}]\n"
                f"{block.get('content') or ''}"
            )
    return "\n".join(filter(None, parts))


def _conversation_prompt(messages: list[dict]) -> str:
    return "\n\n".join(
        f"[{str(message.get('role') or 'user').upper()}]\n"
        f"{_content_text(message.get('content'))}"
        for message in messages
    )


def _mcp_tools(tools: list[dict]) -> list[dict]:
    return [
        {
            "name": tool["name"],
            "description": tool.get("description", ""),
            "inputSchema": tool.get("input_schema", {"type": "object"}),
        }
        for tool in tools
    ]


def _capture_factory_credits(conversation: _Conversation, message: dict) -> None:
    notification = (message.get("params") or {}).get("notification") or {}
    if notification.get("type") != "session_token_usage_changed":
        return
    credits = (notification.get("tokenUsage") or {}).get("factoryCredits")
    if isinstance(credits, (int, float)) and credits >= 0:
        conversation.factory_credits = float(credits)


async def discover_models(proxy_url: str | None = None) -> list[str]:
    """Return models available to the account currently signed in through Droid CLI."""
    from droid_sdk import DroidClient

    directory = _workspace_directory()
    transport = _IsolatedProcessTransport(cwd=str(directory), env=_child_env(proxy_url))
    client = DroidClient(transport=transport)
    try:
        await client.connect()
        result = await asyncio.wait_for(
            client.initialize_session(machine_id="aespa", cwd=str(directory)),
            timeout=30,
        )
        return [model.id for model in result.available_models or []]
    finally:
        await client.close()


async def _handle_relay(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    conversation: _Conversation,
    tool_names: set[str],
) -> None:
    tool_id = ""
    try:
        payload = json.loads(await reader.readline())
        if not secrets.compare_digest(str(payload.get("token") or ""), conversation.token):
            raise RuntimeError("Invalid Droid tool bridge token")
        params = payload.get("params") or {}
        name = str(params.get("name") or "")
        arguments = params.get("arguments") or {}
        if name not in tool_names or not isinstance(arguments, dict):
            raise RuntimeError("Invalid Droid tool call")
        tool_id = secrets.token_urlsafe(12)
        pending = _PendingTool(asyncio.get_running_loop().create_future(), writer)
        conversation.pending[tool_id] = pending
        await conversation.events.put(
            (
                "tool",
                {"type": "tool_use", "id": tool_id, "name": name, "input": arguments},
            )
        )
        result, is_error = await pending.future
        response = {
            "content": [{"type": "text", "text": result}],
            "isError": is_error,
        }
        writer.write((json.dumps(response, separators=(",", ":")) + "\n").encode())
        await writer.drain()
    except Exception as exc:
        with contextlib.suppress(Exception):
            writer.write(
                (
                    json.dumps(
                        {
                            "content": [{"type": "text", "text": str(exc)}],
                            "isError": True,
                        },
                        separators=(",", ":"),
                    )
                    + "\n"
                ).encode()
            )
            await writer.drain()
    finally:
        if tool_id:
            conversation.pending.pop(tool_id, None)
        writer.close()
        with contextlib.suppress(Exception):
            await writer.wait_closed()


def _permission_handler(params: dict[str, Any]) -> str:
    from droid_sdk import ToolConfirmationOutcome

    tool_uses = params.get("toolUses") or []
    aespa_only = bool(tool_uses) and all(
        isinstance(item, dict)
        and item.get("confirmationType") == "mcp_tool"
        and (item.get("details") or {}).get("serverName") == "aespa"
        for item in tool_uses
    )
    return (
        ToolConfirmationOutcome.ProceedOnce.value
        if aespa_only
        else ToolConfirmationOutcome.Cancel.value
    )


async def _drain(conversation: _Conversation) -> None:
    from droid_sdk import (
        AssistantTextDelta,
        ErrorEvent,
        TokenUsageUpdate,
        TurnComplete,
    )

    text: list[str] = []
    async for message in conversation.client.receive_response():
        if isinstance(message, AssistantTextDelta):
            text.append(message.text)
        elif isinstance(message, TokenUsageUpdate):
            conversation.usage = message
        elif isinstance(message, ErrorEvent):
            await conversation.events.put(("error", message.message))
        elif isinstance(message, TurnComplete):
            conversation.usage = message.token_usage or conversation.usage
            await conversation.events.put(("complete", "".join(text)))
            return


async def _create_conversation(
    config: LLMConfig,
    system_message: str,
    messages: list[dict],
    tools: list[dict],
    usage_callback: Callable[..., None],
    proxy_url: str | None,
) -> _Conversation:
    from droid_sdk import DroidClient

    directory = _workspace_directory()
    transport = _IsolatedProcessTransport(cwd=str(directory), env=_child_env(proxy_url))
    client = DroidClient(transport=transport)
    token = secrets.token_urlsafe(32)
    holder: dict[str, _Conversation] = {}
    tool_names = {tool["name"] for tool in tools}
    server = await asyncio.start_server(
        lambda r, w: _handle_relay(r, w, holder["conversation"], tool_names),
        "127.0.0.1",
        0,
    )
    port = server.sockets[0].getsockname()[1]
    conversation = _Conversation(client, transport, directory, server, token)
    holder["conversation"] = conversation
    try:
        await client.connect()
        conversation.unsubscribe_usage = client.on_notification(
            lambda message: _capture_factory_credits(conversation, message)
        )
        client.set_permission_handler(_permission_handler)
        await client.initialize_session(
            machine_id="aespa",
            cwd=str(directory),
            model_id=config.model,
            mcp_servers=[
                {
                    "name": "aespa",
                    "command": os.sys.executable,
                    "args": [
                        "-m",
                        "aespa.services.droid_mcp_relay",
                        "127.0.0.1",
                        str(port),
                        token,
                        json.dumps(_mcp_tools(tools), separators=(",", ":")),
                    ],
                    "env": {},
                }
            ],
        )
        prompt = f"{system_message}\n\n{_conversation_prompt(messages)}"
        await client.add_user_message(text=prompt)
        conversation.last_message_count = len(messages)
        conversation.drain_task = asyncio.create_task(_drain(conversation))
        return conversation
    except Exception:
        await client.close()
        server.close()
        await server.wait_closed()
        raise


def _record_usage(
    conversation: _Conversation,
    config: LLMConfig,
    usage_callback: Callable[..., None],
) -> None:
    usage = conversation.usage
    if usage is None:
        return
    current = (
        usage.input_tokens,
        usage.output_tokens,
        usage.cache_read_tokens,
        usage.cache_write_tokens,
        conversation.factory_credits,
    )
    delta = tuple(
        max(0, value - previous)
        for value, previous in zip(current, conversation.recorded_usage)
    )
    usage_callback(
        config.model,
        *delta[:4],
        factory_credits=delta[4],
        requests=1,
    )
    conversation.recorded_usage = current
    conversation.usage = None


async def completion_with_tools(
    config: LLMConfig,
    system_message: str,
    messages: list[dict],
    tools: list[dict],
    usage_callback: Callable[..., None],
    proxy_url: str | None = None,
) -> tuple[list[dict], str, list[dict]]:
    key = id(messages)
    conversation = _conversations.get(key)
    if conversation is None:
        conversation = await _create_conversation(
            config, system_message, messages, tools, usage_callback, proxy_url
        )
        _conversations[key] = conversation
    else:
        next_prompt: list[str] = []
        for message in messages[conversation.last_message_count :]:
            if message.get("role") != "user":
                continue
            content = message.get("content")
            if isinstance(content, str):
                if content:
                    next_prompt.append(content)
                continue
            for block in content or []:
                if not isinstance(block, dict) or block.get("type") != "tool_result":
                    continue
                pending = conversation.pending.get(str(block.get("tool_use_id") or ""))
                if pending and not pending.future.done():
                    content = block.get("content") or ""
                    if not isinstance(content, str):
                        content = json.dumps(content, default=str)
                    pending.future.set_result((content, bool(block.get("is_error"))))
        conversation.last_message_count = len(messages)
        if next_prompt:
            if conversation.drain_task:
                await conversation.drain_task
            await conversation.client.add_user_message(text="\n\n".join(next_prompt))
            conversation.drain_task = asyncio.create_task(_drain(conversation))

    try:
        event_type, data = await asyncio.wait_for(
            conversation.events.get(), timeout=DROID_TURN_TIMEOUT_S
        )
    except TimeoutError as exc:
        await _close_conversation(key)
        raise RuntimeError("Factory Droid turn timed out") from exc
    except asyncio.CancelledError:
        await _close_conversation(key)
        raise
    _record_usage(conversation, config, usage_callback)
    if event_type == "error":
        raise RuntimeError(f"Factory Droid session error: {data}")
    if event_type == "tool":
        blocks = [{**data, "text": None}]
        return blocks, "tool_use", blocks
    if conversation.drain_task:
        await conversation.drain_task
        conversation.drain_task = None
    blocks = (
        [{"type": "text", "id": None, "name": None, "input": None, "text": data}]
        if data
        else []
    )
    return blocks, "end_turn", blocks


async def plain_completion(
    config: LLMConfig,
    prompt: str,
    screenshot_b64: str | None,
    usage_callback: Callable[..., None],
    proxy_url: str | None = None,
) -> str:
    if screenshot_b64:
        raise RuntimeError("Factory Droid vision is not supported by this adapter")
    messages = [{"role": "user", "content": prompt}]
    try:
        blocks, _, _ = await completion_with_tools(
            config,
            "Return only the requested result. Do not use tools.",
            messages,
            [],
            usage_callback,
            proxy_url,
        )
        return "".join(str(block.get("text") or "") for block in blocks)
    finally:
        await close_conversation(messages)


async def close_conversation(messages: list[dict]) -> None:
    await _close_conversation(id(messages))


async def close_clients() -> None:
    for key in list(_conversations):
        await _close_conversation(key)


async def _close_conversation(key: int) -> None:
    conversation = _conversations.pop(key, None)
    if conversation is None:
        return
    for pending in conversation.pending.values():
        if not pending.future.done():
            pending.future.cancel()
    if conversation.drain_task:
        conversation.drain_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await conversation.drain_task
    conversation.server.close()
    await conversation.server.wait_closed()
    if conversation.unsubscribe_usage:
        conversation.unsubscribe_usage()
    await conversation.client.close()
