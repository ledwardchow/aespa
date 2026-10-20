"""API endpoint matching by method, and validator request rules."""

from __future__ import annotations

import asyncio

import httpx
from sqlalchemy import text
from sqlmodel import Session

from aespa.models import ApiCollection, ApiEndpoint, ApiTestRun, ScanFinding
from aespa.services import api_scanner, traffic, validator
from aespa.services import scanner as scanner_svc

# ── API endpoint matching ─────────────────────────────────────────────────────


def _endpoints() -> list[ApiEndpoint]:
    return [
        ApiEndpoint(id=1, collection_id=1, method="GET", path="/users/{id}"),
        ApiEndpoint(id=2, collection_id=1, method="PUT", path="/users/{id}"),
        ApiEndpoint(id=3, collection_id=1, method="DELETE", path="/users/{id}"),
    ]


def test_match_endpoint_prefers_same_method():
    url = "http://api.local/users/42"
    match = api_scanner._match_endpoint_for_url
    assert match(url, _endpoints(), "http://api.local", method="PUT").id == 2
    assert match(url, _endpoints(), "http://api.local", method="delete").id == 3
    assert match(url, _endpoints(), "http://api.local").id == 1


def test_match_endpoint_falls_back_to_path_for_undocumented_method():
    url = "http://api.local/users/42"
    ep = api_scanner._match_endpoint_for_url(
        url, _endpoints(), "http://api.local", method="PATCH"
    )
    assert ep is not None and ep.path == "/users/{id}"


def test_request_method_from_evidence():
    parse = api_scanner._request_method_from_evidence
    assert parse("PUT http://api.local/users/1 HTTP/1.1\nHost: x") == "PUT"
    assert parse("  delete /users/1") == "DELETE"
    assert parse("Sent as user: bob\nGET /x") is None
    assert parse(None) is None


def test_post_finding_hook_returns_when_run_is_gone(engine):
    with Session(engine) as s:
        collection = ApiCollection(name="API", base_url="http://api.local")
        s.add(collection)
        s.flush()
        run = ApiTestRun(collection_id=collection.id, name="API run")
        s.add(run)
        s.flush()
        finding = ScanFinding(
            api_test_run_id=run.id,
            title="IDOR",
            severity="high",
            owasp_category="API1",
            description="d",
            affected_url="http://api.local/users/1",
        )
        s.add(finding)
        s.commit()
        run_id, finding_id = run.id, finding.id
        # Simulate the run row disappearing while the finding hook runs.
        s.exec(text("DELETE FROM api_test_run WHERE id = :id").bindparams(id=run_id))
        s.commit()

    # Before the fix this raised UnboundLocalError for ``endpoints``.
    with Session(engine) as s:
        api_scanner._make_post_finding_fn(run_id)(s.get(ScanFinding, finding_id))

    with Session(engine) as s:
        assert s.get(ScanFinding, finding_id).owasp_api_category == "API1"


# ── Validator request rules ───────────────────────────────────────────────────


class _Policy:
    follow_redirects = True
    scan_mode = "passive"
    methods_by_mode = {"passive": ["GET", "HEAD"], "aggressive": ["GET", "POST"]}
    allowed_schemes = ["http", "https"]
    request_timeout_s = 5.0
    response_body_read_limit_bytes = 4096


def _in_scope_only(url: str) -> str | None:
    return None if "target.local" in url else "outside scope"


class _FakeClient:
    """Stands in for LoggingAsyncClient and serves canned responses."""

    instances: list["_FakeClient"] = []
    responses: dict[str, httpx.Response] = {}

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.sent: list[str] = []
        _FakeClient.instances.append(self)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    def build_request(self, method, url, **kwargs):
        return httpx.Request(method, url, **kwargs)

    async def send(self, request, follow_redirects=False):
        self.sent.append(str(request.url))
        canned = _FakeClient.responses.get(str(request.url))
        if canned is None:
            return httpx.Response(200, text="ok", request=request)
        response = httpx.Response(
            canned.status_code, headers=canned.headers, request=request
        )
        if response.is_redirect:
            response.next_request = httpx.Request("GET", response.headers["location"])
        return response


