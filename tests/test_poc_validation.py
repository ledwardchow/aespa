"""Tests for verified proof-of-concept generation in the validator service."""
import asyncio

from aespa.models import ScanFinding
from aespa.services import validator
from aespa.services.validator import _POC_AUTH_FILE


class _Policy:
    follow_redirects = True


def _finding(url="https://target.local/api/users/2"):
    return ScanFinding(
        test_run_id=1,
        page_id=None,
        owasp_category="A01",
        severity="high",
        title="IDOR",
        description="",
        affected_url=url,
        evidence="",
    )


def _done(**overrides):
    base = {
        "verdict": "confirmed",
        "reasoning": "reproduced",
        "poc_request": {"method": "GET", "url": "https://target.local/api/users/2"},
        "poc_expect": {"status": 200, "body_contains": "victim@example.com"},
    }
    base.update(overrides)
    return base


def test_poc_request_expect_requires_positive_assertion():
    assert validator.poc_request_expect({"poc_expect": {}}) is None
    assert validator.poc_request_expect({"poc_expect": {"status": 200}}) is not None
    assert validator.poc_request_expect({"poc_expect": {"body_contains": "x"}}) is not None


def test_poc_url_in_scope_requires_same_host():
    affected = "https://target.local/a"
    assert validator._poc_url_in_scope("https://target.local/b", affected)
    assert not validator._poc_url_in_scope("https://evil.example/b", affected)
    assert not validator._poc_url_in_scope("ftp://target.local/b", affected)
    assert not validator._poc_url_in_scope("not a url", affected)


def test_resolve_poc_auth_bearer_strips_prefix():
    session = {"extra_headers": {"Authorization": "Bearer abc.def"}, "cookies": {}}
    auth = validator._resolve_poc_auth(session, "bearer")
    assert auth == {"file_value": "abc.def", "header_name": "Authorization", "header_prefix": "Bearer "}


def test_resolve_poc_auth_cookie_builds_header():
    session = {"extra_headers": {}, "cookies": {"sid": "xyz", "csrf": "t"}}
    auth = validator._resolve_poc_auth(session, "cookie_httponly")
    assert auth["header_name"] == "Cookie"
    assert auth["file_value"] == "sid=xyz; csrf=t"


def test_resolve_poc_auth_returns_none_when_credential_absent():
    assert validator._resolve_poc_auth({"extra_headers": {}, "cookies": {}}, "bearer") is None
    assert validator._resolve_poc_auth({"extra_headers": {}, "cookies": {}}, "cookie_httponly") is None


def test_build_curl_command_uses_token_file_not_literal_credential():
    auth = {"file_value": "SECRET", "header_name": "Cookie", "header_prefix": ""}
    cmd = validator._build_curl_command(
        "GET", "https://target.local/x", {}, insecure=True, follow_redirects=True, auth=auth
    )
    assert "SECRET" not in cmd  # the live credential must never appear in the command
    assert f"$(cat {_POC_AUTH_FILE})" in cmd
    assert cmd.startswith("curl ")
    assert "-k" in cmd and "-L" in cmd


def test_build_curl_argv_materialises_credential_shell_free():
    # The shipped command hides the credential behind $(cat …); the verification
    # argv materialises it directly so subprocess.run needs no shell.
    auth = {"file_value": "SECRET", "header_name": "Cookie", "header_prefix": ""}
    argv = validator._build_curl_argv(
        "GET", "https://target.local/x", {}, insecure=True, follow_redirects=True, auth=auth
    )
    assert isinstance(argv, list) and argv[0] == "curl"
    assert "Cookie: SECRET" in argv  # credential inline, no $(cat …)
    assert not any("$(cat" in a for a in argv)


def test_run_and_assert_curl_checks_assertion_without_shell(monkeypatch):
    import subprocess

    class _Proc:
        def __init__(self, out):
            self.stdout = out

    def _fake_run(argv, **kw):
        assert isinstance(argv, list)  # shell-free: argv, never a string
        assert "shell" not in kw or kw["shell"] is False
        return _Proc("HTTP/1.1 200 OK\n\nWELCOME-s3cret")

    monkeypatch.setattr(subprocess, "run", _fake_run)
    argv = ["curl", "https://target.local/x"]
    expect = {"status": 200, "body_contains": "WELCOME-s3cret", "body_not_contains": ""}
    assert validator._run_and_assert_curl(argv, expect) is True

    wrong = {"status": 200, "body_contains": "WELCOME-nope", "body_not_contains": ""}
    assert validator._run_and_assert_curl(argv, wrong) is False


