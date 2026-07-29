"""GitHub Copilot SDK adapter for AESPA's provider-neutral LLM interface.

The Copilot SDK normally owns a complete agent loop. AESPA deliberately owns the
execution boundary so it can apply scope checks, execution monitoring, checkpoints,
and finding validation between every tool call. This adapter keeps one SDK session
alive for each AESPA agent conversation. A custom tool handler pauses while AESPA
executes the request, then receives the real result and lets the same Copilot session
continue. This preserves provider conversation state and prompt-cache opportunities.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import shutil
import sqlite3
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from aespa.models import LLMConfig

log = logging.getLogger("aespa.llm.copilot")

COPILOT_TURN_TIMEOUT_S = 180.0
COPILOT_USAGE_TIMEOUT_S = 0.5
NANO_AI_UNITS_PER_CREDIT = 1_000_000_000


@dataclass
class _ClientEntry:
    client: Any
    base_directory: Path
    owns_base_directory: bool


@dataclass
class _TurnState:
    assistant_text: list[str] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    content_filter_triggered: bool = False
    usage_changed: asyncio.Event = field(default_factory=asyncio.Event)


@dataclass
class _ConversationState:
    session: Any
    event_queue: asyncio.Queue[tuple[str, Any]]
    turn_state: _TurnState
    pending_results: dict[str, asyncio.Future[str]] = field(default_factory=dict)
    pending_changed: asyncio.Event = field(default_factory=asyncio.Event)
    last_tool_ids: set[str] = field(default_factory=set)
    delivered_result_ids: set[str] = field(default_factory=set)
    last_message_count: int = 0
    waiting_for_prompt: bool = False
    unsubscribe: Callable[[], None] | None = None
    # Diagnostics only — lets slow/timed-out turns be attributed to a specific
    # session age and turn number instead of guessing from message-list size.
    created_monotonic: float = field(default_factory=time.monotonic)
    turn_count: int = 0


_clients: dict[str, _ClientEntry] = {}
_clients_lock = asyncio.Lock()
_conversations: dict[int, _ConversationState] = {}

_COPILOT_ENV_ALLOWLIST = (
    "PATH",
    "SYSTEMROOT",
    "HOME",
    "USER",
    "TMPDIR",
    "SHELL",
    "LANG",
    "LC_ALL",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "NODE_EXTRA_CA_CERTS",
    "COPILOT_GITHUB_TOKEN",
    "GH_TOKEN",
    "GITHUB_TOKEN",
)


def _copilot_home() -> Path:
    """Return the Copilot CLI home containing its selected account."""
    configured = (os.environ.get("COPILOT_HOME") or "").strip()
    return Path(configured).expanduser() if configured else Path.home() / ".copilot"


def _client_key(config: LLMConfig, proxy_url: str | None) -> str:
    username = (getattr(config, "username", None) or "").strip()
    token_marker = config.api_key or (
        f"copilot-user:{username.casefold()}:{_copilot_home()}"
        if username
        else f"logged-in-user:{_copilot_home()}"
    )
    material = f"{token_marker}\0{proxy_url or ''}".encode()
    return hashlib.sha256(material).hexdigest()


def _copilot_account_token(username: str) -> str:
    """Read one named Copilot CLI account credential without exposing it."""
    database = _copilot_home() / "data.db"
    if not database.is_file():
        raise RuntimeError(
            "Copilot CLI account data was not found. Sign in with Copilot CLI first."
        )
    try:
        connection = sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)
        try:
            row = connection.execute(
                "SELECT access_token FROM accounts "
                "WHERE login = ? COLLATE NOCASE AND kind = 'github' "
                "ORDER BY is_default DESC LIMIT 1",
                (username,),
            ).fetchone()
        finally:
            connection.close()
    except sqlite3.Error as exc:
        raise RuntimeError("Unable to read Copilot CLI account data.") from exc
    if row is None:
        raise RuntimeError(
            f"Copilot CLI account '{username}' was not found. Use /user in Copilot CLI "
            "to confirm the account login."
        )
    token = str(row[0] or "").strip()
    if not token:
        raise RuntimeError(
            f"Copilot CLI account '{username}' has no stored credential. Sign in to "
            "that account again or configure a GitHub token in AESPA."
        )
    return token


async def _get_client(config: LLMConfig, proxy_url: str | None) -> Any:
    """Return a shared SDK client without exposing the AESPA repository context."""
    key = _client_key(config, proxy_url)
    entry = _clients.get(key)
    if entry is not None:
        return entry.client

    async with _clients_lock:
        entry = _clients.get(key)
        if entry is not None:
            return entry.client

        try:
            from copilot import CopilotClient
        except ImportError as exc:  # pragma: no cover - dependency is required
            raise RuntimeError(
                "GitHub Copilot support requires the github-copilot-sdk package."
            ) from exc

        username = (getattr(config, "username", None) or "").strip()
        token = (config.api_key or "").strip() or None
        if token is None and username:
            token = _copilot_account_token(username)
        # With no explicit token or username, use Copilot CLI's selected account.
        # Its account selection lives under COPILOT_HOME, so that path must stay
        # visible. Named accounts and explicit tokens get temporary storage.
        owns_base_directory = token is not None
        base_directory = (
            Path(tempfile.mkdtemp(prefix="aespa-copilot-"))
            if owns_base_directory
            else _copilot_home()
        )
        client_mode = "empty" if token is not None else "copilot-cli"
        # Do not copy AESPA/provider/target environment variables into the CLI.
        # It receives only what it needs to start and authenticate to Copilot.
        child_env = {
            name: os.environ[name]
            for name in _COPILOT_ENV_ALLOWLIST
            if name in os.environ
        }
        if proxy_url:
            child_env["HTTP_PROXY"] = proxy_url
            child_env["HTTPS_PROXY"] = proxy_url

        client = CopilotClient(
            mode=client_mode,
            base_directory=str(base_directory),
            working_directory=tempfile.gettempdir(),
            github_token=token,
            use_logged_in_user=token is None,
            env=child_env,
            log_level="warning",
        )
        try:
            await client.start()
        except Exception:
            if owns_base_directory:
                shutil.rmtree(base_directory, ignore_errors=True)
            log.exception("Unable to start the GitHub Copilot SDK runtime")
            raise
        _clients[key] = _ClientEntry(
            client=client,
            base_directory=base_directory,
            owns_base_directory=owns_base_directory,
        )
        return client


async def close_clients() -> None:
    """Stop all shared Copilot CLI processes during application shutdown."""
    for key in list(_conversations):
        await _close_conversation_key(key)
    async with _clients_lock:
        entries = list(_clients.values())
        _clients.clear()
    for entry in entries:
        try:
            await entry.client.stop()
        except Exception:
            log.debug("Failed to stop a Copilot SDK client", exc_info=True)
        if entry.owns_base_directory:
            shutil.rmtree(entry.base_directory, ignore_errors=True)


async def discover_models(proxy_url: str | None = None) -> list[str]:
    """Return model IDs available through the GitHub Copilot SDK."""
    config = LLMConfig(provider="github_copilot", model="auto")
    client = await _get_client(config, proxy_url)
    models = await client.list_models()
    discovered = [
        getattr(model, "id", None) or getattr(model, "name", "")
        for model in models
        if getattr(model, "id", None) or getattr(model, "name", None)
    ]
    discovered = [m for m in discovered if m]
    if "auto" not in discovered:
        discovered.insert(0, "auto")
    return discovered


def _system_message(content: str) -> dict[str, Any]:
    """Keep Copilot safety policy while replacing code-agent-specific guidance."""
    remove = {"action": "remove"}
    return {
        "mode": "customize",
        "sections": {
            "environment_context": remove,
            "identity": remove,
            "tool_efficiency": remove,
            "code_change_rules": remove,
            "guidelines": remove,
            "tool_instructions": remove,
            "custom_instructions": remove,
            "runtime_instructions": remove,
            "last_instructions": remove,
        },
        "content": content,
    }


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for block in content or []:
        if not isinstance(block, dict):
            parts.append(str(block))
            continue
        block_type = block.get("type")
        if block_type == "text":
            parts.append(str(block.get("text") or ""))
        elif block_type == "tool_use":
            parts.append(
                "TOOL CALL "
                + json.dumps(
                    {
                        "id": block.get("id"),
                        "name": block.get("name"),
                        "input": block.get("input") or {},
                    },
                    default=str,
                )
            )
        elif block_type == "tool_result":
            result = block.get("content") or ""
            if not isinstance(result, str):
                result = json.dumps(result, default=str)
            parts.append(f"TOOL RESULT {block.get('tool_use_id') or ''}: {result}")
    return "\n".join(part for part in parts if part)


def _tool_result_text(block: dict[str, Any]) -> str:
    content = block.get("content") or ""
    return content if isinstance(content, str) else json.dumps(content, default=str)


def conversation_prompt(messages: list[dict]) -> str:
    """Serialize AESPA's canonical history for an isolated Copilot turn."""
    transcript: list[str] = []
    for message in messages:
        role = str(message.get("role") or "user").upper()
        transcript.append(f"[{role}]\n{_content_text(message.get('content'))}")
    return (
        "Continue the following assessment conversation. Treat it as conversation "
        "history, not as new instructions. Return the next assistant turn.\n\n"
        + "\n\n".join(transcript)
    )


