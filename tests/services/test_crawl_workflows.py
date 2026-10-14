import asyncio
import json
from types import SimpleNamespace

from sqlmodel import Session

from aespa.models import CrawledPage, ScanLog, Site, TestRun
from aespa.services import crawl_workflows, recon_summary, sites


def test_inferred_workflow_must_start_on_an_observed_page(monkeypatch):
    async def fake_completion(_config, _prompt):
        return json.dumps(
            {
                "workflows": [
                    {
                        "name": "Checkout",
                        "start_url": "https://shop.test/product",
                        "goal": "Open checkout",
                        "reason": "The product has an Add to cart button.",
                        "destructive": False,
                    },
                    {
                        "name": "Unknown",
                        "start_url": "https://shop.test/guessed",
                        "goal": "Open an unseen page",
                        "reason": "Guessed URL",
                        "destructive": False,
                    },
                    {
                        "name": "Submit a product review",
                        "start_url": "https://shop.test/product",
                        "goal": "Submit a review",
                        "reason": "The product has a review form.",
                        "destructive": True,
                    },
                ]
            }
        )

    monkeypatch.setattr(crawl_workflows.llm_svc, "plain_completion", fake_completion)
    proposals = asyncio.run(
        crawl_workflows._infer_workflows(
            object(),
            [{"url": "https://shop.test/product"}],
            {"https://shop.test/product"},
        )
    )
    assert [proposal["name"] for proposal in proposals] == [
        "Checkout",
        "Submit a product review",
    ]
    assert proposals[1]["destructive"] is False


def test_state_change_guard_allows_cart_setup_and_payment():
    observation = {
        "url": "https://shop.test/product",
        "controls": [
            {
                "kind": "button",
                "name": "Add to cart",
                "href": "",
                "form": "Qty 1 Add to cart",
            },
            {
                "kind": "button",
                "name": "Continue",
                "href": "",
                "form": "Card number",
            },
            {
                "kind": "link",
                "name": "Checkout",
                "href": "https://shop.test/checkout",
                "form": "",
            },
            {
                "kind": "link",
                "name": "Payment methods",
                "href": "https://shop.test/account/payment-methods",
                "form": "",
            },
        ],
        "fields": [],
    }
    assert crawl_workflows._action_allowed(
        {"action": "click", "index": 0, "risk": "safe"}, observation
    )[0]
    assert crawl_workflows._action_allowed(
        {"action": "click", "index": 1, "risk": "safe"}, observation
    )[0]
    assert crawl_workflows._action_allowed(
        {"action": "click", "index": 2, "risk": "safe"}, observation
    )[0]
    assert crawl_workflows._action_allowed(
        {"action": "click", "index": 3, "risk": "safe"}, observation
    )[0]


def test_save_button_is_not_blocked_by_a_sibling_cancel_button():
    observation = {
        "url": "https://shop.test/account/addresses",
        "controls": [
            {
                "kind": "button",
                "name": "Save address",
                "href": "",
                "form": "Full name Street address Postcode Save address Cancel",
                "formAction": "/account/addresses",
            },
            {
                "kind": "button",
                "name": "Cancel",
                "href": "",
                "form": "Full name Street address Postcode Save address Cancel",
                "formAction": "",
            },
        ],
        "fields": [],
    }
    assert crawl_workflows._action_allowed(
        {"action": "click", "index": 0, "risk": "safe"}, observation
    )[0]
    assert crawl_workflows._action_allowed(
        {"action": "click", "index": 1, "risk": "safe"}, observation
    )[0]


def test_form_action_allows_order_submission():
    observation = {
        "url": "https://shop.test/checkout",
        "controls": [
            {
                "kind": "button",
                "name": "Save details",
                "href": "",
                "form": "Contact details",
                "formAction": "/orders/place-order",
            }
        ],
        "fields": [],
    }
    assert crawl_workflows._action_allowed(
        {"action": "click", "index": 0, "risk": "safe"}, observation
    )[0]