def test_run_and_assert_curl_honours_status_mismatch(monkeypatch):
    import subprocess

    class _Proc:
        stdout = "HTTP/1.1 403 Forbidden\n\nbody"

    monkeypatch.setattr(subprocess, "run", lambda argv, **kw: _Proc())
    assert validator._run_and_assert_curl(["curl"], {"status": 200, "body_contains": ""}) is False


def test_build_and_verify_poc_returns_command_when_verified(monkeypatch):
    captured = {}

    def _stub(argv, expect):
        captured["argv"] = argv
        return True

    monkeypatch.setattr(validator, "_run_and_assert_curl", _stub)
    result = asyncio.run(
        validator._build_and_verify_poc(_finding(), _done(), {}, _Policy())
    )
    assert result is not None
    command, setup = result
    assert command.startswith("curl ")
    assert "https://target.local/api/users/2" in command
    assert setup == ""  # no auth needed
    assert "https://target.local/api/users/2" in captured["argv"]


def test_build_and_verify_poc_drops_when_verification_fails(monkeypatch):
    monkeypatch.setattr(validator, "_run_and_assert_curl", lambda *a: False)
    result = asyncio.run(
        validator._build_and_verify_poc(_finding(), _done(), {}, _Policy())
    )
    assert result is None


def test_build_and_verify_poc_rejects_state_changing_method(monkeypatch):
    monkeypatch.setattr(validator, "_run_and_assert_curl", lambda *a: True)
    done = _done(poc_request={"method": "DELETE", "url": "https://target.local/api/users/2"})
    result = asyncio.run(
        validator._build_and_verify_poc(_finding(), done, {}, _Policy())
    )
    assert result is None


def test_build_and_verify_poc_rejects_out_of_scope_url(monkeypatch):
    monkeypatch.setattr(validator, "_run_and_assert_curl", lambda *a: True)
    done = _done(poc_request={"method": "GET", "url": "https://evil.example/steal"})
    result = asyncio.run(
        validator._build_and_verify_poc(_finding(), done, {}, _Policy())
    )
    assert result is None


def test_build_and_verify_poc_requires_session_for_auth(monkeypatch):
    monkeypatch.setattr(validator, "_run_and_assert_curl", lambda *a: True)
    done = _done(
        poc_request={"method": "GET", "url": "https://target.local/api/users/2", "use_session": "victim"},
        poc_auth={"mechanism": "cookie_httponly"},
    )
    # No matching session available -> cannot verify -> no PoC.
    result = asyncio.run(
        validator._build_and_verify_poc(_finding(), done, {}, _Policy())
    )
    assert result is None


def test_build_and_verify_poc_includes_setup_for_auth(monkeypatch):
    captured = {}

    def _stub(argv, expect):
        captured["argv"] = argv
        return True

    monkeypatch.setattr(validator, "_run_and_assert_curl", _stub)
    done = _done(
        poc_request={"method": "GET", "url": "https://target.local/api/users/2", "use_session": "victim"},
        poc_auth={"mechanism": "cookie_httponly", "instructions": "Log in as victim."},
    )
    sessions = {"victim": {"username": "victim", "cookies": {"sid": "abc"}, "extra_headers": {}}}
    result = asyncio.run(
        validator._build_and_verify_poc(_finding(), done, sessions, _Policy())
    )
    assert result is not None
    command, setup = result
    # The shipped command keeps the credential behind $(cat …); the verification
    # argv materialises it inline so the live cookie is exercised shell-free.
    assert f"$(cat {_POC_AUTH_FILE})" in command
    assert "Network" in setup  # httponly fallback instructions
    assert "Cookie: sid=abc" in captured["argv"]


# ── POST acceptance + body serialisation ───────────────────────────────────────

