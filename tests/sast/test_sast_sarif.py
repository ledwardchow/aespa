"""Tests for SAST SARIF 2.1.0 export functionality and API endpoint."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from aespa import db as db_mod
from aespa.db import get_session, set_engine
from aespa.main import create_app
from aespa.models import SastRun, ScanLead
from aespa.services import sast_sarif

_UTC = timezone.utc


@pytest.fixture(name="env")
def env_fixture():
    """Isolated in-memory database and test client."""
    prev_engine = db_mod._engine
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from aespa import models as _models  # noqa: F401

    SQLModel.metadata.create_all(engine)
    set_engine(engine)

    def _override_session():
        with Session(engine) as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = _override_session
    with TestClient(app, raise_server_exceptions=True) as c:
        yield engine, c
    set_engine(prev_engine)


def test_parse_location_formats():
    # path:line
    path, line, col, endpoint = sast_sarif.parse_location("src/auth/jwt.py:42")
    assert path == "src/auth/jwt.py"
    assert line == 42
    assert col is None
    assert endpoint is None

    # path:line:col
    path, line, col, endpoint = sast_sarif.parse_location("src/auth/jwt.py:42:15")
    assert path == "src/auth/jwt.py"
    assert line == 42
    assert col == 15
    assert endpoint is None

    # bare file path
    path, line, col, endpoint = sast_sarif.parse_location("controllers/user.ts")
    assert path == "controllers/user.ts"
    assert line == 1
    assert col is None
    assert endpoint is None

    # HTTP endpoint with trace fallback
    sink_trace = {"file": "src/routes.py", "line": 88}
    path, line, col, endpoint = sast_sarif.parse_location(
        "POST /api/v1/login", sink_trace=sink_trace
    )
    assert path == "src/routes.py"
    assert line == 88
    assert endpoint == "POST /api/v1/login"

    # HTTP endpoint without trace fallback
    path, line, col, endpoint = sast_sarif.parse_location(
        "GET /api/v1/users", fallback_filename="archive.zip"
    )
    assert path == "archive.zip"
    assert line == 1
    assert endpoint == "GET /api/v1/users"


def test_map_severity():
    assert sast_sarif.map_severity_to_level("critical") == "error"
    assert sast_sarif.map_severity_to_level("high") == "error"
    assert sast_sarif.map_severity_to_level("medium") == "warning"
    assert sast_sarif.map_severity_to_level("low") == "note"
    assert sast_sarif.map_severity_to_level("info") == "note"

    assert sast_sarif.map_severity_to_score("critical") == "9.0"
    assert sast_sarif.map_severity_to_score("high") == "7.5"
    assert sast_sarif.map_severity_to_score("medium") == "5.0"
    assert sast_sarif.map_severity_to_score("low") == "2.5"
    assert sast_sarif.map_severity_to_score("info") == "0.0"


def test_build_sarif_rules_deduplication():
    lead1 = ScanLead(
        producer_run_id=1,
        producer_run_type="sast",
        category="A03:2021-Injection",
        title="SQL Injection",
        description="SQL injection in users",
        severity="high",
        confidence=0.9,
    )
    lead2 = ScanLead(
        producer_run_id=1,
        producer_run_type="sast",
        category="A03:2021-Injection",
        title="Command Injection",
        description="Command injection in ping",
        severity="critical",
        confidence=0.95,
    )
    lead3 = ScanLead(
        producer_run_id=1,
        producer_run_type="sast",
        category="A01:2021-Broken Access Control",
        title="IDOR in profile",
        description="Direct reference without auth check",
        severity="medium",
        confidence=0.8,
    )

    rules, index_map = sast_sarif.build_sarif_rules([lead1, lead2, lead3])
    assert len(rules) == 2
    assert "AESPA/A03-2021-Injection" in index_map
    assert "AESPA/A01-2021-Broken-Access-Control" in index_map
    assert index_map["AESPA/A03-2021-Injection"] == 0
    assert index_map["AESPA/A01-2021-Broken-Access-Control"] == 1

    rule0 = rules[0]
    assert rule0["id"] == "AESPA/A03-2021-Injection"
    assert "defaultConfiguration" in rule0
    assert rule0["defaultConfiguration"]["level"] == "error"
    assert "security-severity" in rule0["properties"]


def test_generate_sast_sarif_and_api(env):
    engine, client = env

    now = datetime.now(_UTC)
    with Session(engine) as session:
        run = SastRun(
            name="Security Review - App",
            status="completed",
            source_filename="app_source.zip",
            started_at=now,
            completed_at=now,
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

        # Confirmed reportable lead
        confirmed_lead = ScanLead(
            producer_run_id=run_id,
            producer_run_type="sast",
            title="SQL Injection in user search",
            description="User query is concatenated directly into SQLite cursor.",
            category="A03:2021-Injection",
            severity="high",
            confidence=0.95,
            location="src/db/queries.py:45",
            evidence="cursor.execute(f'SELECT * FROM users WHERE id = {user_id}')",
            fingerprint="hash-sql-injection",
            validation_status="confirmed",
            validation_reasoning="Validator verified unescaped f-string reaching cursor.execute",
            reportable=True,
            public_reference="REF-SAST-001",
            source_trace_json=json.dumps(
                {
                    "file": "src/api/routes.py",
                    "line": 12,
                    "symbol": "user_id",
                    "input": "query param",
                }
            ),
            control_trace_json=json.dumps(["Checked length > 0"]),
            sink_trace_json=json.dumps(
                {
                    "file": "src/db/queries.py",
                    "line": 45,
                    "symbol": "cursor.execute",
                    "operation": "SQL execution",
                }
            ),
            counterevidence_json=json.dumps(["No ORM parameterization used"]),
            proof_gaps_json=json.dumps(["None"]),
            attack_path_json=json.dumps(
                {"dynamic_test": "Inject ' OR 1=1 -- into id parameter"}
            ),
        )

        # Dismissed lead
        dismissed_lead = ScanLead(
            producer_run_id=run_id,
            producer_run_type="sast",
            title="Potential SSRF in webhook handler",
            description="Webhook URL fetched via requests.post",
            category="A10:2021-SSRF",
            severity="medium",
            confidence=0.45,
            location="src/services/webhook.py:30",
            fingerprint="hash-ssrf",
            validation_status="dismissed",
            validation_reasoning="URL is hardcoded from internal configuration, not user controllable.",
            reportable=False,
            public_reference="REF-SAST-002",
        )

        session.add(confirmed_lead)
        session.add(dismissed_lead)
        session.commit()

    # 1. Test generate_sast_sarif directly with default reportable_only=False (includes all candidates)
    with Session(engine) as session:
        sarif = sast_sarif.generate_sast_sarif(session, run_id)

    assert sarif["$schema"] == "https://json.schemastore.org/sarif-2.1.0.json"
    assert sarif["version"] == "2.1.0"
    assert len(sarif["runs"]) == 1

    run_obj = sarif["runs"][0]
    assert run_obj["tool"]["driver"]["name"] == "AESPA"
    assert len(run_obj["invocations"]) == 1
    assert run_obj["invocations"][0]["executionSuccessful"] is True

    # Both confirmed and dismissed candidates included by default
    assert len(run_obj["results"]) == 2
    result = run_obj["results"][0]
    assert result["ruleId"] == "AESPA/A03-2021-Injection"
    assert result["level"] == "error"
    assert result["rank"] == 95.0
    assert result["partialFingerprints"]["primaryLocationHash"] == "hash-sql-injection"

    # Locations check
    assert len(result["locations"]) == 1
    loc = result["locations"][0]["physicalLocation"]
    assert loc["artifactLocation"]["uri"] == "src/db/queries.py"
    assert loc["region"]["startLine"] == 45
    assert "snippet" in loc["region"]

    # Code flow check
    assert "codeFlows" in result
    flow = result["codeFlows"][0]["threadFlows"][0]["locations"]
    assert len(flow) == 3  # source, control, sink
    assert flow[0]["importance"] == "essential"
    assert flow[1]["importance"] == "important"
    assert flow[2]["importance"] == "essential"

    # Property bag check
    props = result["properties"]
    assert props["leadReference"] == "REF-SAST-001"
    assert props["confidence"] == 0.95
    assert props["validationStatus"] == "confirmed"
    assert (
        props["validationReasoning"]
        == "Validator verified unescaped f-string reaching cursor.execute"
    )
    assert props["counterevidence"] == ["No ORM parameterization used"]
    assert props["proofGaps"] == ["None"]
    assert props["attackPath"]["dynamic_test"] == "Inject ' OR 1=1 -- into id parameter"

    # Markdown message check
    assert "Validator Reasoning" in result["message"]["markdown"]
    assert "Dynamic Test Guidance" in result["message"]["markdown"]

    # Dismissed result checks (suppressions present)
    dismissed_result = run_obj["results"][1]
    assert dismissed_result["ruleId"] == "AESPA/A10-2021-SSRF"
    assert dismissed_result["rank"] == 45.0
    assert "suppressions" in dismissed_result
    assert dismissed_result["suppressions"][0]["kind"] == "external"
    assert dismissed_result["suppressions"][0]["status"] == "accepted"
    assert (
        "internal configuration" in dismissed_result["suppressions"][0]["justification"]
    )

    # 2. Test generate_sast_sarif with reportable_only=True (filters down to reportable only)
    with Session(engine) as session:
        sarif_reportable = sast_sarif.generate_sast_sarif(
            session, run_id, reportable_only=True
        )
    assert len(sarif_reportable["runs"][0]["results"]) == 1

    # 3. Test HTTP API endpoint default (includes all candidates)
    resp = client.get(f"/api/sast-runs/{run_id}/sarif")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/sarif+json")
    assert (
        'attachment; filename="Security_Review_-_App.sarif"'
        in resp.headers["content-disposition"]
    )
    data = resp.json()
    assert data["version"] == "2.1.0"
    assert len(data["runs"][0]["results"]) == 2

    # 4. Test API with reportable_only=true
    resp_reportable = client.get(f"/api/sast-runs/{run_id}/sarif?reportable_only=true")
    assert resp_reportable.status_code == 200
    assert len(resp_reportable.json()["runs"][0]["results"]) == 1

    # 5. Test 404 for missing run
    resp_404 = client.get("/api/sast-runs/999999/sarif")
    assert resp_404.status_code == 404