def test_state_change_guard_rejects_ambiguous_controls_but_allows_orders():
    observation = {
        "url": "https://shop.test/checkout",
        "controls": [
            {"kind": "button", "name": "Continue", "href": "", "form": ""},
            {"kind": "button", "name": "Continue", "href": "", "form": ""},
            {"kind": "button", "name": "Confirm order", "href": "", "form": ""},
        ],
        "fields": [],
    }
    assert not crawl_workflows._action_allowed(
        {"action": "click", "index": 0, "risk": "safe"}, observation
    )[0]
    assert crawl_workflows._action_allowed(
        {"action": "click", "index": 2, "risk": "safe"}, observation
    )[0]
    assert crawl_workflows._action_allowed(
        {"action": "click", "index": 2, "risk": "safe"},
        observation,
        generate_sample_data=True,
    )[0]


def test_review_submission_ignores_model_risk_but_delete_actions_are_blocked():
    observation = {
        "url": "https://shop.test/product",
        "controls": [
            {"kind": "button", "name": "Submit review", "form": "Your review"},
            {"kind": "button", "name": "Delete review", "form": "Your review"},
            {"kind": "button", "name": "Continue", "formAction": "/reviews/remove"},
        ],
        "fields": [],
    }
    assert crawl_workflows._action_allowed(
        {"action": "click", "index": 0, "risk": "destructive"}, observation
    )[0]
    for index in (1, 2):
        allowed, reason = crawl_workflows._action_allowed(
            {"action": "click", "index": index, "risk": "safe"}, observation
        )
        assert not allowed
        assert reason == "The next action would delete something."


def test_network_guard_blocks_delete_requests():
    class Route:
        def __init__(self, method, url):
            self.request = SimpleNamespace(method=method, url=url)
            self.action = None

        async def abort(self):
            self.action = "abort"

        async def continue_(self):
            self.action = "continue"

    for method, url, expected in (
        ("DELETE", "https://shop.test/reviews/1", "abort"),
        ("POST", "https://shop.test/reviews/remove/1", "abort"),
        ("POST", "https://shop.test/reviews", "continue"),
    ):
        route = Route(method, url)
        asyncio.run(crawl_workflows._block_delete_request(route))
        assert route.action == expected


def test_fill_requires_an_exact_user_supplied_value():
    observation = {
        "url": "https://shop.test/address",
        "controls": [],
        "fields": [{"fieldName": "street", "fieldId": "", "type": "text"}],
    }
    decision = {
        "action": "fill",
        "index": 0,
        "risk": "safe",
        "value": "1 Example Street",
    }
    assert not crawl_workflows._action_allowed(decision, observation)[0]
    assert crawl_workflows._action_allowed(
        decision, observation, "Use 1 Example Street, Sydney NSW 2000"
    )[0]
    assert not crawl_workflows._action_allowed(
        {**decision, "value": "2 Invented Street"},
        observation,
        "Use 1 Example Street, Sydney NSW 2000",
    )[0]
    assert crawl_workflows._action_allowed(
        {**decision, "value": "2 Test Street"},
        observation,
        generate_sample_data=True,
    )[0]


def test_user_supplied_password_can_be_filled():
    observation = {
        "url": "https://shop.test/account",
        "controls": [],
        "fields": [{"fieldName": "password", "fieldId": "", "type": "password"}],
    }
    decision = {"action": "fill", "index": 0, "value": "example-secret"}
    assert crawl_workflows._action_allowed(
        decision, observation, "Password: example-secret"
    )[0]


