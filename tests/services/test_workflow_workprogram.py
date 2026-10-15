from __future__ import annotations

import json

import pytest
from sqlmodel import select

from aespa.models import CrawledPage, ScanLog, Site, TestRun, TrafficEntry
from aespa.services.web_workprogram import (
    _build_web_enforce_directive,
    get_web_coverage_gaps,
)
from aespa.services.workflow_workprogram import (
    list_workflow_tests,
    record_workflow_test,
    remaining_workflow_tests,
    seed_workflow_tests,
)


def _run(db_session) -> TestRun:
    site = Site(name="Workflow target", base_url="https://target.local")
    db_session.add(site)
    db_session.commit()
    run = TestRun(site_id=site.id, name="Workflow run")
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    return run


def _page(
    db_session,
    run_id: int,
    *,
    access: bool = False,
    state_kind: str = "interactive",
    url: str = "https://target.local/orders",
    steps: list[dict] | None = None,
    business_logic: bool = False,
) -> CrawledPage:
    page = CrawledPage(
        test_run_id=run_id,
        url=url,
        replay_steps_json=json.dumps({"root_url": url, "steps": steps or []}),
        has_business_logic=business_logic,
        in_scope=True,
        state_kind=state_kind,
        state_key=f"state-{access}-{db_session.exec(select(CrawledPage.id)).all()}",
        req_auth=access,
        has_object_ref=access,
    )
    db_session.add(page)
    db_session.commit()
    db_session.refresh(page)
    return page


def _note(db_session, run_id: int, page: CrawledPage, name: str, retry_of=None):
    note = ScanLog(
        test_run_id=run_id,
        run_kind="web",
        phase="crawl_note",
        data_json=json.dumps(
            {
                "note": {
                    "name": name,
                    "goal": f"Finish {name}",
                    "status": "crawled",
                    "page_id": page.id,
                    "url": page.url,
                    "retry_of": retry_of,
                }
            }
        ),
    )
    db_session.add(note)
    db_session.commit()
    db_session.refresh(note)
    return note


def test_same_url_workflows_have_separate_checks_and_retry_keeps_result(db_session):
    run = _run(db_session)
    first_page = _page(db_session, run.id, access=True)
    second_page = _page(db_session, run.id)
    first_note = _note(db_session, run.id, first_page, "Place order")
    _note(db_session, run.id, second_page, "Write review")

    assert seed_workflow_tests(run.id) == 3
    assert seed_workflow_tests(run.id) == 0
    items = list_workflow_tests(run.id)["items"]
    assert [(item["name"], item["test_kind"]) for item in items] == [
        ("Place order", "sequence"),
        ("Place order", "access"),
        ("Write review", "sequence"),
    ]
    traffic = TrafficEntry(
        test_run_id=run.id,
        source="httpx",
        method="POST",
        url=first_page.url,
        owasp_category="A04",
    )
    db_session.add(traffic)
    db_session.commit()
    db_session.refresh(traffic)
    record_workflow_test(
        run.id,
        items[0]["id"],
        status="passed",
        attempted_sequence=["Create an order", "Try to repeat confirmation"],
        expected_behavior="The second confirmation is rejected",
        observed_behavior="The server returned 409",
        evidence_traffic_ids=[traffic.id],
    )
    _note(db_session, run.id, first_page, "Place order", retry_of=first_note.id)
    assert seed_workflow_tests(run.id) == 0
    assert list_workflow_tests(run.id)["items"][0]["status"] == "passed"
    assert len(remaining_workflow_tests(run.id)) == 2
    gaps = get_web_coverage_gaps(run.id)
    assert gaps["workflow_remaining"] == 2
    assert {item["item_id"] for item in gaps["workflow_actions"]} == {
        items[1]["id"],
        items[2]["id"],
    }
    directive = _build_web_enforce_directive(run.id)
    assert "Workflow checks still to cover" in directive
    assert "Place order" in directive
    assert "Write review" in directive


