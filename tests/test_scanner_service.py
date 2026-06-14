from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from aespa.models import CrawledPage, ScanFinding, Site, TrafficEntry
from aespa.models import TestRun as RunModel
from aespa.services import burp_rest
from aespa.services import scanner


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
        "finding_list", args,
        pages_snapshot=[], findings_snapshot=snapshot, history=[], run_id=1,
    )


def test_finding_list_category_filter():
    snapshot = [
        {"title": "SQL injection in /search", "severity": "high", "owasp": "A03",
         "affected_url": "https://t/search", "description": "blind sql"},
        {"title": "Reflected XSS in name param", "severity": "medium", "owasp": "A03",
         "affected_url": "https://t/profile", "description": "cross-site scripting"},
        {"title": "SSRF via webhook url", "severity": "high", "owasp": "A10",
         "affected_url": "https://t/webhook", "description": "server-side request forgery"},
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
    long_request = "POST /api/search HTTP/1.1\nContent-Type: application/json\n\n" + ("A" * 9000)
    long_response = "HTTP/1.1 200 OK\nContent-Type: application/json\n\n" + ("B" * 12000)

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
    assert any(item["value"] == "200" for item in finding.evidence_items if item["type"] == "status")


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
    item_types = {item["type"] for item in scanner._evidence_items_from_json(evidence_json)}

    assert {"status_delta", "timing", "timing_delta", "body_diff", "action_outcome", "action_log", "screenshot"} <= item_types


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