def test_generated_values_do_not_fill_payment_or_secret_fields():
    decision = {"action": "fill", "index": 0, "risk": "safe", "value": "test value"}
    for url, field_name in [
        ("https://shop.test/payment-methods", "holder"),
        ("https://shop.test/address", "card_number"),
        ("https://shop.test/address", "security_code"),
    ]:
        allowed, reason = crawl_workflows._action_allowed(
            decision,
            {
                "url": url,
                "controls": [],
                "fields": [
                    {
                        "name": field_name,
                        "fieldName": field_name,
                        "fieldId": "",
                        "type": "text",
                    }
                ],
            },
            generate_sample_data=True,
        )
        assert not allowed
        assert reason == "Payment or secret fields need user-supplied test data."


def test_generated_values_are_ready_to_edit_and_reuse():
    workflow = {"user_instructions": "Use 1 Test Street", "generate_sample_data": True}
    observation = {
        "fields": [
            {"name": "street"},
            {"name": "name"},
            {"name": "postcode"},
        ]
    }
    for decision in [
        {"action": "fill", "index": 0, "value": "1 Test Street"},
        {"action": "fill", "index": 1, "value": "AESPA Test User"},
        {"action": "fill", "index": 1, "value": "AESPA Test User"},
        {"action": "select", "index": 2, "value": "2000"},
    ]:
        crawl_workflows._remember_generated_value(workflow, decision, observation)
    assert len(workflow["generated_values"]) == 2
    assert crawl_workflows._instructions_with_generated_values(workflow) == (
        "Use 1 Test Street\nGenerated test values:\n"
        "name: AESPA Test User\npostcode: 2000"
    )


def test_crawler_model_gets_generation_permission_only_for_requested_retry(monkeypatch):
    prompts = []

    async def fake_completion(_config, prompt):
        prompts.append(prompt)
        return '{"action":"stop","risk":"safe"}'

    monkeypatch.setattr(crawl_workflows.llm_svc, "plain_completion", fake_completion)
    observation = {"url": "https://shop.test/address", "fields": [], "controls": []}
    asyncio.run(
        crawl_workflows._decide_action(
            object(), {"name": "Address", "generate_sample_data": True}, observation, []
        )
    )
    asyncio.run(
        crawl_workflows._decide_action(object(), {"name": "Address"}, observation, [])
    )
    assert "explicitly authorized you to generate" in prompts[0]
    assert "do not invent names" in prompts[1]


def test_saved_site_workflow_data_is_reused_by_later_crawls(isolated_db_engine):
    with Session(isolated_db_engine) as session:
        site = Site(name="Shop", base_url="https://shop.test")
        session.add(site)
        session.commit()
        sites.save_site_workflow_data(
            session,
            site.id,
            {
                "name": "Add a delivery address",
                "goal": "Open the address form",
                "start_url": "https://shop.test/account/addresses",
            },
            "Use 1 Example Street",
        )
        sites.save_site_workflow_data(
            session,
            site.id,
            {
                "name": "Add a delivery address",
                "goal": "Open the address form",
                "start_url": "https://shop.test/account/addresses",
            },
            "Use 2 Example Street",
        )
        session.refresh(site)
        saved = sites.workflow_data_for_site(site)
        proposals = crawl_workflows._saved_workflow_proposals(site)
    assert len(saved) == 1
    assert saved[0]["instructions"] == "Use 2 Example Street"
    assert proposals[0]["user_instructions"] == "Use 2 Example Street"
    assert proposals[0]["saved_site_data"] is True


def test_saved_site_workflows_do_not_leave_the_site():
    site = Site(
        name="Shop",
        base_url="https://shop.test",
        workflow_data_json=json.dumps(
            [
                {
                    "name": "Outside",
                    "goal": "Open another site",
                    "start_url": "https://other.test/checkout",
                    "instructions": "Use test data",
                }
            ]
        ),
    )
    assert crawl_workflows._saved_workflow_proposals(site) == []


