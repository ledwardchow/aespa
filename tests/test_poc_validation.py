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


def test_run_and_assert_curl_executes_command_and_reads_token_file():
    cmd = f'printf "HTTP/1.1 200 OK\\n\\nWELCOME-"; cat {_POC_AUTH_FILE}'
    expect = {"status": 200, "body_contains": "WELCOME-s3cret", "body_not_contains": ""}
    assert validator._run_and_assert_curl(cmd, expect, "s3cret") is True

    wrong = {"status": 200, "body_contains": "WELCOME-nope", "body_not_contains": ""}
    assert validator._run_and_assert_curl(cmd, wrong, "s3cret") is False


def test_run_and_assert_curl_honours_status_mismatch():
    cmd = 'printf "HTTP/1.1 403 Forbidden\\n\\nbody"'
    assert validator._run_and_assert_curl(cmd, {"status": 200, "body_contains": ""}, None) is False


def test_build_and_verify_poc_returns_command_when_verified(monkeypatch):
    captured = {}

    def _stub(command, expect, auth_file_value):
        captured["command"] = command
        captured["auth_file_value"] = auth_file_value
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
    assert captured["auth_file_value"] is None


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

    def _stub(command, expect, auth_file_value):
        captured["auth_file_value"] = auth_file_value
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
    assert f"$(cat {_POC_AUTH_FILE})" in command
    assert "Network" in setup  # httponly fallback instructions
    assert captured["auth_file_value"] == "sid=abc"
