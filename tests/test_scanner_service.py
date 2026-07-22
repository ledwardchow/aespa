import asyncio
import json
from types import SimpleNamespace

import httpx
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from aespa.models import ScanFinding, Site, TestRun
from aespa.services import burp_rest, scanner


def test_execution_snapshot_records_reproducible_config_without_secrets(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(scanner, "get_engine", lambda: engine)
    with Session(engine) as session:
        site = Site(name="target", base_url="https://target.local")
        session.add(site)
        session.flush()
        run = TestRun(
            site_id=site.id,
            name="snapshot",
            recon_summary='{"schema_version":2,"routes":[]}',
        )
        session.add(run)
        session.commit()
        run_id = run.id

    scanner._persist_execution_snapshot(
        run_id,
        llm_cfg=SimpleNamespace(
            provider="openai",
            model="minimax/m3",
            max_tokens=70_000,
            temperature=0.2,
            use_vision=False,
            force_tool_choice=False,
            api_key="must-not-be-persisted",
        ),
        scanner_policy=SimpleNamespace(
            scan_mode="aggressive",
            max_probes_per_page=50,
            request_timeout_s=10,
            min_delay_s=0.05,
            follow_redirects=True,
            allow_subdomains=True,
            execution_monitor_enabled=False,
            max_consecutive_text_turns=3,
            enforce_full_coverage_obligations=True,
        ),
        pages_snapshot=[{"url": "https://target.local/", "req_auth": False}],
        coverage_mode="enforce",
        enforce_coverage=True,
    )

    with Session(engine) as session:
        snapshot_raw = session.get(TestRun, run_id).execution_snapshot_json
    snapshot = json.loads(snapshot_raw)
    assert snapshot["model"]["model"] == "minimax/m3"
    assert snapshot["coverage_mode"] == "enforce"
    assert len(snapshot["crawl_sha256"]) == 64
    assert "must-not-be-persisted" not in snapshot_raw


def test_select_browser_auth_token_accepts_namespaced_token_key():
    token, key = scanner._select_browser_auth_token(
        {
            "bankofed_user": '{"email":"amelia@example.com"}',
            "bankofed_token": "opaque-access-token",
        }
    )

    assert token == "opaque-access-token"
    assert key == "bankofed_token"


def test_select_browser_auth_token_accepts_jwt_under_arbitrary_key():
    jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.signature"

    assert scanner._select_browser_auth_token({"app_session": jwt}) == (
        jwt,
        "app_session",
    )


def test_select_browser_auth_token_rejects_non_bearer_tokens():
    assert scanner._select_browser_auth_token(
        {"csrf_token": "csrf", "refresh_token": "refresh"}
    ) == (None, None)


def test_authorization_header_is_case_insensitive():
    assert (
        scanner._authorization_header({"authorization": "Bearer persisted"})
        == "Bearer persisted"
    )


# ── scope-checked redirect following ──────────────────────────────────────────


class _FakeResp:
    def __init__(self, url, status_code, headers=None):
        self.url = httpx.URL(url)
        self.status_code = status_code
        self.headers = headers or {}


class _FakeClient:
    """Minimal httpx-like client returning canned responses keyed by URL."""

    def __init__(self, responses):
        self._responses = responses
        self.calls = []  # (method, url, kwargs)

    async def request(self, method, url, follow_redirects=True, **kwargs):
        self.calls.append((method, str(url), kwargs))
        return self._responses[str(url)]


def test_reporting_handoff_replaces_test_lead_decision_status(monkeypatch):
    emitted = []
    monkeypatch.setattr(
        scanner.events_svc,
        "emit",
        lambda run_id, event: emitted.append((run_id, event)),
    )

    scanner._emit_reporting_handoff(42, probe_count=12, batch_count=3)

    assert emitted == [
        (
            42,
            {
                "type": "agent_status",
                "agent_id": "scanner",
                "role": "Test Lead",
                "status": "active",
                "current_task": "Testing complete - handed traffic to reporting agent for analysis...",
                "outcome": "Reporting is analysing 12 probe result(s) across 3 LLM turn(s).",
                "_persist": True,
            },
        )
    ]


def test_scan_complete_is_emitted_as_the_terminal_phase(monkeypatch):
    emitted = []
    monkeypatch.setattr(
        scanner.events_svc,
        "emit",
        lambda run_id, event: emitted.append((run_id, event)),
    )

    scanner._emit_scan_complete(42, finding_count=3)

    assert emitted[-1] == (
        42,
        {
            "type": "scanner_phase",
            "phase": "scan_complete",
            "status": "complete",
            "message": "Scan complete",
            "data": {"finding_count": 3},
        },
    )


def test_reporting_findings_use_managed_validator_queue(monkeypatch):
    queued = []

    async def fake_start_validation(run_id, finding_ids=None, **kwargs):
        queued.append((run_id, finding_ids, kwargs))

    from aespa.services import validator

    monkeypatch.setattr(validator, "start_validation", fake_start_validation)

    asyncio.run(scanner._queue_reporting_validation(42, [7, 8]))
    asyncio.run(scanner._queue_reporting_validation(42, []))

    assert queued == [(42, [7, 8], {"use_reporting_concurrency": True})]


def test_request_scope_checked_follows_in_scope_redirect(monkeypatch):
    monkeypatch.setattr(scanner, "check_scope", lambda url, site_id, run_id: None)
    client = _FakeClient(
        {
            "https://t.local/a": _FakeResp(
                "https://t.local/a", 302, {"location": "/b"}
            ),
            "https://t.local/b": _FakeResp("https://t.local/b", 200, {}),
        }
    )
    resp, blocked = asyncio.run(
        scanner._request_scope_checked(
            client, "GET", "https://t.local/a", site_id=1, run_id=1
        )
    )
    assert blocked is None
    assert resp.status_code == 200
    assert [c[:2] for c in client.calls] == [
        ("GET", "https://t.local/a"),
        ("GET", "https://t.local/b"),
    ]


def test_request_scope_checked_blocks_out_of_scope_redirect(monkeypatch):
    monkeypatch.setattr(
        scanner,
        "check_scope",
        lambda url, site_id, run_id: None if "t.local" in url else "Host out of scope",
    )
    client = _FakeClient(
        {
            "https://t.local/a": _FakeResp(
                "https://t.local/a", 302, {"location": "http://169.254.169.254/meta"}
            ),
        }
    )
    resp, blocked = asyncio.run(
        scanner._request_scope_checked(
            client, "GET", "https://t.local/a", site_id=1, run_id=1
        )
    )
    assert blocked is not None
    assert blocked[0] == "http://169.254.169.254/meta"
    assert resp.status_code == 302  # the unfollowed 3xx is returned
    # The off-scope host must NEVER have been contacted.
    assert all("169.254.169.254" not in url for _, url, _ in client.calls)
    assert [c[:2] for c in client.calls] == [("GET", "https://t.local/a")]


def test_request_scope_checked_303_downgrades_post_to_get_and_drops_body(monkeypatch):
    monkeypatch.setattr(scanner, "check_scope", lambda url, site_id, run_id: None)
    client = _FakeClient(
        {
            "https://t.local/a": _FakeResp(
                "https://t.local/a", 303, {"location": "/done"}
            ),
            "https://t.local/done": _FakeResp("https://t.local/done", 200, {}),
        }
    )
    resp, blocked = asyncio.run(
        scanner._request_scope_checked(
            client, "POST", "https://t.local/a", site_id=1, run_id=1, json={"x": 1}
        )
    )
    assert blocked is None and resp.status_code == 200
    method, url, kwargs = client.calls[-1]
    assert (method, url) == ("GET", "https://t.local/done")
    assert "json" not in kwargs  # body dropped on the GET follow-up


def test_persist_discovered_credential_refuses_out_of_scope_login(monkeypatch):
    """A credential whose login_url is on a different host than the site must
    NOT be saved into the site's credential store (the "Discovered by dynamic
    scan" foreign-credential bug)."""
    from aespa.models import Credential, Site, TestRun
    from aespa.services import scope as scope_svc

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        from aespa import models as _models  # noqa: F401

        SQLModel.metadata.create_all(engine)
        # Both the persister and check_scope must read the same DB.
        monkeypatch.setattr(scanner, "get_engine", lambda: engine)
        monkeypatch.setattr(scope_svc, "get_engine", lambda: engine)
        monkeypatch.setattr(scanner.events_svc, "emit", lambda *a, **k: None)

        with Session(engine) as session:
            site = Site(name="Bank of Ed", base_url="https://bankofed.local")
            session.add(site)
            session.commit()
            session.refresh(site)
            site.scope_hosts = '["bankofed.local"]'
            session.add(site)
            run = TestRun(site_id=site.id, name="run-1", status="scanning")
            session.add(run)
            session.commit()
            session.refresh(run)
            site_id, run_id = site.id, run.id

        # Off-host login → refused, nothing written.
        created = scanner._maybe_persist_discovered_credential(
            run_id,
            username="attacker",
            password="pw",
            login_url="https://evil-other.com/login",
        )
        assert created is False

        # In-scope login → saved.
        created = scanner._maybe_persist_discovered_credential(
            run_id,
            username="realuser",
            password="pw",
            login_url="https://bankofed.local/login",
        )
        assert created is True

        with Session(engine) as session:
            creds = session.exec(
                select(Credential).where(Credential.site_id == site_id)
            ).all()
        assert [c.username for c in creds] == ["realuser"]
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def test_compact_thinking_context_includes_all_existing_findings():
    findings = [
        {
            "severity": "medium",
            "owasp": "A01",
            "title": f"Finding {i}",
            "affected_url": f"https://target.local/finding/{i}",
        }
        for i in range(12)
    ]

    context = scanner._build_compact_thinking_context(
        "https://target.local",
        pages_snapshot=[],
        findings_snapshot=findings,
    )

    assert "+2 more" not in context
    assert "Finding 0 @ https://target.local/finding/0" in context
    assert "Finding 11 @ https://target.local/finding/11" in context


def test_load_findings_snapshot_returns_existing_findings(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        from aespa import models as _models  # noqa: F401

        SQLModel.metadata.create_all(engine)
        monkeypatch.setattr(scanner, "get_engine", lambda: engine)

        with Session(engine) as session:
            session.add(
                ScanFinding(
                    test_run_id=7,
                    owasp_category="A03",
                    severity="high",
                    title="SQL injection in /search",
                    affected_url="https://target.local/search",
                    description="param is concatenated into the query",
                )
            )
            # A finding for a different run must not leak in.
            session.add(
                ScanFinding(
                    test_run_id=99,
                    owasp_category="A01",
                    severity="low",
                    title="Other run finding",
                    affected_url="https://other.local",
                    description="unrelated",
                )
            )
            session.commit()

        snapshot = scanner._load_findings_snapshot(7)

        assert len(snapshot) == 1
        assert snapshot[0]["id"] == 1
        assert snapshot[0]["title"] == "SQL injection in /search"
        assert snapshot[0]["owasp"] == "A03"

        # finding_list over the loaded snapshot must surface the finding rather
        # than the empty-list regression that returned count 0 (issue #124).
        result = scanner._run_thinking_context_tool(
            "finding_list",
            {"category": "sqli"},
            pages_snapshot=[],
            findings_snapshot=snapshot,
            history=[],
            run_id=7,
        )
        assert result["count"] == 1
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def _finding_list(args, snapshot):
    return scanner._run_thinking_context_tool(
        "finding_list",
        args,
        pages_snapshot=[],
        findings_snapshot=snapshot,
        history=[],
        run_id=1,
    )


def test_finding_list_category_filter():
    snapshot = [
        {
            "title": "SQL injection in /search",
            "severity": "high",
            "owasp": "A03",
            "affected_url": "https://t/search",
            "description": "blind sql",
        },
        {
            "title": "Reflected XSS in name param",
            "severity": "medium",
            "owasp": "A03",
            "affected_url": "https://t/profile",
            "description": "cross-site scripting",
        },
        {
            "title": "SSRF via webhook url",
            "severity": "high",
            "owasp": "A10",
            "affected_url": "https://t/webhook",
            "description": "server-side request forgery",
        },
    ]

    # Vuln-class slug matches only its class, not other A03 findings.
    sqli = _finding_list({"category": "sqli"}, snapshot)
    assert sqli["count"] == 1
    assert sqli["findings"][0]["title"].startswith("SQL injection")

    # Alias resolves to canonical slug.
    assert _finding_list({"category": "RCE"}, snapshot)["count"] == 0
    assert _finding_list({"category": "cross-site scripting"}, snapshot)["count"] == 1

    # Keyword match catches a finding even if its owasp code differs from the map.
    assert _finding_list({"category": "ssrf"}, snapshot)["count"] == 1

    # owasp_category still filters by exact code (both injection findings).
    assert _finding_list({"owasp_category": "A03"}, snapshot)["count"] == 2

    # Unknown slug degrades into a free-text search token.
    assert _finding_list({"category": "webhook"}, snapshot)["count"] == 1
    assert _finding_list({"category": "nonexistentclass"}, snapshot)["count"] == 0

    # No filter returns everything.
    assert _finding_list({}, snapshot)["count"] == 3


def test_burp_scan_body_uses_default_configuration_when_name_blank():
    body = burp_rest._build_scan_body(
        "https://target.local/api/customers?search=test",
        cookies=None,
        extra_headers=None,
        application_logins=None,
        scan_configuration_name=None,
    )

    assert "scan_configurations" not in body


def test_burp_scan_body_can_use_named_configuration():
    body = burp_rest._build_scan_body(
        "https://target.local/api/customers?search=test",
        cookies=None,
        extra_headers=None,
        application_logins=None,
        scan_configuration_name="Fast audit",
    )

    assert body["scan_configurations"] == [
        {"name": "Fast audit", "type": "NamedConfiguration"}
    ]


def test_burp_investigation_candidate_detects_sqli_intent():
    candidate = scanner._burp_investigation_candidate(
        {
            "url": "https://target.local/api/admin/customers?search=test'",
            "hypothesis": "Admin customers list - test SQL injection in search parameter",
            "payload_purpose": "Test SQL injection in admin customers search",
        },
        "investigating Admin customers list",
    )

    assert candidate == (
        "SQL Injection",
        "Admin customers list - test SQL injection in search parameter",
    )


def test_burp_investigation_candidate_detects_additional_active_scan_classes():
    cases = [
        ("test OS command injection in ping parameter", "Command Injection"),
        ("probe path traversal with ../../etc/passwd", "Path Traversal"),
        ("test SSRF URL fetcher against localhost", "SSRF"),
        ("test XXE payload in XML parser", "XXE"),
        ("test server-side template injection with {{7*7}}", "SSTI"),
    ]

    for hypothesis, expected in cases:
        candidate = scanner._burp_investigation_candidate(
            {
                "url": "https://target.local/api/test",
                "hypothesis": hypothesis,
            },
            "investigating input validation",
        )
        assert candidate is not None
        assert candidate[0] == expected


def test_dynamic_finding_can_be_saved_without_page_assignment():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        from aespa import models as _models  # noqa: F401

        SQLModel.metadata.create_all(engine)

        finding = scanner._finding_from_llm(
            run_id=1,
            page_id=None,
            page_url="https://target.local",
            raw={
                "owasp_category": "A05",
                "title": "Global security header missing",
                "affected_url": "global application configuration",
            },
            result_by_url={},
            validation_status="unvalidated",
            validation_note=None,
        )

        with Session(engine) as session:
            session.add(finding)
            session.commit()
            saved = session.get(ScanFinding, finding.id)

        assert saved is not None
        assert saved.page_id is None
        assert saved.affected_url == "global application configuration"
        assert saved.finding_source == "dynamic_scan"
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def test_finding_from_llm_preserves_large_request_response_evidence():
    long_request = "POST /api/search HTTP/1.1\nContent-Type: application/json\n\n" + (
        "A" * 9000
    )
    long_response = "HTTP/1.1 200 OK\nContent-Type: application/json\n\n" + (
        "B" * 12000
    )

    finding = scanner._finding_from_llm(
        run_id=1,
        page_id=2,
        page_url="https://target.local/search",
        raw={
            "owasp_category": "A03",
            "title": "Verbose response evidence",
            "affected_url": "https://target.local/search",
            "cvss_score": 5.3,
        },
        result_by_url={
            "https://target.local/search": {
                "request_evidence": long_request,
                "response_evidence": long_response,
            }
        },
    )

    assert len(finding.request_evidence) > 8000
    assert len(finding.response_evidence) > 11000
    assert len(finding.evidence) > 19000
    assert "REQUEST:" in finding.evidence
    assert "RESPONSE:" in finding.evidence


def test_finding_from_llm_emits_structured_evidence_items():
    finding = scanner._finding_from_llm(
        run_id=1,
        page_id=2,
        page_url="https://target.local/admin",
        raw={
            "owasp_category": "A01",
            "title": "Authorization bypass",
            "affected_url": "https://target.local/admin",
            "evidence": "Anonymous actor received a protected response.",
            "cvss_score": 8.1,
        },
        result_by_url={
            "https://target.local/admin": {
                "status": 200,
                "request_evidence": "GET /admin HTTP/1.1\nAuthorization: Bearer secret-token",
                "response_evidence": "HTTP/1.1 200 OK\n\nadmin panel",
            }
        },
    )

    item_types = {item["type"] for item in finding.evidence_items}
    assert {"summary", "status", "http_request", "http_response"} <= item_types
    assert "secret-token" not in finding.evidence_json
    assert any(
        item["value"] == "200"
        for item in finding.evidence_items
        if item["type"] == "status"
    )


def test_http_evidence_items_include_timing_diff_outcome_and_screenshot():
    evidence_json = scanner._http_evidence_items_json(
        "GET /admin HTTP/1.1",
        "HTTP/1.1 200 OK\n\nadmin panel",
        summary="Admin panel rendered for an anonymous request.",
        status=200,
        status_delta="anonymous 200 vs expected 403",
        duration_ms=42,
        timing_delta_ms=1250,
        body_diff={"added_terms": ["admin", "settings"]},
        action_outcome="Request succeeded without an authenticated session.",
        action_log=["goto /admin", "snapshot"],
        screenshot_b64="abc123",
    )
    item_types = {
        item["type"] for item in scanner._evidence_items_from_json(evidence_json)
    }

    assert {
        "status_delta",
        "timing",
        "timing_delta",
        "body_diff",
        "action_outcome",
        "action_log",
        "screenshot",
    } <= item_types


def test_session_request_headers_remove_primary_credentials_for_anonymous():
    primary = {
        "extra_headers": {
            "Authorization": "Bearer primary-secret",
            "X-Session-Key": "primary-key",
        }
    }
    anonymous = {"kind": "anonymous", "cookies": {}, "extra_headers": {}}

    headers = scanner._session_request_headers(
        {
            "User-Agent": "aespa",
            "Authorization": "Bearer primary-secret",
            "X-Session-Key": "primary-key",
            "Accept": "*/*",
        },
        anonymous,
        default_session=primary,
    )

    assert "authorization" not in {key.lower() for key in headers}
    assert "x-session-key" not in {key.lower() for key in headers}
    assert headers["User-Agent"] == "aespa"
    assert headers["Accept"] == "*/*"


def test_session_request_headers_replace_primary_with_selected_identity():
    headers = scanner._session_request_headers(
        {"Authorization": "Bearer primary-secret", "User-Agent": "aespa"},
        {"extra_headers": {"Authorization": "Bearer alternate-secret"}},
        default_session={"extra_headers": {"Authorization": "Bearer primary-secret"}},
    )

    assert headers["Authorization"] == "Bearer alternate-secret"
    assert "primary-secret" not in str(headers)


def test_sent_request_auth_summary_reports_presence_without_secret():
    summary = scanner._sent_request_auth_summary(
        {
            "Authorization": "Bearer secret-token",
            "Cookie": "session=secret; theme=dark",
        }
    )

    assert "Authorization: present" in summary
    assert "Cookies: session, theme" in summary
    assert "secret-token" not in summary


def test_finding_from_llm_preserves_prebuilt_probe_evidence_items():
    evidence_json = scanner._http_evidence_items_json(
        "BROWSER ACTION\nInitial URL: https://target.local/admin",
        "Final URL: https://target.local/admin\nVisible text excerpt:\nadmin panel",
        summary="Browser action reached admin panel.",
        status=200,
        action_outcome="Browser action completed.",
        action_log=["goto https://target.local/admin", "snapshot"],
        screenshot_b64="abc123",
    )

    finding = scanner._finding_from_llm(
        run_id=1,
        page_id=2,
        page_url="https://target.local/admin",
        raw={
            "owasp_category": "A01",
            "title": "Authorization bypass",
            "affected_url": "https://target.local/admin",
            "evidence": "Browser evidence showed the admin panel.",
            "cvss_score": 8.1,
        },
        result_by_url={
            "https://target.local/admin": {
                "status": 200,
                "request_evidence": "BROWSER ACTION",
                "response_evidence": "admin panel",
                "evidence_json": evidence_json,
                "screenshot_b64": "abc123",
            }
        },
    )

    item_types = {item["type"] for item in finding.evidence_items}
    assert {"action_outcome", "action_log", "screenshot"} <= item_types
    assert finding.screenshot_b64 == "abc123"
    assert finding.finding_source == "dynamic_scan"


def test_dynamic_page_assignment_returns_none_for_non_page_finding():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        from aespa import models as _models  # noqa: F401

        SQLModel.metadata.create_all(engine)

        with Session(engine) as session:
            page_id = scanner._dynamic_finding_page_id(
                session,
                run_id=1,
                affected_url="global application configuration",
                base_url="https://target.local",
                pages_snapshot=[],
                first_page_id=None,
            )

        assert page_id is None
    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def test_cvss_score_calculator():
    # Test known CVSS v3.1 vectors
    # 1. SQLi: CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N -> 9.1
    metrics1 = scanner.parse_cvss_vector("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N")
    assert scanner.calculate_cvss_score(metrics1) == 9.1

    # 2. XSS: CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N -> 6.1
    metrics2 = scanner.parse_cvss_vector("CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N")
    assert scanner.calculate_cvss_score(metrics2) == 6.1

    # 3. Low: CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:N/A:N -> 3.1
    metrics3 = scanner.parse_cvss_vector("CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:N/A:N")
    assert scanner.calculate_cvss_score(metrics3) == 3.1


def test_calibrate_finding_rating():
    # 1. CORS should calibrate to 3.1 (Low)
    score, severity, vector = scanner._calibrate_finding_rating(
        "CORS arbitrary Origin reflection",
        6.5,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:N/A:N",
    )
    assert score == 3.1
    assert severity == "low"
    assert "AC:H" in vector
    assert "C:L" in vector
    assert "I:N" in vector

    # 2. Server headers (including CSP) should calibrate to 3.7 (Low) or 0.0 (Info)
    score, severity, vector = scanner._calibrate_finding_rating(
        "Content-Security-Policy missing",
        5.3,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N",
    )
    assert score == 3.7
    assert severity == "low"
    assert "AC:H" in vector
    assert "C:L" in vector

    # 3. Username enumeration should calibrate to 3.7 (Low)
    score, severity, vector = scanner._calibrate_finding_rating(
        "Username Enumeration on login page",
        5.3,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N",
    )
    assert score == 3.7
    assert severity == "low"
    assert "AC:H" in vector

    # 4. Session logout invalidation should calibrate to 3.6 (Low)
    score, severity, vector = scanner._calibrate_finding_rating(
        "Session not invalidated on logout",
        7.5,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N",
    )
    assert score == 3.6
    assert severity == "low"
    assert "AV:L" in vector
    assert "AC:H" in vector
    assert "C:L" in vector
    assert "I:L" in vector

    # 5. Stack trace should calibrate to 3.7 (Low)
    score, severity, vector = scanner._calibrate_finding_rating(
        "Verbose stack trace disclosure",
        5.3,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N",
    )
    assert score == 3.7
    assert severity == "low"
    assert "AC:H" in vector

    # 6. Generic info disclosure (without secrets) should calibrate to 3.7 (Low)
    score, severity, vector = scanner._calibrate_finding_rating(
        "Internal path disclosure", 5.3, "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N"
    )
    assert score == 3.7
    assert severity == "low"
    assert "AC:H" in vector

    # Sensitive data exposed (with secrets) should NOT calibrate
    score, severity, vector = scanner._calibrate_finding_rating(
        "Sensitive data exposed: private key leaked",
        7.5,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
    )
    assert score == 7.5
    assert severity == "high"

    # 7. Rate Limiting (normal) should calibrate to 3.7 (Low)
    score, severity, vector = scanner._calibrate_finding_rating(
        "Missing login rate limiting",
        5.3,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N",
    )
    assert score == 3.7
    assert severity == "low"
    assert "AC:H" in vector

    # Rate Limiting (TOTP/MFA) should calibrate to 5.3 (Medium)
    score, severity, vector = scanner._calibrate_finding_rating(
        "Rate limiting bypass on TOTP validation",
        7.5,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N",
    )
    assert score == 5.3
    assert severity == "medium"
    assert "AC:L" in vector
    assert "C:N" in vector
    assert "I:N" in vector
    assert "A:L" in vector

    # 8. Unaffected findings (SQL Injection) should remain unchanged even with verbose error in title
    score, severity, vector = scanner._calibrate_finding_rating(
        "SQL injection in admin customer search with verbose PDO error disclosure",
        8.6,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
    )
    assert score == 8.6
    assert severity == "high"


def test_calibrate_all_findings_for_run():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        from aespa import models as _models  # noqa: F401

        SQLModel.metadata.create_all(engine)

        with Session(engine) as session:
            # Add one CORS finding (should calibrate to Low) and one SQLi finding (should remain High)
            cors = ScanFinding(
                test_run_id=1,
                owasp_category="A05",
                severity="medium",
                title="CORS arbitrary Origin reflection",
                description="",
                cvss_score=6.5,
                cvss_vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:N/A:N",
            )
            sqli = ScanFinding(
                test_run_id=1,
                owasp_category="A03",
                severity="high",
                title="SQL injection error disclosure",
                description="",
                cvss_score=7.1,
                cvss_vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N",
            )
            session.add(cors)
            session.add(sqli)
            session.commit()

        # Monkeypatch get_engine to use our memory db
        from unittest import mock

        with mock.patch("aespa.services.scanner.get_engine", return_value=engine):
            scanner.calibrate_all_findings_for_run(1)

        with Session(engine) as session:
            findings = session.exec(select(ScanFinding)).all()
            for f in findings:
                if "CORS" in f.title:
                    assert f.severity == "low"
                    assert f.cvss_score == 3.1
                    assert "AC:H" in f.cvss_vector
                else:
                    assert f.severity == "high"
                    assert f.cvss_score == 7.1

    finally:
        SQLModel.metadata.drop_all(engine)
        engine.dispose()