def _install_fake_client(monkeypatch, responses=None):
    _FakeClient.instances = []
    _FakeClient.responses = responses or {}
    monkeypatch.setattr(traffic, "LoggingAsyncClient", _FakeClient)
    monkeypatch.setattr(
        validator, "_validator_scope_check", lambda run_id: _in_scope_only
    )


def _http_request(tool_input, policy=None):
    return asyncio.run(
        validator._validator_http_request(
            tool_input, None, {}, policy or _Policy(), run_id=1
        )
    )


def test_validator_blocks_out_of_scope_request(monkeypatch):
    _install_fake_client(monkeypatch)
    result = _http_request({"method": "GET", "url": "http://evil.example/x"})
    assert result["status"] is None
    assert "outside scope" in result["error"]
    assert _FakeClient.instances == []


def test_validator_blocks_method_not_allowed_in_scan_mode(monkeypatch):
    _install_fake_client(monkeypatch)
    result = _http_request({"method": "DELETE", "url": "http://target.local/x"})
    assert result["status"] is None
    assert "not allowed in passive mode" in result["error"]
    assert _FakeClient.instances == []


def test_validator_does_not_follow_out_of_scope_redirect(monkeypatch):
    _install_fake_client(
        monkeypatch,
        {
            "http://target.local/start": httpx.Response(
                302, headers={"location": "http://evil.example/steal"}
            )
        },
    )
    result = _http_request({"method": "GET", "url": "http://target.local/start"})
    assert result["status"] == 302
    assert _FakeClient.instances[0].sent == ["http://target.local/start"]


def test_validator_follows_in_scope_redirect(monkeypatch):
    _install_fake_client(
        monkeypatch,
        {
            "http://target.local/start": httpx.Response(
                302, headers={"location": "http://target.local/next"}
            )
        },
    )
    result = _http_request({"method": "GET", "url": "http://target.local/start"})
    assert result["status"] == 200
    assert _FakeClient.instances[0].sent == [
        "http://target.local/start",
        "http://target.local/next",
    ]


def test_validator_request_uses_scanner_proxy_and_global_headers(monkeypatch):
    _install_fake_client(monkeypatch)
    proxy_token = scanner_svc._scanner_proxy_var.set("http://proxy.local:8080")
    header_token = scanner_svc._scanner_global_header_var.set({"X-Test": "1"})
    try:
        _http_request({"method": "GET", "url": "http://target.local/x"})
    finally:
        scanner_svc._scanner_proxy_var.reset(proxy_token)
        scanner_svc._scanner_global_header_var.reset(header_token)

    kwargs = _FakeClient.instances[0].kwargs
    assert kwargs["proxy"] == "http://proxy.local:8080"
    assert kwargs["headers"]["X-Test"] == "1"


def test_legacy_validation_probe_sends_request(monkeypatch):
    """The legacy probe path used to fail on scanner helpers that no longer exist."""
    _install_fake_client(monkeypatch)
    result = asyncio.run(
        validator._run_validation_probe(
            {"method": "GET", "url": "http://target.local/x", "body": {"a": 1}},
            None,
            None,
            page_url="http://target.local/x",
            scanner_policy=_Policy(),
            run_id=1,
        )
    )
    assert result is not None
    assert result["status"] == 200
    assert _FakeClient.instances[0].sent == ["http://target.local/x"]


def test_legacy_validation_probe_rejects_out_of_scope(monkeypatch):
    _install_fake_client(monkeypatch)
    result = asyncio.run(
        validator._run_validation_probe(
            {"method": "GET", "url": "http://evil.example/x"},
            None,
            None,
            page_url="http://target.local/x",
            scanner_policy=_Policy(),
            run_id=1,
        )
    )
    assert result is None
    assert _FakeClient.instances == []


def test_scope_check_fails_closed_without_run():
    check = validator._validator_scope_check(None)
    assert check("http://target.local/x")