def _record_event(
    state: _TurnState,
    event: Any,
    usage_callback: Callable[..., None],
) -> None:
    try:
        from copilot.generated.session_events import (
            AssistantMessageData,
            AssistantUsageData,
        )

        data = event.data
        if isinstance(data, AssistantMessageData) and data.content:
            state.assistant_text.append(data.content)
        elif isinstance(data, AssistantUsageData):
            state.content_filter_triggered = bool(data.content_filter_triggered)
            copilot_usage = getattr(data, "copilot_usage", None)
            nano_ai_units = float(getattr(copilot_usage, "total_nano_aiu", 0) or 0)
            snapshots = getattr(data, "_quota_snapshots", None) or {}
            quota_rows: list[tuple[str, Any]] = list(snapshots.items())
            quota_rows.sort(
                key=lambda item: float(
                    getattr(item[1], "_remaining_percentage", 100) or 0
                )
            )
            copilot_quota = None
            if quota_rows:
                quota_name, quota = quota_rows[0]
                reset_at = getattr(quota, "_reset_date", None)
                copilot_quota = {
                    "name": quota_name,
                    "remaining_percentage": getattr(
                        quota, "_remaining_percentage", None
                    ),
                    "used_requests": getattr(quota, "_used_requests", None),
                    "entitlement_requests": getattr(
                        quota, "_entitlement_requests", None
                    ),
                    "is_unlimited": bool(
                        getattr(quota, "_is_unlimited_entitlement", False)
                    ),
                    "token_based_billing": getattr(quota, "_token_based_billing", None),
                    "reset_at": reset_at.isoformat() if reset_at else None,
                    "observed_at": datetime.now(timezone.utc).isoformat(),
                }
            legacy_billing = bool(quota_rows) and all(
                getattr(snapshot, "_token_based_billing", None) is False
                for _, snapshot in quota_rows
            )
            state.usage_changed.set()
            usage_callback(
                data.model,
                data.input_tokens or 0,
                data.output_tokens or 0,
                data.cache_read_tokens or 0,
                data.cache_write_tokens or 0,
                ai_credits=nano_ai_units / NANO_AI_UNITS_PER_CREDIT,
                premium_requests=float(data.cost or 0) if legacy_billing else 0,
                requests=1,
                copilot_quota=copilot_quota,
            )
    except Exception:
        log.debug("Unable to process a Copilot session event", exc_info=True)


