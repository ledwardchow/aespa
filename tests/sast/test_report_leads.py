"""External reports stay unverified and isolated to their destination run."""

from __future__ import annotations

import json
from urllib.parse import quote

import pytest
from sqlmodel import select

from aespa.models import ApiCollection, ApiTestRun, ScanFinding, ScanLead, Site
from aespa.models import TestRun as WebRun
from aespa.services import report_leads
from aespa.services.scan_leads import get_lead_detail_for_run, get_leads_for_run


@pytest.fixture
def destinations(db_session):
    site = Site(name="Portal", base_url="http://portal.test")
    collection = ApiCollection(name="API", base_url="http://api.test")
    db_session.add_all([site, collection])
    db_session.flush()
    web = WebRun(site_id=site.id, name="Web", status="scanning")
    api = ApiTestRun(collection_id=collection.id, name="API", status="scanning")
    db_session.add_all([web, api])
    db_session.commit()
    return {"web": web.id, "api": api.id}


def sarif():
    return {
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "Example scanner",
                        "rules": [
                            {
                                "id": "sql-injection",
                                "shortDescription": {"text": "SQL injection"},
                                "properties": {
                                    "security-severity": "9.1",
                                    "tags": ["CWE-89"],
                                },
                            }
                        ],
                    }
                },
                "results": [
                    {
                        "ruleId": "sql-injection",
                        "level": "warning",
                        "message": {"text": "User input reaches a SQL query."},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {
                                        "uri": "src/query%20handler.py"
                                    },
                                    "region": {
                                        "startLine": 42,
                                        "startColumn": 3,
                                        "snippet": {"text": "db.query(user_input)"},
                                    },
                                }
                            }
                        ],
                        "codeFlows": [
                            {
                                "threadFlows": [
                                    {
                                        "locations": [
                                            {
                                                "location": {
                                                    "message": {
                                                        "text": "Input reaches query"
                                                    }
                                                }
                                            }
                                        ]
                                    }
                                ]
                            }
                        ],
                        "properties": {
                            "validationStatus": "confirmed",
                            "status": "confirmed",
                        },
                    }
                ],
            }
        ],
    }


@pytest.mark.parametrize("kind", ["web", "api"])
def test_preview_import_duplicate_and_run_isolation(
    client, db_session, destinations, kind
):
    run_id = destinations[kind]
    prefix = "api-test-runs" if kind == "api" else "test-runs"
    url = f"/api/{prefix}/{run_id}/import-report"
    payload = json.dumps(sarif()).encode()
    preview = client.post(url, files={"file": ("report.sarif", payload)})
    assert preview.status_code == 200
    assert preview.json()["new_count"] == 1
    assert preview.json()["items"][0]["severity"] == "critical"
    assert db_session.exec(select(ScanLead)).all() == []
    assert db_session.exec(select(ScanFinding)).all() == []
    imported = client.post(
        url, files={"file": ("../report.sarif", payload)}, data={"preview": "false"}
    )
    assert imported.status_code == 200
    assert imported.json()["imported"] == 1
    [lead] = get_leads_for_run(kind, run_id)
    assert lead.status == "open" and lead.validation_status == "pending"
    assert lead.confidence == 0
    assert lead.location == "src/query handler.py:42:3"
    assert "db.query(user_input)" in lead.evidence
    assert "Input reaches query" in lead.evidence
    assert lead.source == "Example scanner" and lead.category == "CWE-89"
    assert lead.producer_run_type == "external"
    trace = json.loads(lead.source_trace_json)
    assert trace["external_report"]["filename"] == "report.sarif"
    assert trace["external_report"]["rule_id"] == "sql-injection"
    assert lead.reference
    assert (
        get_lead_detail_for_run(kind, run_id, lead_id=lead.id)["source_sast_run_id"]
        is None
    )
    assert get_leads_for_run("api" if kind == "web" else "web", run_id) == []
    repeated = client.post(
        url, files={"file": ("renamed.sarif", payload)}, data={"preview": "false"}
    )
    assert repeated.json()["imported"] == 0
    assert repeated.json()["already_imported"] == 1
    assert len(get_leads_for_run(kind, run_id)) == 1
    assert db_session.exec(select(ScanFinding)).all() == []
    model = WebRun if kind == "web" else ApiTestRun
    db_session.expire_all()
    assert db_session.get(model, run_id).status == "scanning"