def test_retry_checkbox_waits_for_success_before_saving(
    isolated_db_engine, monkeypatch
):
    with Session(isolated_db_engine) as session:
        site = Site(name="Shop", base_url="https://shop.test")
        session.add(site)
        session.flush()
        run = TestRun(site_id=site.id, name="First test")
        session.add(run)
        session.commit()
        site_id, run_id = site.id, run.id

    attempts = []

    async def fake_retry(_run_id, _workflow, *, save_to_site=False):
        attempts.append(
            (
                save_to_site,
                _workflow["generate_sample_data"],
                _workflow["user_instructions"],
            )
        )
        return None

    monkeypatch.setattr(crawl_workflows, "_run_workflow_retry", fake_retry)
    note = {
        "id": 23,
        "name": "Address",
        "goal": "Open address form",
        "start_url": "https://shop.test/account/addresses",
        "needs_input": True,
    }

    async def submit():
        crawl_workflows.start_workflow_retry(
            run_id, note, "Use 1 Example Street", save_to_site=True
        )
        await crawl_workflows._retry_tasks[run_id]

    asyncio.run(submit())
    with Session(isolated_db_engine) as session:
        saved = sites.workflow_data_for_site(session.get(Site, site_id))
    assert saved == []
    assert crawl_workflows.workflow_retry_status(run_id)["saved_to_site"] is False
    assert attempts == [(True, False, "Use 1 Example Street")]

    async def retry_without_input():
        crawl_workflows.start_workflow_retry(run_id, note, "")
        await crawl_workflows._retry_tasks[run_id]

    asyncio.run(retry_without_input())
    assert attempts[-1] == (False, False, "")

    async def generate():
        crawl_workflows.start_workflow_retry(
            run_id, note, "", generate_sample_data=True
        )
        await crawl_workflows._retry_tasks[run_id]

    asyncio.run(generate())
    assert attempts[-1] == (False, True, "")
    crawl_workflows._retry_tasks.pop(run_id, None)
    crawl_workflows._retry_results.pop(run_id, None)


def test_crawl_note_appears_in_attack_surface(isolated_db_engine):
    with Session(isolated_db_engine) as session:
        site = Site(name="Shop", base_url="https://shop.test")
        session.add(site)
        session.flush()
        run = TestRun(site_id=site.id, name="Crawl")
        session.add(run)
        session.flush()
        session.add(
            CrawledPage(
                test_run_id=run.id,
                url="https://shop.test/cart",
                status="crawled",
            )
        )
        note = {
            "name": "Checkout",
            "status": "not_attempted",
            "reason": "The last action appears to place an order.",
            "steps": ["Open cart"],
            "detail": "Not tried because the next action may be destructive.",
        }
        session.add(
            ScanLog(
                test_run_id=run.id,
                run_kind="web",
                phase="crawl_note",
                data_json=json.dumps({"stage": "workflow_note", "note": note}),
            )
        )
        session.commit()
        assert crawl_workflows._prior_workflow_names(run.id) == {"checkout"}
        summary = recon_summary.build_recon_summary(run.id, session=session)

    assert len(summary["crawl_notes"]) == 1
    assert {key: summary["crawl_notes"][0][key] for key in note} == note
    assert summary["crawl_notes"][0]["needs_input"] is False


def test_legacy_missing_data_note_can_be_continued_and_success_clears_it(
    isolated_db_engine,
):
    with Session(isolated_db_engine) as session:
        site = Site(name="Shop", base_url="https://shop.test")
        session.add(site)
        session.flush()
        run = TestRun(site_id=site.id, name="Crawl")
        session.add(run)
        session.flush()
        old_note = ScanLog(
            test_run_id=run.id,
            run_kind="web",
            phase="crawl_note",
            data_json=json.dumps(
                {
                    "note": {
                        "name": "Add a delivery address",
                        "status": "not_attempted",
                        "detail": "No sample address was provided.",
                        "url": "https://shop.test/account/addresses",
                    }
                }
            ),
        )
        session.add(old_note)
        session.flush()
        notes = crawl_workflows.list_workflow_notes(session, run.id)
        assert notes[0]["needs_input"] is True
        session.add(
            ScanLog(
                test_run_id=run.id,
                run_kind="web",
                phase="crawl_note",
                data_json=json.dumps(
                    {
                        "note": {
                            "name": "Add a delivery address",
                            "status": "crawled",
                            "retry_of": old_note.id,
                            "detail": "Reached the workflow with user-provided instructions.",
                        }
                    }
                ),
            )
        )
        session.flush()
        notes = crawl_workflows.list_workflow_notes(session, run.id)
        assert notes[0]["needs_input"] is False
        assert notes[0]["resolved"] is True


