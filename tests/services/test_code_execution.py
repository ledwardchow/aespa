import base64
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import ApiTestRun, CodeExecution, CodeExecutionConfig, TestRun
from aespa.services import code_execution
from aespa.services.outbound_policy import validate_request

RUNTIME_DIR = Path(__file__).resolve().parents[2] / "runtime" / "python-executor"


def _policy(**overrides):
    values = {
        "allowed_schemes": ["http", "https"],
        "scan_mode": "aggressive",
        "methods_by_mode": {"aggressive": ["GET", "POST"]},
        "blocked_headers": ["host", "cookie"],
        "max_request_body_bytes": 1024,
        "require_approval_for_destructive": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _runner_config(**overrides):
    values = {
        "enabled": True,
        "backend": "docker",
        "image_ref": "ledwardchow/aespa-python-executor:0.1",
        "timeout_s": 30,
        "memory_mb": 256,
        "cpu_cores": 0.5,
        "pids_limit": 32,
        "workspace_mb": 16,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_outbound_policy_allows_scoped_request():
    decision = validate_request(
        method="POST",
        url="https://target.local/check",
        headers={"Content-Type": "application/json"},
        body_size=20,
        scanner_policy=_policy(),
        scope_check=lambda _url: None,
    )

    assert decision.allowed is True


def test_outbound_policy_rejects_scope_method_headers_and_body():
    cases = [
        ({"url": "https://other.local"}, "out of scope"),
        ({"method": "DELETE"}, "not allowed"),
        ({"headers": {"Cookie": "secret"}}, "reserved request header"),
        ({"body_size": 1025}, "policy limit"),
        ({"url": "https://user:pass@target.local"}, "embedded"),
    ]
    for changes, expected in cases:
        params = {
            "method": "GET",
            "url": "https://target.local/check",
            "headers": {},
            "body_size": 0,
            "scanner_policy": _policy(),
            "scope_check": lambda url: "out of scope" if "other.local" in url else None,
        }
        params.update(changes)
        decision = validate_request(**params)
        assert decision.allowed is False
        assert expected in (decision.reason or "")


def test_outbound_policy_requires_destructive_approval():
    decision = validate_request(
        method="DELETE",
        url="https://target.local/check",
        headers={},
        body_size=0,
        scanner_policy=_policy(
            scan_mode="destructive",
            methods_by_mode={"destructive": ["DELETE"]},
        ),
        scope_check=lambda _url: None,
    )

    assert decision.allowed is False
    assert "approval" in (decision.reason or "")


def test_docker_profile_assigns_workspace_to_non_root_sandbox_user():
    args = code_execution._docker_run_args(
        _runner_config(), name="aespa-code-test", label="test"
    )

    tmpfs = args[args.index("--tmpfs") + 1]
    assert "uid=65532" in tmpfs
    assert "gid=65532" in tmpfs
    assert "mode=0700" in tmpfs
    assert args[args.index("--user") + 1] == "65532:65532"
    assert args[args.index("--network") + 1] == "none"


@pytest.mark.anyio
async def test_runtime_status_rejects_incompatible_container_profile(monkeypatch):
    monkeypatch.setattr(code_execution.shutil, "which", lambda _name: "/usr/bin/docker")

    async def image_present(*_args, **_kwargs):
        return 0, ""

    async def incompatible(_config):
        return False, "workspace is not writable"

    monkeypatch.setattr(code_execution, "_run_command", image_present)
    monkeypatch.setattr(code_execution, "_runtime_self_test", incompatible)

    status = await code_execution.runtime_status(_runner_config())

    assert status["image_present"] is True
    assert status["available"] is False
    assert status["message"] == (
        "Sandbox runtime is incompatible: workspace is not writable"
    )


def test_execution_audit_routes_are_scoped_by_run_kind(client):
    with Session(get_engine()) as session:
        web_run = TestRun(site_id=1, name="Web audit")
        api_run = ApiTestRun(collection_id=1, name="API audit")
        session.add(web_run)
        session.add(api_run)
        session.commit()
        session.refresh(web_run)
        session.refresh(api_run)
        web_execution = CodeExecution(
            run_kind="web",
            run_id=int(web_run.id),
            agent_id="alice",
            agent_role="alice",
            purpose="Web workflow",
            code_sha256="a" * 64,
        )
        api_execution = CodeExecution(
            run_kind="api",
            run_id=int(api_run.id),
            agent_id="specialist-1",
            agent_role="specialist",
            purpose="API workflow",
            code_sha256="b" * 64,
        )
        session.add(web_execution)
        session.add(api_execution)
        session.commit()
        session.refresh(web_execution)
        session.refresh(api_execution)
        web_run_id = int(web_run.id)
        api_run_id = int(api_run.id)
        web_execution_id = int(web_execution.id)
        api_execution_id = int(api_execution.id)

    web_response = client.get(f"/api/test-runs/{web_run_id}/code-executions")
    assert web_response.status_code == 200
    assert [item["id"] for item in web_response.json()] == [web_execution_id]

    api_response = client.get(f"/api/api-test-runs/{api_run_id}/code-executions")
    assert api_response.status_code == 200
    assert [item["id"] for item in api_response.json()] == [api_execution_id]

    cross_kind = client.get(
        f"/api/test-runs/{web_run_id}/code-executions/{api_execution_id}"
    )
    assert cross_kind.status_code == 404


@pytest.mark.anyio
async def test_execution_persists_redacted_audit_record(
    monkeypatch, isolated_db_engine
):
    with Session(get_engine()) as session:
        run = TestRun(site_id=1, name="Sandbox test")
        session.add(run)
        session.commit()
        session.refresh(run)
        session.add(
            CodeExecutionConfig(
                id=1,
                enabled=True,
                allowed_roles_json='["specialist"]',
            )
        )
        session.commit()
        run_id = int(run.id)

    async def ready(_config):
        return {"available": True, "message": "ready"}

    async def fake_execute(_execution_id, _code, _config, _broker):
        return {
            "exit_code": 0,
            "stdout": "token=top-secret-token",
            "stderr": "",
        }

    monkeypatch.setattr(code_execution, "runtime_status", ready)
    monkeypatch.setattr(code_execution, "_docker_execute", fake_execute)
    result = await code_execution.execute_agent_python(
        run_kind="web",
        run_id=run_id,
        agent_id="specialist-1",
        agent_role="specialist",
        agent_step=3,
        purpose="Parse a non-standard response",
        code='print("top-secret-token")',
        session_vault={
            "configured_primary": {
                "cookies": {"session": "top-secret-token"},
                "extra_headers": {},
            }
        },
        scanner_policy=_policy(),
        scope_check_fn=lambda _url: None,
    )

    assert '"status":"succeeded"' in result
    assert "top-secret-token" not in result
    with Session(get_engine()) as session:
        row = session.exec(select(CodeExecution)).one()
        assert row.status == "succeeded"
        assert row.agent_id == "specialist-1"
        assert row.code_redacted == 'print("[REDACTED]")'
        assert row.stdout_preview == "token=[REDACTED]"


@pytest.mark.anyio
async def test_execution_reports_runner_exit_when_harness_returns_no_result(
    monkeypatch, isolated_db_engine
):
    with Session(get_engine()) as session:
        run = TestRun(site_id=1, name="Harness failure")
        session.add(run)
        session.commit()
        session.refresh(run)
        session.add(
            CodeExecutionConfig(
                id=1,
                enabled=True,
                allowed_roles_json='["alice"]',
            )
        )
        session.commit()
        run_id = int(run.id)

    async def ready(_config):
        return {"available": True, "message": "ready"}

    async def harness_failure(_execution_id, _code, _config, _broker):
        return {
            "exit_code": None,
            "runner_exit_code": 17,
            "stdout": "",
            "stderr": "harness failed",
        }

    monkeypatch.setattr(code_execution, "runtime_status", ready)
    monkeypatch.setattr(code_execution, "_docker_execute", harness_failure)
    result = json.loads(
        await code_execution.execute_agent_python(
            run_kind="web",
            run_id=run_id,
            agent_id="alice",
            agent_role="alice",
            agent_step=1,
            purpose="Exercise harness failure",
            code="print('never reached')",
            session_vault={},
            scanner_policy=_policy(),
            scope_check_fn=lambda _url: None,
        )
    )

    assert result["status"] == "failed"
    assert "runner exit code 17" in result["error"]
    with Session(get_engine()) as session:
        row = session.exec(select(CodeExecution)).one()
        assert row.exit_code == 17
        assert "runner exit code 17" in (row.error_message or "")


def test_sandbox_harness_separates_output_and_broker_protocol(tmp_path):
    environment = os.environ.copy()
    environment["AESPA_WORK_DIR"] = str(tmp_path)
    process = subprocess.Popen(
        [sys.executable, str(RUNTIME_DIR / "aespa_harness.py")],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=environment,
    )
    assert process.stdin is not None
    assert process.stdout is not None
    process.stdin.write(
        json.dumps(
            {
                "type": "execution.start",
                "protocol_version": "1",
                "execution_id": 9,
                "code": (
                    "from aespa_runtime import request\n"
                    "response = request('GET', 'https://target.local/check')\n"
                    "print(response.status_code, response.text, response.traffic_id)\n"
                ),
            }
        )
        + "\n"
    )
    process.stdin.flush()

    captured = bytearray()
    exit_code = None
    for line in process.stdout:
        frame = json.loads(line)
        if frame["type"] == "broker.request":
            assert frame["request"]["url"] == "https://target.local/check"
            process.stdin.write(
                json.dumps(
                    {
                        "ok": True,
                        "request_id": frame["request_id"],
                        "status_code": 200,
                        "headers": {"content-type": "text/plain"},
                        "body_b64": base64.b64encode(b"brokered").decode(),
                        "url": "https://target.local/check",
                        "duration_ms": 4,
                        "traffic_id": 77,
                    }
                )
                + "\n"
            )
            process.stdin.flush()
        elif frame["type"] == "stdout.chunk":
            captured.extend(base64.b64decode(frame["data_b64"]))
        elif frame["type"] == "execution.result":
            exit_code = frame["exit_code"]
            break

    assert process.wait(timeout=5) == 0
    assert exit_code == 0
    assert captured.decode().strip() == "200 brokered 77"