def test_sarif_multiple_tools_suppression_and_message_templates():
    document = sarif()
    run = document["runs"][0]
    run["tool"]["extensions"] = [
        {
            "name": "Extension scanner",
            "rules": [
                {
                    "id": "X",
                    "messageStrings": {"detail": {"text": "Input reaches {0}."}},
                    "defaultConfiguration": {"level": "error"},
                }
            ],
        }
    ]
    run["artifacts"] = [{"location": {"uri": "src/extension.py"}}]
    run["results"].extend(
        [
            {
                "message": {"text": "Suppressed"},
                "suppressions": [{"kind": "external", "status": "accepted"}],
            },
            {"message": {"text": "Gone"}, "baselineState": "absent"},
            {"message": {"text": "Passed"}, "kind": "pass"},
            {
                "rule": {"index": 0, "toolComponent": {"index": 0}},
                "message": {"id": "detail", "arguments": ["sink"]},
                "locations": [{"physicalLocation": {"artifactLocation": {"index": 0}}}],
            },
        ]
    )
    document["runs"].append(
        {
            "tool": {"driver": {"name": "Second scanner"}},
            "results": [
                {"message": {"markdown": "Another suspected issue"}, "level": "note"}
            ],
        }
    )
    _, leads, warnings, skipped = report_leads.parse_report(
        json.dumps(document).encode(), "report.json"
    )
    assert skipped == 3 and len(leads) == 3
    assert leads[1].scanner == "Extension scanner"
    assert leads[1].description == "Input reaches sink."
    assert leads[1].severity == "high" and leads[1].location == "src/extension.py"
    assert leads[2].severity == "low"
    assert any("no location" in warning for warning in warnings)


def test_markdown_template_fences_and_metadata():
    text = b"""# Scanner findings

## 1. Missing access check
- **Scanner:** Example scanner
- Severity: HIGH
- Rule ID: auth-001
- Category: A01
- Location: src/orders.py:12
- Confidence: 80%
- Suggested endpoint: GET /orders/{id}

### Description
The order handler does not check the caller's ownership.

### Evidence
```python
## This is code, not a finding
return order
```

## Redirect issue
- Severity: low
- Location: src/auth.py:8
### Description
A redirect accepts an untrusted URL.
"""
    _, leads, _, _ = report_leads.parse_report(text, "report.md")
    assert len(leads) == 2
    assert leads[0].scanner == "Example scanner"
    assert leads[0].rule_id == "auth-001"
    assert leads[0].severity == "high" and leads[0].confidence == 0.8
    assert leads[0].suggested_endpoint == "GET /orders/{id}"
    assert "## This is code" in leads[0].evidence
    assert "ownership" in leads[0].description


def test_aespa_markdown_export_ignores_imported_verdicts(client, destinations):
    items = [
        {
            "title": "Exported lead",
            "severity": "high",
            "confidence": 0.9,
            "location": "app.py:3",
            "source": "sast",
            "status": "confirmed",
            "linked_finding_id": 44,
        }
    ]
    text = "<!-- aespa-sast-leads-json\n" + quote(json.dumps(items)) + "\n-->"
    url = f"/api/test-runs/{destinations['web']}/import-report"
    response = client.post(
        url, files={"file": ("leads.md", text)}, data={"preview": "false"}
    )
    assert response.json()["imported"] == 1
    [lead] = get_leads_for_run("web", destinations["web"])
    assert lead.status == "open" and lead.validation_status == "pending"
    assert lead.linked_finding_id is None


@pytest.mark.parametrize(
    "filename,content",
    [
        ("empty.md", b""),
        ("random.md", b"No structured findings"),
        ("bad.sarif", b"{"),
        ("bad.json", b'{"version":"1.0","runs":[]}'),
        ("bad.sarif", b'{"version":"2.1.0","runs":{}}'),
        ("bad.md", b"\xff"),
        ("file.txt", b"random text"),
        ("bad.md", b"## Finding\n- Severity: urgent"),
        ("bad.md", b"## Finding\n- Confidence: NaN"),
        ("bad.md", b"<!-- aespa-sast-leads-json\nnot-json\n-->"),
    ],
)
def test_invalid_reports_never_write(
    client, db_session, destinations, filename, content
):
    response = client.post(
        f"/api/test-runs/{destinations['web']}/import-report",
        files={"file": (filename, content)},
        data={"preview": "false"},
    )
    assert response.status_code == 422
    assert db_session.exec(select(ScanLead)).all() == []