def test_retry_replaces_notification_even_when_workflow_is_not_reached(
    isolated_db_engine,
):
    with Session(isolated_db_engine) as session:
        site = Site(name="Shop", base_url="https://shop.test")
        session.add(site)
        session.flush()
        run = TestRun(site_id=site.id, name="Crawl")
        session.add(run)
        session.flush()
        original = ScanLog(
            test_run_id=run.id,
            run_kind="web",
            phase="crawl_note",
            data_json=json.dumps(
                {
                    "note": {
                        "name": "Checkout",
                        "status": "needs_input",
                        "needs_input": True,
                    }
                }
            ),
        )
        session.add(original)
        session.flush()
        session.add(
            ScanLog(
                test_run_id=run.id,
                run_kind="web",
                phase="crawl_note",
                data_json=json.dumps(
                    {
                        "note": {
                            "name": "Checkout",
                            "status": "not_reached",
                            "needs_input": False,
                            "retry_of": original.id,
                        }
                    }
                ),
            )
        )
        session.flush()
        notes = crawl_workflows.list_workflow_notes(session, run.id)
        assert notes[0]["needs_input"] is False
        assert notes[1]["needs_input"] is False
        session.add(
            ScanLog(
                test_run_id=run.id,
                run_kind="web",
                phase="crawl_note",
                data_json=json.dumps(
                    {
                        "note": {
                            "name": "Checkout",
                            "status": "needs_input",
                            "needs_input": True,
                            "retry_of": notes[1]["id"],
                        }
                    }
                ),
            )
        )
        session.flush()
        notes = crawl_workflows.list_workflow_notes(session, run.id)
        assert [note["needs_input"] for note in notes] == [False, False, True]


def test_workflow_retry_api_accepts_unfinished_notes_but_not_destructive_or_old_notes(
    isolated_client, isolated_db_engine, monkeypatch
):
    with Session(isolated_db_engine) as session:
        site = Site(name="Shop", base_url="https://shop.test")
        session.add(site)
        session.flush()
        run = TestRun(site_id=site.id, name="Crawl")
        session.add(run)
        session.flush()
        for name, status, detail in [
            ("Address", "not_attempted", "No sample address was provided."),
            (
                "Ship order",
                "not_attempted",
                "Not tried because this workflow appears destructive.",
            ),
            ("Checkout", "not_reached", "The page did not load."),
            ("Done", "crawled", "Reached the workflow."),
        ]:
            session.add(
                ScanLog(
                    test_run_id=run.id,
                    run_kind="web",
                    phase="crawl_note",
                    data_json=json.dumps(
                        {
                            "note": {
                                "name": name,
                                "status": status,
                                "detail": detail,
                                "url": "https://shop.test/account",
                            }
                        }
                    ),
                )
            )
        session.commit()
        run_id = run.id

    notes = isolated_client.get(f"/api/test-runs/{run_id}/crawl/workflows").json()[
        "notes"
    ]
    assert [note["needs_input"] for note in notes] == [True, False, False, False]
    assert [note["retryable"] for note in notes] == [True, False, True, False]
    captured = {}

    def fake_start(
        _run_id, note, instructions, *, save_to_site=False, generate_sample_data=False
    ):
        captured.update(
            run_id=_run_id,
            note_id=note["id"],
            instructions=instructions,
            save_to_site=save_to_site,
            generate_sample_data=generate_sample_data,
        )
        return {"status": "running", "note_id": note["id"]}

    monkeypatch.setattr(crawl_workflows, "start_workflow_retry", fake_start)
    blocked = isolated_client.post(
        f"/api/test-runs/{run_id}/crawl/workflows/{notes[1]['id']}/retry",
        json={"instructions": "Ship it"},
    )
    assert blocked.status_code == 409
    blocked_done = isolated_client.post(
        f"/api/test-runs/{run_id}/crawl/workflows/{notes[3]['id']}/retry",
        json={"instructions": ""},
    )
    assert blocked_done.status_code == 409
    retry_unfinished = isolated_client.post(
        f"/api/test-runs/{run_id}/crawl/workflows/{notes[2]['id']}/retry",
        json={"instructions": ""},
    )
    assert retry_unfinished.status_code == 200
    assert captured["note_id"] == notes[2]["id"]
    assert captured["instructions"] == ""
    accepted = isolated_client.post(
        f"/api/test-runs/{run_id}/crawl/workflows/{notes[0]['id']}/retry",
        json={"instructions": "Use 1 Example Street", "save_to_site": True},
    )
    assert accepted.status_code == 200
    assert captured == {
        "run_id": run_id,
        "note_id": notes[0]["id"],
        "instructions": "Use 1 Example Street",
        "save_to_site": True,
        "generate_sample_data": False,
    }
    generated = isolated_client.post(
        f"/api/test-runs/{run_id}/crawl/workflows/{notes[0]['id']}/retry",
        json={"instructions": "", "generate_sample_data": True},
    )
    assert generated.status_code == 200
    assert captured["instructions"] == ""
    assert captured["generate_sample_data"] is True