def test_workflow_result_requires_scan_evidence_or_block_reason(db_session):
    run = _run(db_session)
    page = _page(db_session, run.id)
    _note(db_session, run.id, page, "Place order")
    crawl_traffic = TrafficEntry(
        test_run_id=run.id,
        source="playwright",
        method="POST",
        url=page.url,
    )
    db_session.add(crawl_traffic)
    db_session.commit()
    seed_workflow_tests(run.id)
    item_id = list_workflow_tests(run.id)["items"][0]["id"]
    with pytest.raises(ValueError, match="traffic from this scan"):
        record_workflow_test(
            run.id,
            item_id,
            status="passed",
            attempted_sequence=["Try order again"],
            expected_behavior="Rejected",
            observed_behavior="Rejected",
            evidence_traffic_ids=[crawl_traffic.id],
        )
    with pytest.raises(ValueError, match="specific reason"):
        record_workflow_test(
            run.id,
            item_id,
            status="blocked",
            attempted_sequence=[],
            expected_behavior="",
            observed_behavior="",
            evidence_traffic_ids=[],
        )
    result = record_workflow_test(
        run.id,
        item_id,
        status="blocked",
        attempted_sequence=[],
        expected_behavior="",
        observed_behavior="",
        evidence_traffic_ids=[],
        blocked_reason="Replaying this recipe would place another order",
    )
    assert result["status"] == "blocked"
    assert list_workflow_tests(run.id)["totals"]["passed"] == 0
    assert remaining_workflow_tests(run.id) == []


def test_older_successful_workflow_can_use_a_unique_api_page(db_session):
    run = _run(db_session)
    page = _page(db_session, run.id, state_kind="api")
    note = _note(db_session, run.id, page, "Submit order")
    data = json.loads(note.data_json)
    data["note"].pop("page_id")
    note.data_json = json.dumps(data)
    db_session.add(note)
    db_session.commit()

    assert seed_workflow_tests(run.id) == 1
    assert list_workflow_tests(run.id)["items"][0]["reached_page_id"] == page.id


def _kinds(run_id: int, name: str) -> dict[str, str]:
    return {
        item["test_kind"]: item["owasp_category"]
        for item in list_workflow_tests(run_id)["items"]
        if item["name"] == name
    }


def test_workflow_checks_follow_what_the_workflow_does(db_session):
    run = _run(db_session)
    browse = _page(
        db_session,
        run.id,
        url="https://target.local/catalog",
        steps=[{"kind": "click", "role": "link", "name": "Laptops"}],
    )
    cart = _page(
        db_session,
        run.id,
        url="https://target.local/cart",
        steps=[{"kind": "fill", "selector": '[name="itemQty"]', "value": "2"}],
    )
    card = _page(
        db_session,
        run.id,
        access=True,
        url="https://target.local/account/payment-methods",
        steps=[{"kind": "fill", "selector": '[name="postcode"]', "value": "2000"}],
    )
    discard = _page(
        db_session,
        run.id,
        access=True,
        url="https://target.local/drafts",
        steps=[{"kind": "fill", "selector": '[name="accountNote"]', "value": "hi"}],
    )
    _note(db_session, run.id, browse, "Browse laptops")
    _note(db_session, run.id, cart, "Add to cart")
    _note(db_session, run.id, card, "Add a payment card")
    _note(db_session, run.id, discard, "Discard a draft")

    seed_workflow_tests(run.id)

    assert _kinds(run.id, "Browse laptops") == {"sequence": "A04"}
    assert _kinds(run.id, "Add to cart") == {
        "sequence": "A04",
        "replay": "A04",
        "tampering": "A08",
    }
    # A numeric postcode is not a value the server should recalculate.
    assert _kinds(run.id, "Add a payment card") == {
        "sequence": "A04",
        "access": "A01",
        "replay": "A04",
        "csrf": "A01",
        "reauth": "A07",
    }
    # "accountNote" and "Discard" do not match the tampering or sensitive words.
    assert _kinds(run.id, "Discard a draft") == {
        "sequence": "A04",
        "access": "A01",
        "replay": "A04",
        "csrf": "A01",
    }
    item = next(
        item
        for item in list_workflow_tests(run.id)["items"]
        if item["test_kind"] == "tampering"
    )
    assert "amounts, quantities, prices" in item["test_guidance"]
    gaps = get_web_coverage_gaps(run.id, limit=50)
    assert {action["test_kind"] for action in gaps["workflow_actions"]} >= {
        "replay",
        "tampering",
        "csrf",
        "reauth",
    }
    assert "anti-CSRF token" in _build_web_enforce_directive(run.id)


def test_sensitive_signed_in_workflow_gets_every_check_except_tampering(db_session):
    run = _run(db_session)
    page = _page(
        db_session,
        run.id,
        access=True,
        url="https://target.local/account/password",
        business_logic=True,
    )
    _note(db_session, run.id, page, "Change password")

    assert seed_workflow_tests(run.id) == 5
    assert seed_workflow_tests(run.id) == 0
    assert set(_kinds(run.id, "Change password")) == {
        "sequence",
        "access",
        "replay",
        "csrf",
        "reauth",
    }