def test_upload_limits_and_missing_target(client, destinations, monkeypatch):
    monkeypatch.setattr(report_leads, "MAX_REPORT_BYTES", 20)
    url = f"/api/test-runs/{destinations['web']}/import-report"
    assert client.post(url, files={"file": ("report.md", b"x" * 21)}).status_code == 422
    assert (
        client.post(
            "/api/api-test-runs/999999/import-report",
            files={"file": ("report.md", b"test")},
        ).status_code
        == 404
    )


def test_duplicate_results_and_limit_are_explicit(monkeypatch):
    document = sarif()
    document["runs"][0]["results"] *= 2
    _, leads, warnings, skipped = report_leads.parse_report(
        json.dumps(document).encode(), "scan.sarif"
    )
    assert len(leads) == 1 and skipped == 1
    assert any("duplicate" in warning for warning in warnings)
    monkeypatch.setattr(report_leads, "MAX_RESULTS", 1)
    with pytest.raises(report_leads.ReportImportError, match="at most 1"):
        report_leads.parse_report(json.dumps(document).encode(), "scan.sarif")


def test_external_leads_enter_existing_dynamic_investigation(
    client, db_session, destinations
):
    from aespa.services.scan_leads import update_lead

    run_id = destinations["web"]
    response = client.post(
        f"/api/test-runs/{run_id}/import-report",
        files={"file": ("report.sarif", json.dumps(sarif()))},
        data={"preview": "false"},
    )
    assert response.json()["imported"] == 1
    [lead] = get_leads_for_run("web", run_id)
    assert (
        update_lead(
            lead.id, status="confirmed", owner_run_type="api", owner_run_id=run_id
        )
        is None
    )
    reviewed = update_lead(
        lead.id,
        status="confirmed",
        owner_run_type="web",
        owner_run_id=run_id,
        investigated_by_run_type="web",
        investigated_by_run_id=run_id,
        note="Verified against the live target (test fixture).",
        link_coverage=False,
    )
    finding = db_session.get(ScanFinding, reviewed.linked_finding_id)
    assert finding.test_run_id == run_id and finding.api_test_run_id is None
    assert finding.origin_type == "external"
    assert finding.reference == lead.reference


def test_suppression_under_review_remains_an_unverified_lead():
    document = sarif()
    document["runs"][0]["results"][0]["suppressions"] = [
        {"kind": "external", "status": "underReview"}
    ]
    _, leads, _, skipped = report_leads.parse_report(
        json.dumps(document).encode(), "report.sarif"
    )
    assert len(leads) == 1 and skipped == 0


def test_markdown_round_trip_keeps_external_rule_identity(client, destinations):
    document = sarif()
    run_id = destinations["web"]
    url = f"/api/test-runs/{run_id}/import-report"
    assert (
        client.post(
            url,
            files={"file": ("scan.sarif", json.dumps(document))},
            data={"preview": "false"},
        ).json()["imported"]
        == 1
    )
    [lead] = get_leads_for_run("web", run_id)
    payload = [
        {
            "title": lead.title,
            "scanner": lead.source,
            "rule_id": "sql-injection",
            "location": lead.location,
            "severity": lead.severity,
        }
    ]
    markdown = "<!-- aespa-sast-leads-json\n" + quote(json.dumps(payload)) + "\n-->"
    result = client.post(
        url, files={"file": ("leads.md", markdown)}, data={"preview": "false"}
    ).json()
    assert result["imported"] == 0 and result["already_imported"] == 1


def test_invalid_unicode_in_sarif_fails_before_writing(
    client, db_session, destinations
):
    document = sarif()
    document["runs"][0]["results"][0]["message"] = {"text": "\ud800"}
    result = client.post(
        f"/api/test-runs/{destinations['web']}/import-report",
        files={"file": ("scan.sarif", json.dumps(document))},
        data={"preview": "false"},
    )
    assert result.status_code == 422
    assert db_session.exec(select(ScanLead)).all() == []