def test_retry_runner_saves_only_reached_workflows(isolated_db_engine, monkeypatch):
    from aespa.services import settings

    with Session(isolated_db_engine) as session:
        site = Site(name="Shop", base_url="https://shop.test")
        session.add(site)
        session.flush()
        run = TestRun(site_id=site.id, name="Crawl", max_pages=25)
        session.add(run)
        session.flush()
        session.add(
            CrawledPage(
                test_run_id=run.id,
                url="https://shop.test/account/addresses",
                status="crawled",
            )
        )
        session.commit()
        run_id = run.id
        site_id = site.id

    monkeypatch.setattr(settings, "get_llm_config_for_role", lambda *_: object())
    monkeypatch.setattr(
        settings,
        "get_upstream_proxy_config",
        lambda *_: SimpleNamespace(proxy_scanner=False),
    )
    monkeypatch.setattr(
        settings,
        "get_browser_debug_config",
        lambda *_: SimpleNamespace(browser_engine="chromium", browser_visible=False),
    )
    monkeypatch.setattr(
        settings,
        "get_global_http_header_config",
        lambda *_: SimpleNamespace(headers=[]),
    )
    captured = {}

    result = {"status": "needs_input"}

    async def fake_explore(run_id, **kwargs):
        captured.update(run_id=run_id, **kwargs)
        kwargs["progress"](
            {
                "stage": "checking_page",
                "message": "Checking the result",
                "current_path": "/account/addresses",
                "actions_done": 1,
                "actions": ["click Add an address"],
            }
        )
        kwargs["progress"](
            {
                "stage": "finished",
                "message": "A full name is needed.",
                "result_status": result["status"],
            }
        )

    monkeypatch.setattr(crawl_workflows, "explore_after_crawl", fake_explore)
    workflow = {
        "name": "Add a delivery address",
        "goal": "Save an address",
        "reason": "Address form observed",
        "start_url": "https://shop.test/account/addresses",
        "retry_of": 123,
        "user_instructions": "Use 1 Example Street",
    }
    crawl_workflows._retry_results[run_id] = {"saved_to_site": False}
    asyncio.run(
        crawl_workflows._run_workflow_retry(run_id, workflow, save_to_site=True)
    )
    assert captured["run_id"] == run_id
    assert captured["max_pages"] == 25
    assert captured["selected_workflows"] == [workflow]
    status = crawl_workflows.workflow_retry_status(run_id)
    assert status["status"] == "complete"
    assert status["note_id"] == 123
    assert status["result_status"] == "needs_input"
    assert status["actions"] == ["click Add an address"]
    assert status["saved_to_site"] is False
    with Session(isolated_db_engine) as session:
        assert sites.workflow_data_for_site(session.get(Site, site_id)) == []

    async def failed_explore(_run_id, **_kwargs):
        raise RuntimeError("Browser closed")

    monkeypatch.setattr(crawl_workflows, "explore_after_crawl", failed_explore)
    crawl_workflows._retry_results[run_id] = {"saved_to_site": False}
    asyncio.run(
        crawl_workflows._run_workflow_retry(run_id, workflow, save_to_site=True)
    )
    assert crawl_workflows.workflow_retry_status(run_id)["status"] == "error"
    with Session(isolated_db_engine) as session:
        assert sites.workflow_data_for_site(session.get(Site, site_id)) == []
        notes = crawl_workflows.list_workflow_notes(session, run_id)
    assert notes[-1]["instructions"] == "Use 1 Example Street"
    assert notes[-1]["needs_input"] is True

    monkeypatch.setattr(crawl_workflows, "explore_after_crawl", fake_explore)
    result["status"] = "crawled"
    workflow["generate_sample_data"] = True
    workflow["generated_values"] = [{"field": "full_name", "value": "AESPA Test User"}]
    crawl_workflows._retry_results[run_id] = {"saved_to_site": False}
    asyncio.run(
        crawl_workflows._run_workflow_retry(run_id, workflow, save_to_site=True)
    )
    assert crawl_workflows.workflow_retry_status(run_id)["saved_to_site"] is True
    with Session(isolated_db_engine) as session:
        saved = sites.workflow_data_for_site(session.get(Site, site_id))
    assert saved[0]["instructions"] == (
        "Use 1 Example Street\nGenerated test values:\nfull_name: AESPA Test User"
    )
    crawl_workflows._retry_results.pop(run_id, None)