def test_post_method_is_accepted(monkeypatch):
    monkeypatch.setattr(validator, "_run_and_assert_curl", lambda *a: True)
    done = _done(
        poc_request={"method": "POST", "url": "https://target.local/api/login"},
    )
    finding = _finding(url="https://target.local/api/login")
    result = asyncio.run(
        validator._build_and_verify_poc(finding, done, {}, _Policy())
    )
    assert result is not None
    command, _ = result
    assert "-X POST" in command
    assert "https://target.local/api/login" in command


def test_put_method_still_suppressed(monkeypatch):
    monkeypatch.setattr(validator, "_run_and_assert_curl", lambda *a: True)
    done = _done(
        poc_request={"method": "PUT", "url": "https://target.local/api/users/2"}
    )
    result = asyncio.run(
        validator._build_and_verify_poc(_finding(), done, {}, _Policy())
    )
    assert result is None


def test_patch_method_still_suppressed(monkeypatch):
    monkeypatch.setattr(validator, "_run_and_assert_curl", lambda *a: True)
    done = _done(
        poc_request={"method": "PATCH", "url": "https://target.local/api/users/2"}
    )
    result = asyncio.run(
        validator._build_and_verify_poc(_finding(), done, {}, _Policy())
    )
    assert result is None


def test_build_curl_command_serialises_string_body():
    cmd = validator._build_curl_command(
        "POST", "https://target.local/login", {},
        insecure=True, follow_redirects=True, auth=None,
        body="username=admin&password=admin",
    )
    assert "--data-raw" in cmd
    assert "username=admin&password=admin" in cmd


def test_build_curl_command_serialises_dict_body_as_json():
    cmd = validator._build_curl_command(
        "POST", "https://target.local/api/x", {},
        insecure=True, follow_redirects=True, auth=None,
        body={"user": "admin", "role": "superuser"},
    )
    assert "Content-Type: application/json" in cmd
    assert "--data-raw" in cmd
    assert '"user":"admin"' in cmd
    assert '"role":"superuser"' in cmd


def test_build_curl_command_omits_body_flag_when_no_body():
    cmd = validator._build_curl_command(
        "POST", "https://target.local/x", {},
        insecure=True, follow_redirects=True, auth=None,
    )
    assert "--data-raw" not in cmd


# ── Event + log emission on every branch ──────────────────────────────────────

def _capture_emits(monkeypatch):
    captured: list[dict] = []

    def _fake_emit(run_id, event):
        captured.append({"run_id": run_id, **event})

    monkeypatch.setattr(validator.events_svc, "emit", _fake_emit)
    return captured


def test_no_poc_request_emits_no_request_event(monkeypatch, caplog):
    captured = _capture_emits(monkeypatch)
    done = {"verdict": "confirmed", "reasoning": "x"}  # no poc_request
    with caplog.at_level("INFO", logger="aespa.validator"):
        result = asyncio.run(
            validator._build_and_verify_poc(_finding(), done, {}, _Policy(), run_id=42)
        )
    assert result is None
    phase_evts = [e for e in captured if e.get("type") == "scanner_phase"]
    agent_evts = [e for e in captured if e.get("type") == "agent_status"]
    assert any(
        e.get("phase") == "poc_verify" and e["data"]["poc_status"] == "no_request"
        for e in phase_evts
    )
    assert any(
        e.get("agent_id") == "reporting" and e.get("_persist") is True
        for e in agent_evts
    )
    assert "PoC [no_request]" in caplog.text


def test_out_of_scope_emits_event(monkeypatch, caplog):
    captured = _capture_emits(monkeypatch)
    done = _done(poc_request={"method": "GET", "url": "https://evil.example/x"})
    with caplog.at_level("INFO", logger="aespa.validator"):
        result = asyncio.run(
            validator._build_and_verify_poc(_finding(), done, {}, _Policy(), run_id=42)
        )
    assert result is None
    assert any(
        e.get("phase") == "poc_verify" and e["data"]["poc_status"] == "out_of_scope"
        for e in captured if e.get("type") == "scanner_phase"
    )
    assert "PoC [out_of_scope]" in caplog.text


