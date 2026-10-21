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
    assert preview.json()["items"][0]["confidence"] is None
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


@pytest.mark.parametrize("kind", ["web", "api"])
def test_ai_report_preview_imports_exact_reviewed_lead(
    client, db_session, destinations, monkeypatch, kind
):
    calls = []

    async def complete(_config, prompt):
        calls.append(prompt)
        return json.dumps(
            {
                "total_found": 1,
                "findings": [
                    {
                        "title": "Missing ownership check",
                        "severity": "high",
                        "description": "The report describes an unchecked account lookup.",
                        "source_quote": "Account lookup has no ownership check",
                        "location": "src/accounts.py:10",
                        "confidence": None,
                    }
                ],
            }
        )

    monkeypatch.setattr(report_leads, "get_llm_config_for_run", lambda *_: object())
    monkeypatch.setattr(report_leads.llm_service, "plain_completion", complete)
    prefix = "api-test-runs" if kind == "api" else "test-runs"
    url = f"/api/{prefix}/{destinations[kind]}/import-report"
    content = b"Account lookup has no ownership check"
    preview = client.post(url, files={"file": ("notes.txt", content)})
    assert preview.status_code == 200, preview.text
    assert preview.json()["format"] == "AI-reviewed report"
    assert preview.json()["items"][0]["confidence"] is None
    assert preview.json()["items"][0]["source_quote"] == content.decode()
    assert (
        preview.json()["items"][0]["description"]
        == "The report describes an unchecked account lookup."
    )
    assert db_session.exec(select(ScanLead)).all() == []
    prepared = preview.json()["prepared"]
    imported = client.post(
        url,
        files={"file": ("notes.txt", content)},
        data={"preview": "false", "prepared": prepared},
    )
    assert imported.status_code == 200, imported.text
    assert imported.json()["imported"] == 1
    assert len(calls) == 1
    [lead] = get_leads_for_run(kind, destinations[kind])
    assert lead.title == preview.json()["items"][0]["title"]
    assert lead.description == preview.json()["items"][0]["description"]
    assert json.loads(lead.source_trace_json)["confidence_unknown"] is True
    assert (
        json.loads(lead.source_trace_json)["external_report"]["filename"] == "notes.txt"
    )


def test_ai_report_rejects_changed_file_and_ungrounded_quote(
    client, db_session, destinations, monkeypatch
):
    async def complete(_config, _prompt):
        return json.dumps(
            {
                "total_found": 1,
                "findings": [{"title": "Claim", "source_quote": "Missing source"}],
            }
        )

    monkeypatch.setattr(report_leads, "get_llm_config_for_run", lambda *_: object())
    monkeypatch.setattr(report_leads.llm_service, "plain_completion", complete)
    url = f"/api/test-runs/{destinations['web']}/import-report"
    rejected = client.post(url, files={"file": ("notes.txt", b"Different text")})
    assert rejected.status_code == 422
    assert "exact source quote" in rejected.json()["detail"]
    assert db_session.exec(select(ScanLead)).all() == []

    async def grounded(_config, _prompt):
        return json.dumps(
            {
                "total_found": 1,
                "findings": [{"title": "Claim", "source_quote": "Different text"}],
            }
        )

    monkeypatch.setattr(report_leads.llm_service, "plain_completion", grounded)
    prepared = client.post(
        url, files={"file": ("notes.txt", b"Different text")}
    ).json()["prepared"]
    changed = client.post(
        url,
        files={"file": ("notes.txt", b"Changed text")},
        data={"preview": "false", "prepared": prepared},
    )
    assert changed.status_code == 422
    assert db_session.exec(select(ScanLead)).all() == []


def test_malformed_sarif_does_not_call_model(client, destinations, monkeypatch):
    async def fail_if_called(*_args):
        pytest.fail("Malformed SARIF must not use the model")

    monkeypatch.setattr(report_leads.llm_service, "plain_completion", fail_if_called)
    url = f"/api/test-runs/{destinations['web']}/import-report"
    response = client.post(url, files={"file": ("broken.sarif", b'{"runs": []}')})
    assert response.status_code == 422


def test_ai_report_size_limit_is_explicit(client, destinations):
    url = f"/api/test-runs/{destinations['web']}/import-report"
    response = client.post(
        url,
        files={"file": ("large.txt", b"a" * (report_leads.MAX_LLM_REPORT_BYTES + 1))},
    )
    assert response.status_code == 422
    assert "128 KiB" in response.json()["detail"]


def test_ai_report_rejects_model_context_truncation(client, destinations, monkeypatch):
    from types import SimpleNamespace

    async def fail_if_called(*_args):
        pytest.fail("A truncated report must not be sent to the model")

    monkeypatch.setattr(
        report_leads,
        "get_llm_config_for_run",
        lambda *_: SimpleNamespace(max_context_tokens=100),
    )
    monkeypatch.setattr(
        report_leads.llm_service,
        "_fit_plain_prompt_to_context",
        lambda config, prompt, system: (config, prompt[:20], {}),
    )
    monkeypatch.setattr(report_leads.llm_service, "plain_completion", fail_if_called)
    url = f"/api/test-runs/{destinations['web']}/import-report"
    response = client.post(url, files={"file": ("notes.txt", b"One long report")})
    assert response.status_code == 422
    assert "context window" in response.json()["detail"]