async def _wait_for_usage(state: _TurnState) -> None:
    """Let the ephemeral usage event arrive before a turn is returned or closed."""
    try:
        await asyncio.wait_for(
            state.usage_changed.wait(), timeout=COPILOT_USAGE_TIMEOUT_S
        )
    except TimeoutError:
        log.debug("Copilot did not emit usage data for this model call")


async def _create_session(
    config: LLMConfig,
    system_message: str,
    tools: list[Any],
    available_tools: Any,
    state: _TurnState,
    usage_callback: Callable[..., None],
    proxy_url: str | None,
) -> tuple[Any, Any]:
    from copilot.session import PermissionHandler

    client = await _get_client(config, proxy_url)
    session = await client.create_session(
        model=config.model or "auto",
        tools=tools,
        available_tools=available_tools,
        system_message=_system_message(system_message),
        on_permission_request=PermissionHandler.approve_all,
        streaming=False,
        skip_custom_instructions=True,
        custom_agents_local_only=True,
        coauthor_enabled=False,
        manage_schedule_enabled=False,
        enable_config_discovery=False,
        skip_embedding_retrieval=True,
        embedding_cache_storage="in-memory",
        mcp_oauth_token_storage="in-memory",
        enable_skills=False,
        enable_file_hooks=False,
        enable_host_git_operations=False,
        enable_session_store=False,
        enable_session_telemetry=False,
        enable_on_demand_instruction_discovery=False,
        memory={"enabled": False},
        on_event=lambda event: _record_event(state, event, usage_callback),
    )
    return client, session