def test_state_changing_method_emits_event(monkeypatch, caplog):
    captured = _capture_emits(monkeypatch)
    done = _done(
        poc_request={"method": "DELETE", "url": "https://target.local/api/users/2"}
    )
    with caplog.at_level("INFO", logger="aespa.validator"):
        result = asyncio.run(
            validator._build_and_verify_poc(_finding(), done, {}, _Policy(), run_id=42)
        )
    assert result is None
    assert any(
        e.get("phase") == "poc_verify"
        and e["data"]["poc_status"] == "method_suppressed"
        and e["data"]["method"] == "DELETE"
        for e in captured if e.get("type") == "scanner_phase"
    )
    assert "PoC [method_suppressed]" in caplog.text


def test_no_assertion_emits_event(monkeypatch, caplog):
    captured = _capture_emits(monkeypatch)
    done = _done(
        poc_request={"method": "GET", "url": "https://target.local/api/users/2"}
    )
    done["poc_expect"] = {}  # no status, no body_contains
    with caplog.at_level("INFO", logger="aespa.validator"):
        result = asyncio.run(
            validator._build_and_verify_poc(_finding(), done, {}, _Policy(), run_id=42)
        )
    assert result is None
    assert any(
        e.get("phase") == "poc_verify" and e["data"]["poc_status"] == "no_assertion"
        for e in captured if e.get("type") == "scanner_phase"
    )
    assert "PoC [no_assertion]" in caplog.text


def test_auth_unresolved_emits_event(monkeypatch, caplog):
    captured = _capture_emits(monkeypatch)
    done = _done(
        poc_request={
            "method": "GET",
            "url": "https://target.local/api/users/2",
            "use_session": "ghost",
        },
        poc_auth={"mechanism": "bearer"},
    )
    with caplog.at_level("INFO", logger="aespa.validator"):
        result = asyncio.run(
            validator._build_and_verify_poc(_finding(), done, {}, _Policy(), run_id=42)
        )
    assert result is None
    assert any(
        e.get("phase") == "poc_verify" and e["data"]["poc_status"] == "auth_unresolved"
        for e in captured if e.get("type") == "scanner_phase"
    )
    assert "PoC [auth_unresolved]" in caplog.text


def test_verification_failed_emits_event(monkeypatch, caplog):
    captured = _capture_emits(monkeypatch)
    monkeypatch.setattr(validator, "_run_and_assert_curl", lambda *a: False)
    with caplog.at_level("INFO", logger="aespa.validator"):
        result = asyncio.run(
            validator._build_and_verify_poc(
                _finding(), _done(), {}, _Policy(), run_id=42,
            )
        )
    assert result is None
    assert any(
        e.get("phase") == "poc_verify"
        and e["data"]["poc_status"] == "verification_failed"
        for e in captured if e.get("type") == "scanner_phase"
    )
    assert "PoC [verification_failed]" in caplog.text


def test_verified_emits_verified_event(monkeypatch, caplog):
    captured = _capture_emits(monkeypatch)
    monkeypatch.setattr(validator, "_run_and_assert_curl", lambda *a: True)
    with caplog.at_level("INFO", logger="aespa.validator"):
        result = asyncio.run(
            validator._build_and_verify_poc(
                _finding(), _done(), {}, _Policy(), run_id=42,
            )
        )
    assert result is not None
    assert any(
        e.get("phase") == "poc_verify" and e["data"]["poc_status"] == "verified"
        for e in captured if e.get("type") == "scanner_phase"
    )
    reporting = [
        e for e in captured
        if e.get("type") == "agent_status" and e.get("agent_id") == "reporting"
    ]
    assert reporting and reporting[0]["_persist"] is True
    assert "PoC [verified]" in caplog.text


def test_run_id_none_silently_skips_event_emit(monkeypatch):
    """When _build_and_verify_poc is called without run_id (e.g. legacy callers),
    no events are emitted — verification still runs, just silently."""
    captured = _capture_emits(monkeypatch)
    monkeypatch.setattr(validator, "_run_and_assert_curl", lambda *a: True)
    result = asyncio.run(
        validator._build_and_verify_poc(_finding(), _done(), {}, _Policy())
    )
    assert result is not None
    assert captured == []