def test_retry_note_keeps_specific_request_and_instructions(isolated_db_engine):
    with Session(isolated_db_engine) as session:
        site = Site(name="Shop", base_url="https://shop.test")
        session.add(site)
        session.flush()
        run = TestRun(site_id=site.id, name="Crawl")
        session.add(run)
        session.commit()
        run_id = run.id
    crawl_workflows._record_note(
        run_id,
        {
            "name": "Address",
            "goal": "Save an address",
            "reason": "Address form observed",
            "start_url": "https://shop.test/account/addresses",
            "retry_of": 123,
        },
        "needs_input",
        ["click Add an address"],
        "The address form requires a full name, but none was provided.",
        needs_input=True,
        request="Please provide the full name for this delivery address.",
        instructions="1 Example Street, Sydney NSW 2000",
    )
    with Session(isolated_db_engine) as session:
        note = crawl_workflows.list_workflow_notes(session, run_id)[0]
    assert note["request"] == "Please provide the full name for this delivery address."
    assert note["instructions"] == "1 Example Street, Sydney NSW 2000"


def test_invalid_supplied_form_value_requests_a_correction():
    assert (
        crawl_workflows._invalid_supplied_input(
            {
                "validation_errors": [
                    {
                        "field": "Postal code",
                        "message": "Enter a valid postal code.",
                        "has_value": True,
                    }
                ]
            }
        )
        == "Check the Postal code value: Enter a valid postal code."
    )
    assert not crawl_workflows._invalid_supplied_input(
        {"validation_errors": [{"field": "Name", "has_value": False}]}
    )
    assert (
        crawl_workflows._invalid_supplied_input(
            {"form_errors": ["This address is not valid."]}
        )
        == "Check the form data: This address is not valid."
    )