async def plain_completion(
    config: LLMConfig,
    prompt: str,
    screenshot_b64: str | None,
    usage_callback: Callable[..., None],
    proxy_url: str | None = None,
) -> str:
    """Run a text/vision completion through the user's Copilot entitlement."""
    from copilot import ToolSet

    state = _TurnState()
    _client, session = await _create_session(
        config,
        "Follow the user's instructions and return only the requested result.",
        [],
        ToolSet(),
        state,
        usage_callback,
        proxy_url,
    )
    attachments = None
    if screenshot_b64:
        attachments = [
            {
                "type": "blob",
                "data": screenshot_b64,
                "mimeType": "image/png",
                "displayName": "aespa-page.png",
            }
        ]
    try:
        state.usage_changed.clear()
        _t0 = time.monotonic()
        try:
            response = await session.send_and_wait(
                prompt,
                attachments=attachments,
                timeout=COPILOT_TURN_TIMEOUT_S,
            )
        except TimeoutError as exc:
            _elapsed = time.monotonic() - _t0
            log.warning(
                "copilot plain_completion: timed out waiting %.1fs (limit %.1fs) "
                "for the model response — prompt_chars=%d",
                _elapsed,
                COPILOT_TURN_TIMEOUT_S,
                len(prompt),
            )
            raise TimeoutError(
                f"GitHub Copilot did not respond within {COPILOT_TURN_TIMEOUT_S:.0f}s "
                f"(waited {_elapsed:.1f}s; prompt was {len(prompt)} characters)"
            ) from exc
        _elapsed = time.monotonic() - _t0
        if _elapsed > 30.0:
            log.info(
                "copilot plain_completion: model response took %.1fs (prompt_chars=%d)",
                _elapsed,
                len(prompt),
            )
        await _wait_for_usage(state)
        if state.content_filter_triggered:
            raise RuntimeError("content_filter: GitHub Copilot refused the request")
        if response is not None and getattr(response.data, "content", None):
            return str(response.data.content)
        return state.assistant_text[-1] if state.assistant_text else ""
    finally:
        await session.disconnect()