def test_ai_report_uses_only_quoted_confidence(client, destinations, monkeypatch):
    async def complete(_config, _prompt):
        return json.dumps(
            {
                "total_found": 2,
                "findings": [
                    {
                        "title": "First",
                        "source_quote": "First finding",
                        "confidence": 0.99,
                    },
                    {
                        "title": "Second",
                        "source_quote": "Second finding",
                        "confidence_quote": "80%",
                    },
                ],
            }
        )

    monkeypatch.setattr(report_leads, "get_llm_config_for_run", lambda *_: object())
    monkeypatch.setattr(report_leads.llm_service, "plain_completion", complete)
    url = f"/api/test-runs/{destinations['web']}/import-report"
    result = client.post(
        url,
        files={
            "file": ("notes.txt", b"First finding\nSecond finding\nConfidence: 80%")
        },
    )
    assert result.status_code == 200, result.text
    assert [item["confidence"] for item in result.json()["items"]] == [None, 0.8]


@pytest.mark.parametrize(
    "extension,content",
    [
        ("md", b"## Finding\n- Severity: high\n### Description\nA reported issue."),
        ("sarif", json.dumps(sarif()).encode()),
    ],
)
def test_missing_confidence_is_unknown_but_explicit_zero_is_zero(
    client, destinations, extension, content
):
    url = f"/api/test-runs/{destinations['web']}/import-report"
    preview = client.post(url, files={"file": (f"report.{extension}", content)})
    assert preview.status_code == 200, preview.text
    assert preview.json()["items"][0]["confidence"] is None
    if extension == "md":
        explicit = content.replace(
            b"- Severity: high", b"- Severity: high\n- Confidence: 0%"
        )
        result = client.post(url, files={"file": ("explicit.md", explicit)})
        assert result.json()["items"][0]["confidence"] == 0


@pytest.mark.parametrize(
    "total,findings",
    [
        (101, []),
        (2, [{"title": "One", "source_quote": "One finding"}]),
    ],
)
def test_ai_report_rejects_incomplete_or_oversized_finding_list(
    client, destinations, monkeypatch, total, findings
):
    async def complete(_config, _prompt):
        return json.dumps({"total_found": total, "findings": findings})

    monkeypatch.setattr(report_leads, "get_llm_config_for_run", lambda *_: object())
    monkeypatch.setattr(report_leads.llm_service, "plain_completion", complete)
    url = f"/api/test-runs/{destinations['web']}/import-report"
    result = client.post(url, files={"file": ("notes.txt", b"One finding")})
    assert result.status_code == 422


def test_bad_signed_preview_returns_error(client, destinations):
    import hashlib
    import hmac

    url = f"/api/test-runs/{destinations['web']}/import-report"
    payload = "%%%"
    signature = hmac.new(
        client.app.state.auth.secret.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    result = client.post(
        url,
        files={"file": ("notes.txt", b"One finding")},
        data={"preview": "false", "prepared": f"{payload}.{signature}"},
    )
    assert result.status_code == 422
    assert "Preview it again" in result.json()["detail"]


def test_plain_text_with_json_braces_uses_model(client, destinations, monkeypatch):
    async def complete(_config, _prompt):
        return json.dumps({"total_found": 0, "findings": []})

    monkeypatch.setattr(report_leads, "get_llm_config_for_run", lambda *_: object())
    monkeypatch.setattr(report_leads.llm_service, "plain_completion", complete)
    url = f"/api/test-runs/{destinations['web']}/import-report"
    result = client.post(url, files={"file": ("notes.txt", b'{"note": "report"}')})
    assert result.status_code == 200, result.text
    assert result.json()["format"] == "AI-reviewed report"


@pytest.mark.parametrize(
    "filename,content,findings",
    [
        (
            "scanner.json",
            b'{"runs":[{"id":"scan-1","summary":"One issue"}]}',
            [{"title": "One issue", "source_quote": "One issue"}],
        ),
        (
            "mixed.md",
            b"## First issue\n- Severity: high\n### Description\nFirst detail\n\n## Second issue\nSecond detail",
            [
                {"title": "First issue", "source_quote": "First detail"},
                {"title": "Second issue", "source_quote": "Second detail"},
            ],
        ),
    ],
)
def test_non_sarif_runs_and_mixed_markdown_use_model_without_dropping_findings(
    client, destinations, monkeypatch, filename, content, findings
):
    calls = []

    async def complete(_config, prompt):
        calls.append(prompt)
        return json.dumps({"total_found": len(findings), "findings": findings})

    monkeypatch.setattr(report_leads, "get_llm_config_for_run", lambda *_: object())
    monkeypatch.setattr(report_leads.llm_service, "plain_completion", complete)
    url = f"/api/test-runs/{destinations['web']}/import-report"
    result = client.post(url, files={"file": (filename, content)})
    assert result.status_code == 200, result.text
    assert result.json()["format"] == "AI-reviewed report"
    assert result.json()["total"] == len(findings)
    assert len(calls) == 1
