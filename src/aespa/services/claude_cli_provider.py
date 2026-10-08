"""Claude Code CLI adapter for AESPA's LLM interface."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any, Callable

from aespa.models import LLMConfig

TURN_TIMEOUT_S = 600
DEFAULT_MODELS = [
    "sonnet",
    "opus",
    "haiku",
    "mythos",
    "mythos-5",
    "claude-mythos-5",
]
MODEL_ALIASES = {
    "mythos": "claude-mythos-5",
    "mythos-5": "claude-mythos-5",
}
_ENV_KEYS = (
    "PATH",
    "HOME",
    "XDG_CONFIG_HOME",
    "XDG_CACHE_HOME",
    "CLAUDE_CONFIG_DIR",
    "USERPROFILE",
    "APPDATA",
    "LOCALAPPDATA",
    "SYSTEMROOT",
    "TMPDIR",
    "TEMP",
    "TMP",
    "LANG",
    "LC_ALL",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "NODE_EXTRA_CA_CERTS",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "NO_PROXY",
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_MODEL",
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX",
    "CLAUDE_CODE_USE_FOUNDRY",
    "AWS_PROFILE",
    "AWS_REGION",
    "CLOUD_ML_REGION",
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
)


def _executable() -> str:
    candidates = (shutil.which("claude"), str(Path.home() / ".local/bin/claude"))
    for candidate in candidates:
        if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    raise RuntimeError(
        "Claude CLI was not found. Install Claude Code and sign in first."
    )


def _text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return str(content or "")
    parts = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            parts.append(str(block.get("text") or ""))
        elif block.get("type") == "tool_use":
            parts.append(
                f"Tool call {block.get('id')}: {block.get('name')} {json.dumps(block.get('input') or {})}"
            )
        elif block.get("type") == "tool_result":
            parts.append(
                f"Tool result {block.get('tool_use_id')}: {block.get('content')}"
            )
    return "\n".join(parts)


def _usage(result: dict, model: str, callback: Callable[..., None] | None) -> None:
    if not callback:
        return
    usage = result.get("usage") or {}
    callback(
        model,
        int(usage.get("input_tokens") or 0),
        int(usage.get("output_tokens") or 0),
        int(usage.get("cache_read_input_tokens") or 0),
        int(usage.get("cache_creation_input_tokens") or 0),
    )


async def _invoke(
    config: LLMConfig,
    prompt: str,
    *,
    system: str | None = None,
    schema: dict | None = None,
    callback: Callable[..., None] | None = None,
    proxy_url: str | None = None,
) -> dict:
    env = {key: os.environ[key] for key in _ENV_KEYS if key in os.environ}
    if proxy_url:
        env["HTTP_PROXY"] = proxy_url
        env["HTTPS_PROXY"] = proxy_url
    # Running outside the target repository also prevents project instructions
    # or MCP settings from becoming part of a scan request.
    with tempfile.TemporaryDirectory(prefix="aespa-claude-") as workspace:
        cmd = [
            _executable(),
            "--print",
            "--output-format",
            "json",
            "--safe-mode",
            "--strict-mcp-config",
            "--tools",
            "",
            "--disable-slash-commands",
            "--no-session-persistence",
            "--permission-mode",
            "dontAsk",
            "--model",
            MODEL_ALIASES.get(config.model, config.model) or "sonnet",
        ]
        if system:
            cmd.extend(["--system-prompt", system])
        if schema:
            cmd.extend(["--json-schema", json.dumps(schema)])
        if config.reasoning_effort in {"low", "medium", "high", "xhigh", "max"}:
            cmd.extend(["--effort", config.reasoning_effort])
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=workspace,
            env=env,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(prompt.encode()), timeout=TURN_TIMEOUT_S
            )
        except (asyncio.TimeoutError, asyncio.CancelledError):
            process.kill()
            await process.communicate()
            raise
    if process.returncode:
        detail = stderr.decode(errors="replace").strip()[-1000:]
        raise RuntimeError(
            f"Claude CLI failed: {detail or f'exit {process.returncode}'}"
        )
    try:
        result = json.loads(stdout)
    except (ValueError, UnicodeDecodeError) as exc:
        raise RuntimeError("Claude CLI returned invalid JSON") from exc
    if result.get("is_error"):
        raise RuntimeError(str(result.get("result") or "Claude CLI request failed"))
    _usage(result, MODEL_ALIASES.get(config.model, config.model) or "sonnet", callback)
    return result


async def plain_completion(
    config: LLMConfig,
    prompt: str,
    screenshot_b64: str | None = None,
    usage_callback: Callable[..., None] | None = None,
    proxy_url: str | None = None,
) -> str:
    if screenshot_b64:
        raise ValueError("Claude CLI provider does not support screenshots")
    result = await _invoke(config, prompt, callback=usage_callback, proxy_url=proxy_url)
    return str(result.get("result") or "")


async def completion_with_tools(
    config: LLMConfig,
    system_message: str,
    messages: list[dict],
    tools: list[dict],
    usage_callback: Callable[..., None] | None = None,
    proxy_url: str | None = None,
) -> tuple[list[dict], str, list[dict]]:
    names = {tool["name"] for tool in tools}
    schema = {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "tool_calls": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "enum": sorted(names)},
                        "input": {"type": "object"},
                    },
                    "required": ["name", "input"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["text", "tool_calls"],
        "additionalProperties": False,
    }
    tool_specs = json.dumps(tools, ensure_ascii=False)
    system = (
        f"{system_message}\n\nAvailable AESPA tools:\n{tool_specs}\n\n"
        "Return text and any AESPA tool calls in the required JSON structure. "
        "Use only listed tools. AESPA executes calls and provides the results next turn."
    )
    transcript = "\n\n".join(
        f"[{message.get('role', 'user')}]\n{_text(message.get('content'))}"
        for message in messages
    )
    result = await _invoke(
        config,
        transcript,
        system=system,
        schema=schema,
        callback=usage_callback,
        proxy_url=proxy_url,
    )
    answer = result.get("structured_output")
    if not isinstance(answer, dict):
        try:
            answer = json.loads(result.get("result") or "")
        except ValueError as exc:
            raise RuntimeError("Claude CLI returned no structured response") from exc
    blocks: list[dict] = []
    if answer.get("text"):
        blocks.append({"type": "text", "text": str(answer["text"])})
    for call in answer.get("tool_calls") or []:
        if (
            not isinstance(call, dict)
            or call.get("name") not in names
            or not isinstance(call.get("input"), dict)
        ):
            raise RuntimeError("Claude CLI returned an invalid AESPA tool call")
        blocks.append(
            {
                "type": "tool_use",
                "id": f"toolu_{uuid.uuid4().hex}",
                "name": call["name"],
                "input": call["input"],
            }
        )
    if not blocks:
        raise RuntimeError("Claude CLI returned an empty response")
    return blocks, "tool_use" if answer.get("tool_calls") else "end_turn", blocks