async def completion_with_tools(
    config: LLMConfig,
    system_message: str,
    messages: list[dict],
    tools: list[dict],
    usage_callback: Callable[..., None],
    proxy_url: str | None = None,
    _retry_on_timeout: bool = True,
) -> tuple[list[dict], str, list[dict]]:
    """Advance one persistent Copilot conversation to its next model turn.

    The SDK session remains alive while AESPA executes a requested tool. On the
    next call, the matching AESPA result is delivered to the suspended SDK tool
    handler and Copilot continues in the same conversation.

    ``_retry_on_timeout``: internal — a turn that times out waiting for the SDK
    session (see ``COPILOT_TURN_TIMEOUT_S``) is far more often a stalled
    session/backend hiccup than a genuinely un-answerable prompt (prior turns
    on the same session typically responded in seconds). Rather than failing
    the whole scan on one flaky turn, the stale session is discarded and the
    turn is retried exactly once against a brand-new session, replaying the
    full message history as the opening prompt (the same path used for a
    checkpoint resume). Sets this to False on the retry to bound it to a
    single attempt.
    """
    from copilot import ToolSet
    from copilot.tools import Tool, ToolResult

    key = id(messages)
    conversation = _conversations.get(key)
    is_new_session = conversation is None
    if conversation is None:
        turn_state = _TurnState()
        holder: dict[str, _ConversationState] = {}

        async def execute(invocation: Any) -> Any:
            current = holder["conversation"]
            result_future = asyncio.get_running_loop().create_future()
            current.pending_results[invocation.tool_call_id] = result_future
            current.pending_changed.set()
            try:
                result_text = await result_future
            finally:
                current.pending_results.pop(invocation.tool_call_id, None)
            return ToolResult(text_result_for_llm=result_text, result_type="success")

        sdk_tools = [
            Tool(
                name=tool["name"],
                description=tool.get("description", ""),
                parameters=tool.get("input_schema", {"type": "object"}),
                handler=execute,
                overrides_built_in_tool=True,
                skip_permission=True,
                defer="never",
            )
            for tool in tools
        ]
        _client, session = await _create_session(
            config,
            system_message,
            sdk_tools,
            ToolSet().add_custom("*"),
            turn_state,
            usage_callback,
            proxy_url,
        )
        conversation = _ConversationState(
            session=session,
            event_queue=asyncio.Queue(),
            turn_state=turn_state,
            last_message_count=len(messages),
        )
        holder["conversation"] = conversation

        def on_event(event: Any) -> None:
            try:
                from copilot.generated.session_events import (
                    AssistantMessageData,
                    SessionErrorData,
                )

                if isinstance(event.data, AssistantMessageData):
                    conversation.event_queue.put_nowait(("assistant", event.data))
                elif isinstance(event.data, SessionErrorData):
                    conversation.event_queue.put_nowait(("error", event.data))
            except Exception:
                log.debug("Unable to queue a Copilot conversation event", exc_info=True)

        conversation.unsubscribe = session.on(on_event)
        _conversations[key] = conversation
        conversation.turn_state.usage_changed.clear()
        _prompt = conversation_prompt(messages)
        log.info(
            "copilot turn: opening a new SDK session (model=%s, messages=%d, "
            "prompt_chars=%d)",
            config.model,
            len(messages),
            len(_prompt),
        )
        await session.send(_prompt)
    else:
        conversation.turn_state.usage_changed.clear()
        _deliver_start = time.monotonic()
        await _deliver_tool_results(conversation, messages)
        _deliver_elapsed = time.monotonic() - _deliver_start
        if _deliver_elapsed > 1.0:
            log.info(
                "copilot turn: delivering tool result(s) to the SDK took %.1fs "
                "(turn=%d, session_age=%.1fs)",
                _deliver_elapsed,
                conversation.turn_count + 1,
                time.monotonic() - conversation.created_monotonic,
            )
        if (
            conversation.waiting_for_prompt
            and len(messages) > conversation.last_message_count
        ):
            latest = messages[-1]
            if latest.get("role") == "user":
                await conversation.session.send(_content_text(latest.get("content")))
                conversation.waiting_for_prompt = False
                conversation.last_message_count = len(messages)

    conversation.turn_count += 1
    _turn_no = conversation.turn_count
    _wait_start = time.monotonic()
    try:
        event_type, data = await asyncio.wait_for(
            conversation.event_queue.get(), timeout=COPILOT_TURN_TIMEOUT_S
        )
    except TimeoutError as exc:
        _elapsed = time.monotonic() - _wait_start
        _session_age = time.monotonic() - conversation.created_monotonic
        log.warning(
            "copilot turn: timed out waiting %.1fs (limit %.1fs) for the model "
            "response — session_new=%s, session_age=%.1fs, turn=%d, "
            "messages=%d, pending_tool_results=%d",
            _elapsed,
            COPILOT_TURN_TIMEOUT_S,
            is_new_session,
            _session_age,
            _turn_no,
            len(messages),
            len(conversation.pending_results),
        )
        await _close_conversation_key(key)
        if _retry_on_timeout:
            log.warning(
                "copilot turn: discarding the stalled session and retrying once "
                "with a fresh session (turn=%d, messages=%d)",
                _turn_no,
                len(messages),
            )
            return await completion_with_tools(
                config,
                system_message,
                messages,
                tools,
                usage_callback,
                proxy_url,
                _retry_on_timeout=False,
            )
        raise TimeoutError(
            f"GitHub Copilot did not respond within {COPILOT_TURN_TIMEOUT_S:.0f}s "
            f"(waited {_elapsed:.1f}s; turn {_turn_no} of a session that is "
            f"{_session_age:.1f}s old, new_session={is_new_session}, "
            f"{len(messages)} messages in context; retry also timed out)"
        ) from exc
    _wait_elapsed = time.monotonic() - _wait_start
    if _wait_elapsed > 30.0:
        log.info(
            "copilot turn: model response took %.1fs (turn=%d, session_age=%.1fs, "
            "session_new=%s, messages=%d)",
            _wait_elapsed,
            _turn_no,
            time.monotonic() - conversation.created_monotonic,
            is_new_session,
            len(messages),
        )
    await _wait_for_usage(conversation.turn_state)
    if event_type == "error":
        raise RuntimeError(f"GitHub Copilot session error: {data.message or data}")
    if conversation.turn_state.content_filter_triggered:
        raise RuntimeError("content_filter: GitHub Copilot refused the request")

    blocks: list[dict] = []
    if data.content:
        blocks.append(
            {
                "type": "text",
                "id": None,
                "name": None,
                "input": None,
                "text": str(data.content),
            }
        )
    tool_requests = data.tool_requests or []
    for request in tool_requests:
        blocks.append(
            {
                "type": "tool_use",
                "id": request.tool_call_id,
                "name": request.name,
                "input": request.arguments or {},
                "text": None,
            }
        )
    conversation.last_tool_ids = {request.tool_call_id for request in tool_requests}
    conversation.last_message_count = len(messages)
    conversation.waiting_for_prompt = not bool(tool_requests)
    stop_reason = "tool_use" if tool_requests else "end_turn"
    return blocks, stop_reason, list(blocks)


