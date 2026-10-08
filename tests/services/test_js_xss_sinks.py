from __future__ import annotations

import asyncio

import httpx
from sqlmodel import select

from aespa.models import ScanFinding, Site, TargetIntelItem, TestRun
from aespa.services.js_xss_sinks import find_js_xss_sinks
from aespa.services.scanner import _analyse_js_sinks, _build_target_intelligence_context


def test_finds_field_used_in_html_builder_and_ignores_escaped_text() -> None:
    source = """
    function renderRecords(records) {
      var html = '';
      records.forEach(function (record) {
        html += '<p>' + escapeHtml(record.safe_label) + '</p>';
        html += '<p>' + record.message + '</p>';
      });
      panel.innerHTML = html;
    }
    """
    rows = find_js_xss_sinks(source)
    assert ("message", "html") in {(row["field"], row["context"]) for row in rows}
    assert "safe_label" not in {row["field"] for row in rows}


def test_inline_handler_keeps_html_escaped_field_as_a_lead() -> None:
    source = """
    function renderUser(user) {
      var html = '<button onclick="openRecord(\\'' + escapeHtml(user.display_name) + '\\')">Open</button>';
      box.innerHTML = html;
    }
    """
    rows = find_js_xss_sinks(source)
    assert any(
        row["field"] == "display_name" and row["context"] == "event_handler"
        for row in rows
    )


def test_text_content_does_not_create_a_sink() -> None:
    source = "function render(item) { box.textContent = item.comment; }"
    assert find_js_xss_sinks(source) == []


def test_fetched_sink_leads_reach_the_scan_brief(db_session) -> None:
    site = Site(name="sample", base_url="https://example.test")
    db_session.add(site)
    db_session.flush()
    run = TestRun(site_id=site.id, name="sample")
    db_session.add(run)
    db_session.flush()
    script_url = "https://example.test/js/records.js"
    db_session.add(
        TargetIntelItem(
            test_run_id=run.id,
            kind="script",
            key="/js/records.js",
            value=script_url,
            url="https://example.test/records",
            method="GET",
            source="dom_script",
        )
    )
    for index in range(90):
        db_session.add(
            TargetIntelItem(
                test_run_id=run.id,
                kind="input",
                key=f"field_{index}",
                value="",
                source="test",
            )
        )
    db_session.commit()

    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            text="function render(row) { var html = '<p>' + row.comment + '</p>'; panel.innerHTML = html; }",
        )
    )

    async def run_analysis():
        async with httpx.AsyncClient(transport=transport) as client:
            return await _analyse_js_sinks(run.id, client)

    results = asyncio.run(run_analysis())
    assert any(row["field"] == "comment" for row in results)
    saved = db_session.exec(
        select(TargetIntelItem).where(
            TargetIntelItem.test_run_id == run.id,
            TargetIntelItem.kind == "xss_sink",
        )
    ).all()
    assert any(item.key == "comment" for item in saved)
    assert not db_session.exec(
        select(ScanFinding).where(ScanFinding.test_run_id == run.id)
    ).all()
    brief = _build_target_intelligence_context(run.id)
    assert "xss_sink GET comment" in brief
    assert "Seen on: https://example.test/records" in brief
