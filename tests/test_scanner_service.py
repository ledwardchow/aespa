from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from aespa.models import ScanFinding
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