async def _deliver_tool_results(
    conversation: _ConversationState, messages: list[dict]
) -> None:
    results: dict[str, str] = {}
    for message in reversed(messages):
        if message.get("role") != "user" or not isinstance(
            message.get("content"), list
        ):
            continue
        for block in message["content"]:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                tool_id = str(block.get("tool_use_id") or "")
                if tool_id and tool_id not in conversation.delivered_result_ids:
                    results[tool_id] = _tool_result_text(block)
        if results:
            break
    expected = conversation.last_tool_ids.intersection(results)
    if not expected:
        return
    _total_chars = sum(len(results[tool_id]) for tool_id in expected)
    if _total_chars > 20_000:
        log.info(
            "copilot turn: delivering %d tool result(s) totalling %d chars",
            len(expected),
            _total_chars,
        )

    loop = asyncio.get_running_loop()
    deadline = loop.time() + 5.0
    while not expected.issubset(conversation.pending_results):
        remaining = deadline - loop.time()
        if remaining <= 0:
            missing = sorted(expected.difference(conversation.pending_results))
            raise RuntimeError(
                f"Copilot tool handlers did not become ready: {', '.join(missing)}"
            )
        conversation.pending_changed.clear()
        await asyncio.wait_for(conversation.pending_changed.wait(), timeout=remaining)

    for tool_id in expected:
        future = conversation.pending_results[tool_id]
        if not future.done():
            future.set_result(results[tool_id])
        conversation.delivered_result_ids.add(tool_id)
    conversation.last_message_count = len(messages)


async def close_conversation(messages: list[dict]) -> None:
    """Release the persistent SDK session associated with an AESPA message list."""
    await _close_conversation_key(id(messages))


async def _close_conversation_key(key: int) -> None:
    conversation = _conversations.pop(key, None)
    if conversation is None:
        return
    if conversation.unsubscribe is not None:
        try:
            conversation.unsubscribe()
        except Exception:
            log.debug("Failed to unsubscribe Copilot session events", exc_info=True)
    for future in conversation.pending_results.values():
        if not future.done():
            future.cancel()
    try:
        await conversation.session.abort()
    except Exception:
        pass
    try:
        await conversation.session.disconnect()
    except Exception:
        log.debug("Failed to disconnect a Copilot conversation", exc_info=True)
