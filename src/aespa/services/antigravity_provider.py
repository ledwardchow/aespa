"""Google Antigravity CLI/SDK adapter for AESPA's provider-neutral LLM interface."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from aespa.models import LLMConfig

log = logging.getLogger("aespa.llm.antigravity")

ANTIGRAVITY_TURN_TIMEOUT_S = 600.0
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
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "NO_PROXY",
)

KNOWN_MODELS = [
    "Gemini 3.7 Flash (High)",
    "Gemini 3.7 Flash (Medium)",
    "Gemini 3.7 Flash (Low)",
    "Gemini 3.6 Flash (High)",
    "Gemini 3.6 Flash (Medium)",
    "Gemini 3.6 Flash (Low)",
    "Gemini 3.5 Flash (High)",
    "Gemini 3.5 Flash (Medium)",
    "Gemini 3.5 Flash (Low)",
    "Gemini 3.1 Pro (High)",
    "Gemini 3.1 Pro (Low)",
    "Claude Sonnet 4.6 (Thinking)",
    "Claude Opus 4.6 (Thinking)",
    "GPT-OSS 120B (Medium)",
]

MODEL_ALIASES: dict[str, str] = {
    "auto": "Gemini 3.7 Flash (High)",
    "gemini-3.7-flash": "Gemini 3.7 Flash (High)",
    "gemini-3.7-flash-high": "Gemini 3.7 Flash (High)",
    "gemini-3.7-flash-medium": "Gemini 3.7 Flash (Medium)",
    "gemini-3.7-flash-low": "Gemini 3.7 Flash (Low)",
    "gemini-3.7-flash-thinking": "Gemini 3.7 Flash (High)",
    "gemini 3.7 flash": "Gemini 3.7 Flash (High)",
    "gemini-3.6-flash": "Gemini 3.6 Flash (High)",
    "gemini-3.6-flash-high": "Gemini 3.6 Flash (High)",
    "gemini-3.6-flash-medium": "Gemini 3.6 Flash (Medium)",
    "gemini-3.6-flash-low": "Gemini 3.6 Flash (Low)",
    "gemini 3.6 flash": "Gemini 3.6 Flash (High)",
    "gemini-3.5-flash": "Gemini 3.5 Flash (High)",
    "gemini-3.5-flash-high": "Gemini 3.5 Flash (High)",
    "gemini-3.5-flash-medium": "Gemini 3.5 Flash (Medium)",
    "gemini-3.5-flash-low": "Gemini 3.5 Flash (Low)",
    "gemini 3.5 flash": "Gemini 3.5 Flash (High)",
    "gemini-3.1-pro": "Gemini 3.1 Pro (High)",
    "gemini-3.1-pro-high": "Gemini 3.1 Pro (High)",
    "gemini-3.1-pro-low": "Gemini 3.1 Pro (Low)",
    "gemini 3.1 pro": "Gemini 3.1 Pro (High)",
    "gemini-2.5-pro": "Gemini 3.1 Pro (High)",
    "gemini-2.5-flash": "Gemini 3.7 Flash (High)",
    "claude-sonnet-4.6": "Claude Sonnet 4.6 (Thinking)",
    "claude-sonnet-4-6": "Claude Sonnet 4.6 (Thinking)",
    "claude-opus-4.6": "Claude Opus 4.6 (Thinking)",
    "claude-opus-4-6": "Claude Opus 4.6 (Thinking)",
    "gpt-oss-120b": "GPT-OSS 120B (Medium)",
    "gpt-oss-120b-medium": "GPT-OSS 120B (Medium)",
}

_CANONICAL_MAP = {m.casefold(): m for m in KNOWN_MODELS}


class AntigravityUnavailableError(RuntimeError):
    """Antigravity CLI is not installed, signed in, or compatible with AESPA."""


class AntigravityQuotaError(RuntimeError):
    """The Google AI Pro / Antigravity allowance or rate limit has been exhausted."""

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


def _workspace_directory() -> Path:
    """Return an isolated temporary workspace for AESPA Antigravity executions."""
    directory = Path(tempfile.gettempdir()) / "aespa-antigravity-workspace"
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    return directory


def _child_env(proxy_url: str | None = None) -> dict[str, str]:
    env = {name: os.environ[name] for name in _ENV_ALLOWLIST if name in os.environ}
    if proxy_url:
        env["HTTP_PROXY"] = proxy_url
        env["HTTPS_PROXY"] = proxy_url
    return env


def _find_agy_executable() -> str:
    candidates = [
        shutil.which("agy"),
        os.path.expanduser("~/.local/bin/agy"),
        "/usr/local/bin/agy",
        "/opt/homebrew/bin/agy",
    ]
    for cand in candidates:
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    raise AntigravityUnavailableError(
        "Antigravity CLI ('agy') was not found. Install and sign in to Antigravity first."
    )


def _resolve_model(model_name: str | None) -> str:
    if not model_name or not model_name.strip():
        return "Gemini 3.7 Flash (High)"
    raw = model_name.strip()
    folded = raw.casefold()
    if folded in _CANONICAL_MAP:
        return _CANONICAL_MAP[folded]
    if folded in MODEL_ALIASES:
        return MODEL_ALIASES[folded]
    for canonical in KNOWN_MODELS:
        if folded in canonical.casefold():
            return canonical
    return raw


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for block in content or []:
        if not isinstance(block, dict):
            continue
        block_type = block.get("type")
        if block_type == "text":
            parts.append(str(block.get("text") or ""))
        elif block_type == "tool_use":
            parts.append(
                f"[Tool call: {block.get('name') or 'unknown'} "
                f"{json.dumps(block.get('input') or {}, default=str)}]"
            )
        elif block_type == "tool_result":
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


_TRANSIENT_NETWORK_MARKERS = (
    "i/o timeout",
    "dial tcp",
    "connection reset",
    "temporary failure in name resolution",
    "eligibility check failed",
    "network is unreachable",
    "broken pipe",
    "handshake timeout",
    "context deadline exceeded",
)


_EXECUTION_LOCK = asyncio.Lock()


async def plain_completion(
    config: LLMConfig,
    prompt: str,
    screenshot_b64: str | None = None,
    usage_callback: Callable[..., None] | None = None,
    proxy_url: str | None = None,
) -> str:
    """Execute a non-interactive completion via isolated Antigravity CLI print mode."""
    executable = _find_agy_executable()
    model = _resolve_model(config.model)
    workspace = _workspace_directory()
    env = _child_env(proxy_url)
    log_file = workspace / "cli.log"

    cmd = [
        executable,
        "--print",
        prompt,
        "--model",
        model,
        "--disable-slash-commands",
        "--log-file",
        str(log_file),
        "--output-format",
        "json",
    ]
    if config.reasoning_effort in {"low", "medium", "high"}:
        cmd.extend(["--effort", config.reasoning_effort])

    max_retries = 2

    async with _EXECUTION_LOCK:
        for attempt in range(max_retries + 1):
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(workspace),
                env=env,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=ANTIGRAVITY_TURN_TIMEOUT_S
                )
            except TimeoutError as exc:
                proc.kill()
                await proc.wait()
                raise TimeoutError("Antigravity turn timed out after 600s") from exc

            raw_stdout = stdout.decode("utf-8", errors="replace").strip()
            raw_stderr = stderr.decode("utf-8", errors="replace").strip()

            if proc.returncode != 0:
                err_detail = raw_stderr or raw_stdout
                if any(
                    marker in err_detail.lower()
                    for marker in (
                        "quota",
                        "rate limit",
                        "resource_exhausted",
                        "too many requests",
                        "429",
                    )
                ):
                    raise AntigravityQuotaError(
                        f"Antigravity quota limit exceeded: {err_detail[:400]}"
                    )
                if attempt < max_retries and any(
                    marker in err_detail.lower()
                    for marker in _TRANSIENT_NETWORK_MARKERS
                ):
                    log.info(
                        "Antigravity CLI transient network failure on attempt %d/%d; retrying in %0.1fs: %s",
                        attempt + 1,
                        max_retries + 1,
                        1.5 * (attempt + 1),
                        err_detail[:200],
                    )
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
                raise AntigravityUnavailableError(
                    f"Antigravity CLI execution failed: {err_detail[:400]}"
                )

            try:
                data = json.loads(raw_stdout)
            except json.JSONDecodeError:
                return raw_stdout

            response_text = str(data.get("response") or "").strip()

            if data.get("status") == "ERROR":
                err_msg = data.get("error") or "Unknown error"
                if any(
                    marker in err_msg.lower()
                    for marker in (
                        "quota",
                        "rate limit",
                        "resource_exhausted",
                        "too many requests",
                        "429",
                    )
                ):
                    raise AntigravityQuotaError(
                        f"Antigravity quota limit exceeded: {err_msg}"
                    )
                if not response_text:
                    if attempt < max_retries and any(
                        marker in err_msg.lower()
                        for marker in _TRANSIENT_NETWORK_MARKERS
                    ):
                        log.info(
                            "Antigravity CLI transient error on attempt %d/%d; retrying in %0.1fs: %s",
                            attempt + 1,
                            max_retries + 1,
                            1.5 * (attempt + 1),
                            err_msg[:200],
                        )
                        await asyncio.sleep(1.5 * (attempt + 1))
                        continue
                    raise AntigravityUnavailableError(f"Antigravity error: {err_msg}")
                log.debug(
                    "Antigravity returned response with non-fatal notice: %s", err_msg
                )
            usage = data.get("usage") or {}

            if usage_callback:
                input_tokens = int(usage.get("input_tokens") or 0)
                output_tokens = int(usage.get("output_tokens") or 0)
                cache_read_tokens = int(usage.get("cache_read_tokens") or 0)
                thinking_tokens = int(usage.get("thinking_tokens") or 0)
                usage_callback(
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cache_read_tokens=cache_read_tokens,
                    thinking_tokens=thinking_tokens,
                )

            return response_text

        raise AntigravityUnavailableError("Antigravity CLI failed after retries")


def _parse_tool_response(
    raw_text: str, tools: list[dict]
) -> tuple[list[dict], str, list[dict]]:
    """Parse raw text from model into Anthropic-format content blocks and stop_reason."""
    tool_names = {t.get("name") for t in tools if t.get("name")}
    blocks: list[dict] = []

    # Match JSON blocks in markdown code blocks: ```json ... ``` or ``` ... ```
    pattern = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
    matches = list(pattern.finditer(raw_text))

    found_tool = False
    last_end = 0

    for match in matches:
        json_str = match.group(1)
        try:
            parsed = json.loads(json_str)
        except Exception:
            continue

        if isinstance(parsed, dict):
            name = parsed.get("name") or parsed.get("tool") or parsed.get("action")
            inp = (
                parsed.get("arguments")
                or parsed.get("input")
                or parsed.get("parameters")
                or {}
            )
            if name in tool_names:
                text_before = raw_text[last_end : match.start()].strip()
                if text_before:
                    blocks.append({"type": "text", "text": text_before})
                call_id = f"call_{uuid.uuid4().hex[:8]}"
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": call_id,
                        "name": name,
                        "input": inp if isinstance(inp, dict) else {},
                        "text": None,
                    }
                )
                last_end = match.end()
                found_tool = True

    if not found_tool:
        # Check if the entire raw text is a JSON object
        stripped = raw_text.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, dict):
                    name = (
                        parsed.get("name") or parsed.get("tool") or parsed.get("action")
                    )
                    inp = (
                        parsed.get("arguments")
                        or parsed.get("input")
                        or parsed.get("parameters")
                        or {}
                    )
                    if name in tool_names:
                        call_id = f"call_{uuid.uuid4().hex[:8]}"
                        blocks.append(
                            {
                                "type": "tool_use",
                                "id": call_id,
                                "name": name,
                                "input": inp if isinstance(inp, dict) else {},
                                "text": None,
                            }
                        )
                        found_tool = True
            except Exception:
                pass

    if not found_tool:
        blocks = [{"type": "text", "text": raw_text}]
        stop_reason = "end_turn"
    else:
        trailing_text = raw_text[last_end:].strip()
        if trailing_text and not trailing_text.startswith("```"):
            blocks.append({"type": "text", "text": trailing_text})
        stop_reason = "tool_use"

    return blocks, stop_reason, blocks


async def completion_with_tools(
    config: LLMConfig,
    system_message: str,
    messages: list[dict],
    tools: list[dict],
    usage_callback: Callable[..., None] | None = None,
    proxy_url: str | None = None,
) -> tuple[list[dict], str, list[dict]]:
    """Execute a tool-enabled turn by encoding tool schemas and history into the prompt."""
    tools_formatted = json.dumps(
        [
            {
                "name": t.get("name"),
                "description": t.get("description", ""),
                "parameters": t.get("input_schema", {}),
            }
            for t in tools
        ],
        indent=2,
    )

    combined_prompt = (
        f"{system_message}\n\n"
        f"Available tools (respond with a JSON tool call block if you need to use a tool):\n"
        f"{tools_formatted}\n\n"
        f"Conversation History:\n"
        f"{_conversation_prompt(messages)}"
    )

    raw_text = await plain_completion(
        config=config,
        prompt=combined_prompt,
        usage_callback=usage_callback,
        proxy_url=proxy_url,
    )

    return _parse_tool_response(raw_text, tools)


async def close_conversation(messages: list[dict]) -> None:
    """No-op cleanup for ephemeral Antigravity turns."""
    pass


async def close_clients() -> None:
    """Clean up any temporary workspace state upon server shutdown."""
    workspace = _workspace_directory()
    try:
        for item in workspace.glob("*"):
            if item.is_file():
                item.unlink(missing_ok=True)
    except Exception:
        log.debug("Failed to clean up Antigravity temporary workspace", exc_info=True)


async def discover_models(proxy_url: str | None = None) -> list[str]:
    """Return model IDs available through Antigravity CLI."""
    return [item["id"] for item in await discover_model_options(proxy_url=proxy_url)]


async def discover_model_options(proxy_url: str | None = None) -> list[dict[str, Any]]:
    """Return Antigravity display models and their CLI-supported levels."""
    default_models = [
        "auto",
        "Gemini 3.7 Flash (High)",
        "Gemini 3.7 Flash (Medium)",
        "Gemini 3.7 Flash (Low)",
        "Gemini 3.6 Flash (High)",
        "Gemini 3.6 Flash (Medium)",
        "Gemini 3.5 Flash (High)",
        "Gemini 3.1 Pro (High)",
        "Gemini 3.1 Pro (Low)",
        "Claude Sonnet 4.6 (Thinking)",
        "Claude Opus 4.6 (Thinking)",
        "GPT-OSS 120B (Medium)",
    ]
    options = []
    for model in default_models:
        level = next(
            (
                candidate
                for candidate in ("low", "medium", "high")
                if f"({candidate.title()})" in model
            ),
            None,
        )
        if level:
            capability = {"supported_efforts": [level]}
        elif "(Thinking)" in model:
            capability = {"supported_efforts": ["low", "medium", "high"]}
        else:
            capability = {}
        options.append({"id": model, **capability})
    return options
