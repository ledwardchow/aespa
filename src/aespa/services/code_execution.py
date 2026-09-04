"""Sandboxed agent-authored Python with AESPA-brokered HTTP access."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import shutil
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urlencode

from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import CodeExecution
from aespa.services import events as events_svc
from aespa.services.outbound_policy import validate_request
from aespa.services.settings import get_code_execution_config

log = logging.getLogger("aespa.code_execution")

PROTOCOL_VERSION = "1"
SANDBOX_UID = 65532
SANDBOX_GID = 65532
_active: dict[tuple[str, int, int], asyncio.subprocess.Process] = {}


def has_active_executions() -> bool:
    """Return whether a Python sandbox process is still running."""
    return any(process.returncode is None for process in _active.values())


class _ExecutionLimiter:
    """One process-wide limiter whose ceiling is captured by each execution."""

    def __init__(self) -> None:
        self._active = 0
        self._condition = asyncio.Condition()

    @asynccontextmanager
    async def slot(self, limit: int):
        limit = max(1, limit)
        async with self._condition:
            await self._condition.wait_for(lambda: self._active < limit)
            self._active += 1
        try:
            yield
        finally:
            async with self._condition:
                self._active -= 1
                self._condition.notify_all()


_execution_limiter = _ExecutionLimiter()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _redact(value: str, session_vault: dict[str, dict]) -> str:
    redacted = value
    secrets: set[str] = set()
    for session in session_vault.values():
        secrets.update(str(item) for item in (session.get("cookies") or {}).values())
        secrets.update(
            str(item) for item in (session.get("extra_headers") or {}).values()
        )
    for secret in sorted(
        (item for item in secrets if len(item) >= 4), key=len, reverse=True
    ):
        redacted = redacted.replace(secret, "[REDACTED]")
    return redacted


async def _run_command(*args: str, timeout: float = 5.0) -> tuple[int, str]:
    proc = None
    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return proc.returncode or 0, stdout.decode(errors="replace")[:1000]
    except (FileNotFoundError, TimeoutError, OSError) as exc:
        if proc is not None and proc.returncode is None:
            proc.kill()
            await proc.wait()
        return 127, str(exc)


def _docker_run_args(config, *, name: str, label: str) -> list[str]:
    """Build the single hardened Docker profile used by probes and executions."""
    memory = f"{config.memory_mb}m"
    return [
        "docker",
        "run",
        "--rm",
        "--name",
        name,
        "--label",
        f"com.aespa.code-execution={label}",
        "--network",
        "none",
        "--read-only",
        "--user",
        f"{SANDBOX_UID}:{SANDBOX_GID}",
        "--workdir",
        "/work",
        "--tmpfs",
        (
            "/work:rw,noexec,nosuid,nodev,"
            f"size={config.workspace_mb}m,uid={SANDBOX_UID},"
            f"gid={SANDBOX_GID},mode=0700"
        ),
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        str(config.pids_limit),
        "--memory",
        memory,
        "--memory-swap",
        memory,
        "--cpus",
        str(config.cpu_cores),
        "--ulimit",
        "nofile=64:64",
        "--env",
        "PYTHONDONTWRITEBYTECODE=1",
        "--entrypoint",
        "python",
        "-i",
        config.image_ref,
        "-I",
        "/opt/aespa_harness.py",
    ]


async def _runtime_self_test(config) -> tuple[bool, str]:
    """Exercise the exact offline launch profile and writable workspace."""
    token = uuid.uuid4().hex[:12]
    name = f"aespa-code-readiness-{token}"
    args = _docker_run_args(config, name=name, label="readiness")
    start = {
        "type": "execution.start",
        "protocol_version": PROTOCOL_VERSION,
        "execution_id": 0,
        "code": (
            "from pathlib import Path\n"
            "p = Path('/work/.aespa-readiness')\n"
            "p.write_text('ok')\n"
            "print('aespa-readiness-' + p.read_text())\n"
        ),
    }
    proc = None
    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        payload = (json.dumps(start, separators=(",", ":")) + "\n").encode()
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(payload), timeout=min(float(config.timeout_s), 10.0)
        )
        if proc.returncode != 0:
            detail = stderr.decode(errors="replace").strip()[-500:]
            return False, detail or f"runtime probe exited with code {proc.returncode}"
        frames = []
        for line in stdout.splitlines():
            try:
                frames.append(json.loads(line))
            except json.JSONDecodeError:
                return False, "runtime probe emitted an invalid protocol frame"
        terminal = next(
            (frame for frame in frames if frame.get("type") == "execution.result"),
            None,
        )
        output = b"".join(
            base64.b64decode(frame.get("data_b64") or "")
            for frame in frames
            if frame.get("type") == "stdout.chunk"
        )
        if terminal is None or terminal.get("exit_code") != 0:
            return False, "runtime probe did not return a successful terminal result"
        if b"aespa-readiness-ok" not in output:
            return False, "runtime probe could not write to its isolated workspace"
        return True, "Sandbox runtime is ready."
    except (FileNotFoundError, TimeoutError, OSError) as exc:
        if proc is not None and proc.returncode is None:
            proc.kill()
            await proc.wait()
        return False, str(exc)
    finally:
        await _run_command("docker", "rm", "-f", name, timeout=5)


async def runtime_status(config=None) -> dict[str, Any]:
    if config is None:
        with Session(get_engine()) as session:
            config = get_code_execution_config(session)
    docker_installed = shutil.which("docker") is not None
    image_present = False
    runtime_compatible = False
    detail = "Docker is not installed."
    if docker_installed:
        code, output = await _run_command(
            "docker", "image", "inspect", config.image_ref, timeout=5
        )
        image_present = code == 0
        detail = f"Sandbox image {config.image_ref!r} is not installed."
        if image_present and config.enabled:
            runtime_compatible, probe_detail = await _runtime_self_test(config)
            detail = (
                probe_detail
                if runtime_compatible
                else f"Sandbox runtime is incompatible: {probe_detail}"
            )
        else:
            runtime_compatible = image_present
        if output and not image_present:
            log.debug("Docker image readiness check: %s", output)
    available = bool(
        config.enabled and docker_installed and image_present and runtime_compatible
    )
    if not config.enabled:
        detail = "Sandboxed Python execution is disabled."
    return {
        "enabled": bool(config.enabled),
        "available": available,
        "backend": config.backend,
        "image_ref": config.image_ref,
        "docker_installed": docker_installed,
        "image_present": image_present,
        "message": detail,
    }


def list_executions(run_kind: str, run_id: int) -> list[dict[str, Any]]:
    with Session(get_engine()) as session:
        rows = list(
            session.exec(
                select(CodeExecution)
                .where(CodeExecution.run_kind == run_kind)
                .where(CodeExecution.run_id == run_id)
                .order_by(CodeExecution.id.desc())
            ).all()
        )
        return [_execution_dict(row, include_code=False) for row in rows]


def get_execution(
    run_kind: str, run_id: int, execution_id: int
) -> dict[str, Any] | None:
    with Session(get_engine()) as session:
        row = session.get(CodeExecution, execution_id)
        if row is None or row.run_kind != run_kind or row.run_id != run_id:
            return None
        return _execution_dict(row, include_code=True)


def _execution_dict(row: CodeExecution, *, include_code: bool) -> dict[str, Any]:
    value = {
        "id": row.id,
        "run_kind": row.run_kind,
        "run_id": row.run_id,
        "agent_id": row.agent_id,
        "agent_role": row.agent_role,
        "agent_step": row.agent_step,
        "purpose": row.purpose,
        "code_sha256": row.code_sha256,
        "status": row.status,
        "runtime_backend": row.runtime_backend,
        "runtime_version": row.runtime_version,
        "image_ref": row.image_ref,
        "limits": json.loads(row.limits_json or "{}"),
        "request_count": row.request_count,
        "denied_request_count": row.denied_request_count,
        "stdout_preview": row.stdout_preview,
        "stderr_preview": row.stderr_preview,
        "result": json.loads(row.result_json or "{}"),
        "exit_code": row.exit_code,
        "error_message": row.error_message,
        "created_at": row.created_at.isoformat(),
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }
    if include_code:
        value["code_redacted"] = row.code_redacted
    return value


@dataclass
class _Broker:
    run_kind: str
    run_id: int
    execution_id: int
    agent_id: str
    agent_step: int
    session_vault: dict[str, dict]
    scanner_policy: Any
    scope_check: Callable[[str], str | None]
    max_requests: int
    max_concurrent: int
    post_probe_fn: Callable | None = None
    attempt_count: int = 0
    request_count: int = 0
    denied_count: int = 0

    def __post_init__(self) -> None:
        self._budget_lock = asyncio.Lock()
        self._pace_lock = asyncio.Lock()
        self._last_request_started = 0.0

    async def _pace(self) -> None:
        delay = float(getattr(self.scanner_policy, "min_delay_s", 0.0) or 0.0)
        if delay <= 0:
            return
        async with self._pace_lock:
            loop = asyncio.get_running_loop()
            remaining = delay - (loop.time() - self._last_request_started)
            if remaining > 0:
                await asyncio.sleep(remaining)
            self._last_request_started = loop.time()

    async def _reserve(self, count: int = 1) -> str | None:
        async with self._budget_lock:
            if self.attempt_count + count > self.max_requests:
                self.denied_count += count
                return f"execution request budget exceeded ({self.max_requests})"
            self.attempt_count += count
            return None

    async def _mark_transmitted(self) -> None:
        async with self._budget_lock:
            self.request_count += 1

    @staticmethod
    def _body(spec: dict[str, Any]) -> tuple[bytes | None, dict[str, Any]]:
        if spec.get("body_b64") is not None:
            try:
                return base64.b64decode(spec["body_b64"], validate=True), {}
            except Exception as exc:
                raise ValueError(f"invalid base64 request body: {exc}") from exc
        if spec.get("body_text") is not None:
            return str(spec["body_text"]).encode(), {}
        if spec.get("json") is not None:
            data = json.dumps(spec["json"], separators=(",", ":")).encode()
            return data, {"Content-Type": "application/json"}
        if spec.get("form") is not None:
            data = urlencode(spec["form"], doseq=True).encode()
            return data, {"Content-Type": "application/x-www-form-urlencoded"}
        return None, {}

    def _session(self, label: str | None) -> tuple[str | None, dict | None]:
        if label == "anonymous":
            return "anonymous", None
        if label:
            return label, self.session_vault.get(label)
        primary = self.session_vault.get("configured_primary")
        if primary is not None:
            return "configured_primary", primary
        for candidate_label, candidate in self.session_vault.items():
            if (
                not str(candidate_label).startswith("__")
                and candidate.get("kind") != "anonymous"
            ):
                return str(candidate_label), candidate
        return None, None

    async def request(
        self,
        spec: dict[str, Any],
        *,
        batch_id: str | None = None,
        batch_index: int | None = None,
        reserved: bool = False,
    ) -> dict[str, Any]:
        if not reserved:
            budget_error = await self._reserve()
            if budget_error:
                return self._policy_error(budget_error)
        try:
            body, generated_headers = self._body(spec)
        except (TypeError, ValueError) as exc:
            self.denied_count += 1
            return self._policy_error(str(exc))
        method = str(spec.get("method") or "GET").upper()
        url = str(spec.get("url") or "").strip()
        raw_headers = spec.get("headers") or {}
        if not isinstance(raw_headers, dict):
            self.denied_count += 1
            return self._policy_error("request headers must be an object")
        headers = {**generated_headers, **raw_headers}
        decision = validate_request(
            method=method,
            url=url,
            headers=headers,
            body_size=len(body or b""),
            scanner_policy=self.scanner_policy,
            scope_check=self.scope_check,
        )
        if not decision.allowed:
            self.denied_count += 1
            return self._policy_error(decision.reason or "request denied")

        session_label, selected = self._session(spec.get("use_session"))
        if (
            spec.get("use_session")
            and selected is None
            and session_label != "anonymous"
        ):
            self.denied_count += 1
            return self._policy_error(f"unknown session label {session_label!r}")
        merged_headers = {
            "User-Agent": "AESPA-Python-Executor/1.0",
            **((selected or {}).get("extra_headers") or {}),
            **headers,
        }
        cookies = (selected or {}).get("cookies") or {}
        provenance = {
            "code_execution_id": self.execution_id,
            "batch_id": batch_id,
            "batch_index": batch_index,
            "agent_id": self.agent_id,
            "agent_step": self.agent_step,
            "owasp_category": spec.get("owasp_category"),
            "test_class": spec.get("test_class"),
            "obligation_id": spec.get("obligation_id"),
        }
        from aespa.services.scanner import _make_scanner_client, _request_scope_checked

        await self._pace()
        await self._mark_transmitted()
        started = asyncio.get_running_loop().time()
        try:
            async with _make_scanner_client(
                run_id=self.run_id if self.run_kind == "web" else None,
                api_run_id=self.run_id if self.run_kind == "api" else None,
                username=(selected or {}).get("username"),
                cookies=cookies,
                headers=merged_headers,
                timeout=float(getattr(self.scanner_policy, "request_timeout_s", 10)),
                follow_redirects=False,
                verify=False,
                source="python",
                provenance=provenance,
            ) as client:
                client.page_id = spec.get("page_id")
                client.session_label = session_label
                response, redirect_blocked = await _request_scope_checked(
                    client,
                    method,
                    url,
                    scope_check=self.scope_check,
                    content=body,
                    headers=merged_headers,
                )
                elapsed = int((asyncio.get_running_loop().time() - started) * 1000)
                raw = response.content
                captured_session_label = None
                requested_store_as = str(spec.get("store_as") or "").strip()
                if requested_store_as and response.status_code < 400:
                    from aespa.services.scanner import (
                        _extract_bearer_token_from_body,
                        _record_session,
                        _session_kind,
                    )

                    token = _extract_bearer_token_from_body(response.text)
                    response_cookies = {
                        **dict(client.cookies),
                        **dict(response.cookies),
                    }
                    captured_headers = (
                        {"Authorization": f"Bearer {token}"} if token else {}
                    )
                    if token or response_cookies:
                        label = requested_store_as[:100]
                        captured_session_label = label
                        captured = {
                            "label": label,
                            "kind": _session_kind(response_cookies, captured_headers),
                            "username": None,
                            "source": f"Python execution #{self.execution_id}",
                            "extra_headers": captured_headers,
                            "cookies": response_cookies,
                        }
                        self.session_vault[label] = captured
                        _record_session(
                            self.run_id,
                            label=label,
                            session_data=captured,
                            source="python_execution_http_response",
                            metadata={"method": method, "url": url},
                            run_kind=self.run_kind,
                        )
                read_limit = int(
                    getattr(
                        self.scanner_policy, "response_body_read_limit_bytes", 524288
                    )
                )
                returned = raw[:read_limit]
                safe_headers = {
                    key: value
                    for key, value in response.headers.items()
                    if key.lower()
                    not in {"set-cookie", "authorization", "proxy-authenticate"}
                }
                if self.post_probe_fn and spec.get("owasp_category"):
                    try:
                        self.post_probe_fn(
                            url,
                            method,
                            str(spec.get("owasp_category")),
                            test_class=str(spec.get("test_class") or "") or None,
                            response_status=response.status_code,
                            page_id=spec.get("page_id"),
                        )
                    except TypeError:
                        self.post_probe_fn(url, method, str(spec.get("owasp_category")))
                return {
                    "ok": True,
                    "status_code": response.status_code,
                    "headers": safe_headers,
                    "body_b64": base64.b64encode(returned).decode(),
                    "body_size": len(raw),
                    "body_sha256": hashlib.sha256(raw).hexdigest(),
                    "truncated": len(returned) < len(raw),
                    "url": str(response.url),
                    "duration_ms": elapsed,
                    "traffic_id": getattr(client, "last_traffic_id", None),
                    "stored_session": captured_session_label,
                    "redirect_blocked": redirect_blocked[1]
                    if redirect_blocked
                    else None,
                }
        except Exception as exc:
            return {"ok": False, "error_type": "transport", "error": str(exc)}

    async def batch(
        self, specs: list[dict[str, Any]], concurrency: int
    ) -> dict[str, Any]:
        budget_error = await self._reserve(len(specs))
        if budget_error:
            return self._policy_error(budget_error)
        batch_id = hashlib.sha256(
            f"{self.execution_id}:{self.attempt_count}:{len(specs)}".encode()
        ).hexdigest()[:16]
        semaphore = asyncio.Semaphore(max(1, min(concurrency, self.max_concurrent)))

        async def one(index: int, value: dict[str, Any]) -> dict[str, Any]:
            async with semaphore:
                return await self.request(
                    value,
                    batch_id=batch_id,
                    batch_index=index,
                    reserved=True,
                )

        responses = await asyncio.gather(
            *(one(index, value) for index, value in enumerate(specs))
        )
        failed = next((item for item in responses if not item.get("ok")), None)
        if failed:
            return failed
        return {"ok": True, "responses": responses, "batch_id": batch_id}

    @staticmethod
    def _policy_error(reason: str) -> dict[str, Any]:
        return {"ok": False, "error_type": "policy", "error": reason}


async def _docker_execute(
    execution_id: int,
    code: str,
    config,
    broker: _Broker,
) -> dict[str, Any]:
    name = f"aespa-code-{execution_id}"
    args = _docker_run_args(config, name=name, label=str(execution_id))
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _active[(broker.run_kind, broker.run_id, execution_id)] = proc
    stdout = bytearray()
    stderr = bytearray()
    terminal: dict[str, Any] = {"exit_code": None}
    start = {
        "type": "execution.start",
        "protocol_version": PROTOCOL_VERSION,
        "execution_id": execution_id,
        "code": code,
    }
    assert (
        proc.stdin is not None and proc.stdout is not None and proc.stderr is not None
    )
    proc.stdin.write((json.dumps(start, separators=(",", ":")) + "\n").encode())
    await proc.stdin.drain()

    async def read_stderr() -> None:
        while chunk := await proc.stderr.read(4096):
            if len(stderr) < config.output_limit_bytes:
                stderr.extend(chunk[: config.output_limit_bytes - len(stderr)])

    stderr_task = asyncio.create_task(read_stderr())
    try:
        async with asyncio.timeout(config.timeout_s):
            while line := await proc.stdout.readline():
                if len(line) > 2 * 1024 * 1024:
                    raise RuntimeError("sandbox protocol frame exceeded 2 MiB")
                try:
                    event = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise RuntimeError(
                        "sandbox emitted an invalid protocol frame"
                    ) from exc
                event_type = event.get("type")
                if event_type in {"stdout.chunk", "stderr.chunk"}:
                    try:
                        chunk = base64.b64decode(
                            event.get("data_b64") or "", validate=True
                        )
                    except Exception:
                        chunk = b"[invalid output encoding]"
                    target = stdout if event_type.startswith("stdout") else stderr
                    if len(target) < config.output_limit_bytes:
                        target.extend(chunk[: config.output_limit_bytes - len(target)])
                elif event_type == "broker.request":
                    reply = await broker.request(dict(event.get("request") or {}))
                    reply["request_id"] = event.get("request_id")
                    proc.stdin.write(
                        (json.dumps(reply, separators=(",", ":")) + "\n").encode()
                    )
                    await proc.stdin.drain()
                elif event_type == "broker.request_batch":
                    reply = await broker.batch(
                        [dict(value) for value in event.get("requests") or []],
                        int(event.get("concurrency") or 1),
                    )
                    reply["request_id"] = event.get("request_id")
                    proc.stdin.write(
                        (json.dumps(reply, separators=(",", ":")) + "\n").encode()
                    )
                    await proc.stdin.drain()
                elif event_type == "execution.result":
                    terminal = event
            await proc.wait()
    except TimeoutError:
        terminal = {"exit_code": None, "timed_out": True}
    finally:
        if proc.returncode is None:
            proc.kill()
            await proc.wait()
        await stderr_task
        _active.pop((broker.run_kind, broker.run_id, execution_id), None)
        await _run_command("docker", "rm", "-f", name, timeout=5)
    return {
        **terminal,
        "stdout": stdout.decode(errors="replace"),
        "stderr": stderr.decode(errors="replace"),
        "runner_exit_code": proc.returncode,
    }


def cancel_run_executions(run_kind: str, run_id: int) -> None:
    for key, proc in list(_active.items()):
        if key[:2] != (run_kind, run_id):
            continue
        if proc.returncode is None:
            proc.kill()


async def execute_agent_python(
    *,
    run_kind: str,
    run_id: int,
    agent_id: str,
    agent_role: str,
    agent_step: int,
    purpose: str,
    code: str,
    session_vault: dict[str, dict],
    scanner_policy,
    scope_check_fn: Callable[[str], str | None],
    post_probe_fn: Callable | None = None,
    requested_timeout_s: int | None = None,
) -> str:
    if not code.strip():
        return "execute_python rejected: code must not be empty."
    if len(code.encode()) > 50_000:
        return "execute_python rejected: source exceeds the 50,000-byte limit."
    with Session(get_engine()) as session:
        config = get_code_execution_config(session)
        readiness = await runtime_status(config)
        if not config.enabled:
            return "execute_python is disabled in Agent Settings."
        if agent_role not in config.allowed_roles:
            return f"execute_python is not enabled for the {agent_role!r} role."
        if not readiness["available"]:
            return f"execute_python unavailable: {readiness['message']}"
        try:
            requested_timeout = int(requested_timeout_s or config.timeout_s)
        except (TypeError, ValueError):
            requested_timeout = config.timeout_s
        effective_timeout = max(1, min(config.timeout_s, requested_timeout))
        limits = {
            "timeout_s": effective_timeout,
            "memory_mb": config.memory_mb,
            "cpu_cores": config.cpu_cores,
            "pids_limit": config.pids_limit,
            "max_requests": config.max_requests_per_execution,
            "max_concurrent_requests": config.max_concurrent_requests,
        }
        exact_code = code
        row = CodeExecution(
            run_kind=run_kind,
            run_id=run_id,
            agent_id=agent_id,
            agent_role=agent_role,
            agent_step=agent_step,
            purpose=purpose[:500],
            code_redacted=(
                _redact(exact_code, session_vault)
                if config.retain_redacted_source
                else None
            ),
            code_sha256=hashlib.sha256(exact_code.encode()).hexdigest(),
            status="queued",
            runtime_backend=config.backend,
            runtime_version="python-3.12",
            image_ref=config.image_ref,
            limits_json=json.dumps(limits, separators=(",", ":")),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        execution_id = int(row.id)

    events_svc.emit(
        run_id,
        {
            "type": "scanner_phase",
            "phase": "code_execution",
            "status": "running",
            "message": f"{agent_id} started Python execution #{execution_id}: {purpose[:160]}",
            "data": {
                "execution_id": execution_id,
                "agent_id": agent_id,
                "step": agent_step,
            },
            "_run_kind": run_kind,
        },
    )
    broker = _Broker(
        run_kind=run_kind,
        run_id=run_id,
        execution_id=execution_id,
        agent_id=agent_id,
        agent_step=agent_step,
        session_vault=session_vault,
        scanner_policy=scanner_policy,
        scope_check=scope_check_fn,
        max_requests=config.max_requests_per_execution,
        max_concurrent=config.max_concurrent_requests,
        post_probe_fn=post_probe_fn,
    )
    config.timeout_s = effective_timeout
    status = "failed"
    error_message = None
    result: dict[str, Any] = {}
    try:
        async with _execution_limiter.slot(config.max_concurrent_executions):
            with Session(get_engine()) as session:
                current = session.get(CodeExecution, execution_id)
                current.status = "running"
                current.started_at = _utcnow()
                session.add(current)
                session.commit()
            result = await _docker_execute(execution_id, exact_code, config, broker)
        if result.get("timed_out"):
            status = "timed_out"
            error_message = f"execution exceeded {effective_timeout} seconds"
        elif result.get("exit_code") == 0:
            status = "succeeded"
        elif result.get("exit_code") is None:
            status = "failed"
            error_message = (
                "sandbox harness exited before returning a result "
                f"(runner exit code {result.get('runner_exit_code')})"
            )
        else:
            status = "failed"
            error_message = f"sandbox exited with code {result.get('exit_code')}"
    except asyncio.CancelledError:
        status = "cancelled"
        error_message = "execution cancelled"
        raise
    except Exception as exc:
        status = "failed"
        error_message = str(exc)
    finally:
        with Session(get_engine()) as session:
            current = session.get(CodeExecution, execution_id)
            if current is not None:
                current.status = status
                current.request_count = broker.request_count
                current.denied_request_count = broker.denied_count
                current.stdout_preview = _redact(
                    str(result.get("stdout") or ""), session_vault
                )[: config.output_limit_bytes]
                current.stderr_preview = _redact(
                    str(result.get("stderr") or ""), session_vault
                )[: config.output_limit_bytes]
                current.exit_code = (
                    result.get("exit_code")
                    if result.get("exit_code") is not None
                    else result.get("runner_exit_code")
                )
                current.error_message = (
                    _redact(error_message or "", session_vault) or None
                )
                current.result_json = json.dumps(
                    {
                        "timed_out": bool(result.get("timed_out")),
                        "runner_exit_code": result.get("runner_exit_code"),
                    },
                    separators=(",", ":"),
                )
                current.completed_at = _utcnow()
                session.add(current)
                session.commit()
    events_svc.emit(
        run_id,
        {
            "type": "scanner_phase",
            "phase": "code_execution",
            "status": "complete" if status == "succeeded" else "error",
            "message": f"Python execution #{execution_id} {status} ({broker.request_count} request(s))",
            "data": {
                "execution_id": execution_id,
                "agent_id": agent_id,
                "step": agent_step,
            },
            "_run_kind": run_kind,
        },
    )
    summary = {
        "execution_id": execution_id,
        "status": status,
        "request_count": broker.request_count,
        "denied_request_count": broker.denied_count,
        "stdout": _redact(str(result.get("stdout") or ""), session_vault)[:8000],
        "stderr": _redact(str(result.get("stderr") or ""), session_vault)[:4000],
        "error": _redact(error_message or "", session_vault) or None,
    }
    return json.dumps(summary, separators=(",", ":"))
