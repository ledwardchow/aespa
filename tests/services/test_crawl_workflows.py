import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel, select

from aespa.models import (
    CrawledPage,
    Credential,
    DiscoveredTarget,
    PageCredentialView,
    ScanLog,
    Site,
    TargetAccessObservation,
    TestRun,
)
from aespa.services import crawl_workflows, recon_summary, sites, workflow_targets


def test_grouped_workflows_reserve_distinct_exact_items_and_reuse_on_retry(
    isolated_db_engine,
):
    urls = [f"https://shop.test/admin/products/{number}" for number in range(1, 4)]
    with Session(isolated_db_engine) as session:
        site = Site(name="Shop", base_url="https://shop.test")
        session.add(site)
        session.flush()
        run = TestRun(
            site_id=site.id,
            name="Grouped crawl",
            route_groups_json=json.dumps(
                [
                    {
                        "route_pattern": "/admin/products/{value}",
                        "example_urls": [urls[0]],
                    }
                ]
            ),
        )
        session.add(run)
        session.flush()
        for url in urls:
            session.add(
                DiscoveredTarget(
                    test_run_id=run.id,
                    url=url,
                    route_pattern="/admin/products/{value}",
                )
            )
        session.flush()
        targets = list(session.exec(select(DiscoveredTarget)))
        session.add(
            TargetAccessObservation(
                test_run_id=run.id,
                target_id=targets[2].id,
                actor_key="credential:7",
                source_kind="page",
                source_id=1,
                result="reached",
            )
        )
        session.commit()
        run_id = run.id

    edit = workflow_targets.reserve_workflow_target(
        run_id, "crawl:edit", urls[1], actor_key="credential:7"
    )
    delete = workflow_targets.reserve_workflow_target(
        run_id, "crawl:delete", urls[1], actor_key="credential:7"
    )
    assert edit["target_url"] == urls[2]
    assert delete["target_url"] == urls[1]
    assert edit["route_pattern"] == "/admin/products/{value}"
    assert workflow_targets.get_workflow_target(run_id, "crawl:edit") == edit
    assert (
        workflow_targets.reserve_workflow_target(run_id, "crawl:edit", urls[1]) == edit
    )
    assert (
        workflow_targets.reserve_workflow_target(
            run_id, "crawl:edit", urls[1], exclude_urls={edit["target_url"]}
        )
        == edit
    )
    assert (
        workflow_targets.reserve_workflow_target(
            run_id, "crawl:third", urls[1], preferred_url=urls[0]
        )["target_url"]
        == urls[0]
    )
    assert (
        workflow_targets.reserve_workflow_target(run_id, "crawl:fourth", urls[1])
        is None
    )
    assert (
        workflow_targets.reserve_workflow_target(
            run_id,
            "crawl:unknown",
            urls[1],
            preferred_url="https://shop.test/admin/products/99",
        )
        is None
    )


def test_grouped_workflow_rejects_unconfirmed_and_unknown_item(isolated_db_engine):
    with Session(isolated_db_engine) as session:
        site = Site(name="Shop", base_url="https://shop.test")
        session.add(site)
        session.flush()
        run = TestRun(site_id=site.id, name="Crawl", route_groups_json="[]")
        session.add(run)
        session.flush()
        session.add(
            DiscoveredTarget(
                test_run_id=run.id,
                url="https://shop.test/admin/products/1",
                route_pattern="/admin/products/{value}",
            )
        )
        session.commit()
        run_id = run.id
    assert (
        workflow_targets.reserve_workflow_target(
            run_id, "edit", "https://shop.test/admin/products/1"
        )
        is None
    )
    with Session(isolated_db_engine) as session:
        run = session.get(TestRun, run_id)
        run.route_groups_json = json.dumps(
            [{"route_pattern": "/admin/products/{value}", "example_urls": []}]
        )
        session.commit()
    assert (
        workflow_targets.reserve_workflow_target(
            run_id, "edit", "https://shop.test/admin/products/99"
        )
        is None
    )


def test_retry_accepts_discovered_group_example_and_uses_group_page_account(
    isolated_db_engine, monkeypatch
):
    import playwright.async_api

    example_url = "https://shop.test/admin/orders/317"
    crawled_url = "https://shop.test/admin/orders/318"
    with Session(isolated_db_engine) as session:
        site = Site(name="Orders", base_url="https://shop.test")
        session.add(site)
        session.flush()
        first = Credential(site_id=site.id, username="first", password="saved")
        second = Credential(site_id=site.id, username="second", password="saved")
        session.add_all([first, second])
        session.flush()
        run = TestRun(
            site_id=site.id,
            name="Orders crawl",
            route_groups_json=json.dumps(
                [{"route_pattern": "/admin/orders/{value}", "links_seen": 2}]
            ),
        )
        session.add(run)
        session.flush()
        session.add(
            CrawledPage(
                test_run_id=run.id,
                url=crawled_url,
                accessible_by=json.dumps([second.id]),
                req_auth=True,
            )
        )
        for url in (example_url, crawled_url):
            session.add(
                DiscoveredTarget(
                    test_run_id=run.id,
                    url=url,
                    route_pattern="/admin/orders/{value}",
                )
            )
        session.commit()
        run_id = run.id
        session.refresh(first)
        session.refresh(second)
        session.expunge(first)
        session.expunge(second)
        creds = [first, second]
        second_id = second.id

    claim_actors = []

    def reserve(_run_id, _owner, _example, *, actor_key, **_kwargs):
        claim_actors.append(actor_key)
        return {
            "target_url": example_url,
            "route_pattern": "/admin/orders/{value}",
            "example_url": example_url,
        }

    class Browser:
        async def new_context(self, **_kwargs):
            raise RuntimeError("browser reached")

        async def close(self):
            pass

    class Playwright:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            pass

    async def launch(*_args, **_kwargs):
        return Browser()

    monkeypatch.setattr(playwright.async_api, "async_playwright", Playwright)
    monkeypatch.setattr(crawl_workflows, "launch_playwright_browser", launch)
    monkeypatch.setattr(workflow_targets, "reserve_workflow_target", reserve)
    workflow = {
        "name": "Mark an order as shipped",
        "goal": "Mark an order as shipped",
        "start_url": example_url,
        "example_url": example_url,
        "destructive": False,
    }
    with pytest.raises(RuntimeError, match="browser reached"):
        asyncio.run(
            crawl_workflows.explore_after_crawl(
                run_id,
                llm_cfg=None,
                site=SimpleNamespace(base_url="https://shop.test", login_url=""),
                creds=creds,
                shared=None,
                max_pages=10,
                browser_engine="chromium",
                browser_visible=False,
                pw_proxy={},
                global_http_header={},
                selected_workflows=[workflow],
            )
        )
    assert claim_actors == [crawl_workflows.actor_key(second_id)]


def test_shipping_workflow_skips_shipped_example_for_processing_order(
    isolated_db_engine, monkeypatch
):
    import playwright.async_api

    from aespa.services import crawler

    shipped_url = "https://shop.test/admin/orders/1"
    processing_url = "https://shop.test/admin/orders/2"
    pattern = "/admin/orders/{value}"
    with Session(isolated_db_engine) as session:
        site = Site(name="Orders", base_url="https://shop.test")
        session.add(site)
        session.flush()
        run = TestRun(
            site_id=site.id,
            name="Orders crawl",
            route_groups_json=json.dumps([{"route_pattern": pattern, "links_seen": 2}]),
        )
        session.add(run)
        session.flush()
        session.add(CrawledPage(test_run_id=run.id, url=shipped_url))
        for url in (shipped_url, processing_url):
            session.add(
                DiscoveredTarget(test_run_id=run.id, url=url, route_pattern=pattern)
            )
        session.commit()
        run_id = run.id

    visits = []
    decisions = []
    notes = []

    class Page:
        url = "about:blank"

        async def goto(self, url, **_kwargs):
            self.url = url
            visits.append(url)
            return SimpleNamespace(status=200)

    class Context:
        async def route(self, *_args):
            pass

        async def new_page(self):
            return Page()

        async def close(self):
            pass

    class Browser:
        async def new_context(self, **_kwargs):
            return Context()

        async def close(self):
            pass

    class Playwright:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            pass

    async def launch(*_args, **_kwargs):
        return Browser()

    async def observe(page):
        return {
            "url": page.url,
            "title": "Order",
            "text": "Shipped" if page.url == shipped_url else "Processing",
            "controls": [
                {
                    "name": (
                        "Update tracking"
                        if page.url == shipped_url
                        else "Mark as shipped"
                    )
                }
            ],
            "fields": [{"name": "tracking"}],
        }

    async def decide(_llm_cfg, _workflow, observation, *_args):
        decisions.append(observation["url"])
        return {"action": "stop", "reason": "End test"}

    async def no_wait(*_args, **_kwargs):
        pass

    monkeypatch.setattr(playwright.async_api, "async_playwright", Playwright)
    monkeypatch.setattr(crawl_workflows, "launch_playwright_browser", launch)
    monkeypatch.setattr(crawl_workflows, "playwright_user_agent", lambda _b: "test")
    monkeypatch.setattr(crawl_workflows, "protect_playwright_context", lambda *_a: None)
    monkeypatch.setattr(
        crawl_workflows.traffic_svc, "setup_playwright_logging", lambda *_a, **_k: None
    )
    monkeypatch.setattr(crawler, "_wait_for_content_settle", no_wait)
    monkeypatch.setattr(crawl_workflows, "_observe", observe)
    monkeypatch.setattr(crawl_workflows, "_decide_with_corrections", decide)
    monkeypatch.setattr(
        crawl_workflows,
        "_record_note",
        lambda _run_id, workflow, status, *_args, **_kwargs: notes.append(
            (workflow["target_url"], status)
        ),
    )
    workflow = {
        "name": "Mark an order as shipped",
        "goal": "Update an order's shipping status by selecting a carrier and tracking number",
        "start_url": shipped_url,
        "example_url": shipped_url,
        "destructive": False,
    }
    asyncio.run(
        crawl_workflows.explore_after_crawl(
            run_id,
            llm_cfg=None,
            site=SimpleNamespace(base_url="https://shop.test", login_url=""),
            creds=[],
            shared=None,
            max_pages=10,
            browser_engine="chromium",
            browser_visible=False,
            pw_proxy={},
            global_http_header={},
            selected_workflows=[workflow],
        )
    )
    assert visits == [shipped_url, processing_url]
    assert decisions == [processing_url]
    assert workflow["excluded_target_urls"] == [shipped_url]
    assert notes == [(processing_url, "not_reached")]


def test_parallel_workflows_claim_different_items(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'workflow-targets.db'}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(workflow_targets, "get_engine", lambda: engine)
    urls = [f"https://shop.test/products/{number}" for number in range(2)]
    try:
        with Session(engine) as session:
            site = Site(name="Shop", base_url="https://shop.test")
            session.add(site)
            session.flush()
            run = TestRun(
                site_id=site.id,
                name="Parallel workflows",
                route_groups_json=json.dumps(
                    [{"route_pattern": "/products/{value}", "links_seen": 2}]
                ),
            )
            session.add(run)
            session.flush()
            for url in urls:
                session.add(
                    DiscoveredTarget(
                        test_run_id=run.id,
                        url=url,
                        route_pattern="/products/{value}",
                    )
                )
            session.commit()
            run_id = run.id

        def claim(owner):
            return workflow_targets.reserve_workflow_target(run_id, owner, urls[0])

        with ThreadPoolExecutor(max_workers=2) as pool:
            first, second = pool.map(claim, ("edit", "delete"))
        assert {first["target_url"], second["target_url"]} == set(urls)
    finally:
        engine.dispose()


def _retry_state(run_id: int, note_id: int) -> dict:
    status = crawl_workflows.workflow_retry_status(run_id)
    return next(item for item in status["retries"] if item["note_id"] == note_id)


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
    assert [item["generate_sample_data"] for item in proposals] == [True, True]


def test_inference_asks_for_actions_instead_of_generic_pages(monkeypatch):
    prompts = []

    async def completion(_config, prompt):
        prompts.append(prompt)
        return '{"workflows":[]}'

    monkeypatch.setattr(crawl_workflows.llm_svc, "plain_completion", completion)
    assert (
        asyncio.run(
            crawl_workflows._infer_workflows(
                object(),
                [{"url": "https://shop.test/admin"}],
                {"https://shop.test/admin"},
            )
        )
        == []
    )
    assert "specific goal" in prompts[0]
    assert "Do not list ordinary pages, page titles" in prompts[0]
    assert "Include each distinct reached function" not in prompts[0]


def test_grouped_inference_names_one_workflow_for_several_items(monkeypatch):
    urls = [f"https://shop.test/admin/products/{number}" for number in (1, 2)]

    async def completion(_config, prompt):
        assert "grouped_route" in prompt
        return json.dumps(
            {
                "workflows": [
                    {
                        "name": "Edit a product",
                        "start_url": url,
                        "goal": "Save product changes",
                        "reason": "The page shows an edit action",
                    }
                    for url in urls
                ]
            }
        )

    monkeypatch.setattr(crawl_workflows.llm_svc, "plain_completion", completion)
    proposals = asyncio.run(
        crawl_workflows._infer_workflows(
            object(),
            [{"url": url, "grouped_route": "/admin/products/{value}"} for url in urls],
            set(urls),
        )
    )
    assert len(proposals) == 1
    assert proposals[0]["route_pattern"] == "/admin/products/{value}"


def test_inference_keeps_distinct_reached_states_and_validates_page_ids(monkeypatch):
    async def fake_completion(_config, _prompt):
        return json.dumps(
            {
                "workflows": [
                    {
                        "name": "Checkout",
                        "start_url": "https://shop.test/app",
                        "goal": "Open checkout",
                        "reason": "Observed form",
                        "reached_page_id": 11,
                    },
                    {
                        "name": "Checkout",
                        "start_url": "https://shop.test/app",
                        "goal": "Review order",
                        "reason": "Observed state",
                        "reached_page_id": 12,
                    },
                    {
                        "name": "Unknown",
                        "start_url": "https://shop.test/app",
                        "goal": "Unknown",
                        "reason": "Invalid page",
                        "reached_page_id": 99,
                    },
                ]
            }
        )

    monkeypatch.setattr(crawl_workflows.llm_svc, "plain_completion", fake_completion)
    proposals = asyncio.run(
        crawl_workflows._infer_workflows(
            object(),
            [
                {"page_id": 11, "url": "https://shop.test/app"},
                {"page_id": 12, "url": "https://shop.test/app"},
            ],
            {"https://shop.test/app"},
        )
    )
    assert [proposal["reached_page_id"] for proposal in proposals] == [11, 12]


def test_inference_keeps_different_goals_with_the_same_name_and_start(monkeypatch):
    workflows = [
        {
            "name": "Account settings",
            "start_url": "https://shop.test/account",
            "goal": goal,
            "reason": "The account page offers this action",
        }
        for goal in ("Change email", "Change password")
    ]

    async def completion(_config, _prompt):
        return json.dumps({"workflows": workflows})

    monkeypatch.setattr(crawl_workflows.llm_svc, "plain_completion", completion)

    async def infer(prior=None):
        return await crawl_workflows._infer_workflows(
            object(),
            [{"url": "https://shop.test/account"}],
            {"https://shop.test/account"},
            prior,
        )

    assert [item["goal"] for item in asyncio.run(infer())] == [
        "Change email",
        "Change password",
    ]
    prior = {crawl_workflows._workflow_identity(workflows[0])}
    assert [item["goal"] for item in asyncio.run(infer(prior))] == ["Change password"]


def test_reached_note_never_requests_input():
    assert (
        crawl_workflows._needs_user_input({"status": "crawled", "needs_input": True})
        is False
    )


def test_reached_inference_is_recorded_without_opening_browser(monkeypatch):
    notes = []
    page = CrawledPage(id=42, test_run_id=999, url="https://shop.test/app")
    monkeypatch.setattr(
        crawl_workflows,
        "_crawl_inventory",
        lambda _run_id: ([{"page_id": 42, "url": page.url}], {page.url: page}),
    )
    monkeypatch.setattr(
        crawl_workflows, "_prior_workflow_identities", lambda _run_id: set()
    )
    monkeypatch.setattr(crawl_workflows, "_saved_workflow_proposals", lambda _site: [])
    monkeypatch.setattr(
        crawl_workflows, "list_workflow_notes", lambda _session, _id: []
    )

    async def infer(*_args):
        return [
            {
                "name": "Write review",
                "goal": "Open review editor",
                "reason": "Observed form",
                "start_url": page.url,
                "reached_page_id": 42,
                "destructive": False,
            }
        ]

    monkeypatch.setattr(crawl_workflows, "_infer_workflows", infer)
    monkeypatch.setattr(
        crawl_workflows,
        "_record_note",
        lambda *args, **kwargs: notes.append((args, kwargs)),
    )
    asyncio.run(
        crawl_workflows.explore_after_crawl(
            999,
            llm_cfg=object(),
            site=SimpleNamespace(base_url="https://shop.test"),
            creds=[],
            shared=object(),
            max_pages=10,
            browser_engine="chromium",
            browser_visible=False,
            pw_proxy={},
            global_http_header={},
        )
    )
    assert len(notes) == 1
    assert notes[0][0][2] == "crawled"
    assert notes[0][1]["page_id"] == 42
    assert notes[0][1].get("needs_input", False) is False


def test_workflow_reuses_saved_account_after_credential_ids_change():
    page = CrawledPage(
        test_run_id=298,
        url="https://bank.test/accounts",
        accessible_by="[34, 35]",
        req_auth=True,
    )
    credentials = [
        Credential(id=43, site_id=1, username="amelia", password="saved"),
        Credential(id=44, site_id=1, username="zoe", password="saved"),
    ]
    selected, required = crawl_workflows._workflow_credential(
        page, credentials, {34: {"amelia"}, 35: {"zoe"}}
    )
    assert required is True
    assert selected.id == 43
    assert selected.password == "saved"

    selected, required = crawl_workflows._workflow_credential(page, credentials, {})
    assert selected is None
    assert required is True

    public_page = CrawledPage(
        test_run_id=298, url="https://bank.test/help", accessible_by="[]"
    )
    assert crawl_workflows._workflow_credential(public_page, credentials, {}) == (
        None,
        False,
    )

    duplicate_usernames = [
        Credential(id=43, site_id=1, username="amelia", password="first"),
        Credential(id=44, site_id=1, username="amelia", password="second"),
    ]
    selected, required = crawl_workflows._workflow_credential(
        page, duplicate_usernames, {34: {"amelia"}}
    )
    assert selected is None
    assert required is True


def test_workflow_reads_old_credential_identity_from_page_views(isolated_db_engine):
    with Session(isolated_db_engine) as session:
        site = Site(name="Bank", base_url="https://bank.test")
        session.add(site)
        session.flush()
        run = TestRun(site_id=site.id, name="Crawl")
        session.add(run)
        session.flush()
        page = CrawledPage(
            test_run_id=run.id,
            url="https://bank.test/accounts",
            accessible_by="[34]",
        )
        session.add(page)
        session.flush()
        session.add(
            PageCredentialView(
                test_run_id=run.id,
                page_id=page.id,
                credential_id=34,
                username="amelia",
            )
        )
        session.commit()
        run_id = run.id
    assert crawl_workflows._historical_credential_usernames(run_id) == {34: {"amelia"}}


def test_state_change_guard_allows_cart_setup_and_waits_for_payment_data():
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
    assert not crawl_workflows._action_allowed(
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


def test_form_action_requires_supplied_payment_data_for_order_submission():
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
    assert not crawl_workflows._action_allowed(
        {"action": "click", "index": 0, "risk": "safe"}, observation
    )[0]
    assert crawl_workflows._action_allowed(
        {"action": "click", "index": 0, "risk": "safe"},
        observation,
        "Use the supplied test payment details",
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
        ("https://shop.test/login", "password"),
        ("https://shop.test/login", "otp"),
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


def test_bank_profile_contact_data_can_be_fictitious():
    assert crawl_workflows._can_generate_sample_data(
        {
            "name": "Send a birthday card",
            "goal": "Write a message",
            "destructive": False,
        }
    )
    assert crawl_workflows._action_allowed(
        {"action": "fill", "index": 0, "value": "1 Example Street"},
        {
            "url": "https://shop.test/admin/bank-team/profile",
            "controls": [],
            "fields": [
                {
                    "name": "bank_contact_address",
                    "fieldName": "bank_contact_address",
                    "type": "text",
                    "label": "Contact address",
                }
            ],
        },
        generate_sample_data=True,
    ) == (True, "")


def test_new_test_account_password_can_be_generated_but_current_password_cannot():
    observation = {
        "url": "https://shop.test/register",
        "title": "Create account",
        "controls": [],
        "fields": [
            {"fieldName": "password", "type": "password"},
            {"fieldName": "confirmPassword", "type": "password"},
            {"fieldName": "currentPassword", "type": "password"},
        ],
    }
    for index in (0, 1):
        assert crawl_workflows._action_allowed(
            {"action": "fill", "index": index, "value": "Test-only-secret-123"},
            observation,
            generate_sample_data=True,
        ) == (True, "")
    assert crawl_workflows._action_allowed(
        {"action": "fill", "index": 2, "value": "guessed-secret"},
        observation,
        generate_sample_data=True,
    ) == (False, "Payment or secret fields need user-supplied test data.")
    assert crawl_workflows._action_allowed(
        {"action": "fill", "index": 0, "value": "guessed-secret"},
        {
            **observation,
            "url": "https://shop.test/account",
            "title": "Sign in",
            "text": "Sign in or create account",
        },
        generate_sample_data=True,
    ) == (False, "Payment or secret fields need user-supplied test data.")


def test_model_reconsiders_missing_new_test_account_password(monkeypatch):
    responses = [
        {
            "action": "stop",
            "needs_input": True,
            "request": "Please provide a password for the new account.",
        },
        {"action": "fill", "index": 0, "value": "Test-only-secret-123"},
    ]

    async def fake_decide(*_args):
        return responses.pop(0)

    monkeypatch.setattr(crawl_workflows, "_decide_action", fake_decide)
    decision = asyncio.run(
        crawl_workflows._decide_with_corrections(
            object(),
            {"generate_sample_data": True},
            {
                "url": "https://shop.test/register",
                "title": "Create account",
                "fields": [{"fieldName": "password", "type": "password"}],
                "controls": [],
            },
            [],
        )
    )
    assert decision["action"] == "fill"
    assert responses == []


def test_radio_choices_use_field_indexes_and_keep_sensitive_fields_guarded():
    observation = {
        "url": "https://shop.test/feedback",
        "controls": [{"index": 0, "kind": "link", "name": "Offers"}],
        "fields": [
            {
                "index": 0,
                "name": "rating",
                "fieldName": "rating",
                "type": "radio",
                "choice_value": "5",
                "checked": False,
            }
        ],
    }
    assert crawl_workflows._action_allowed(
        {"action": "select", "index": 0, "value": "5"},
        observation,
        generate_sample_data=True,
    ) == (False, "Use check to choose a radio option.")
    assert crawl_workflows._action_allowed(
        {"action": "check", "index": 0},
        observation,
        generate_sample_data=True,
    )[0]
    assert not crawl_workflows._action_allowed(
        {"action": "check", "index": 0}, observation
    )[0]
    sensitive = {
        **observation,
        "fields": [
            {
                **observation["fields"][0],
                "name": "payment_method",
                "fieldName": "payment_method",
            }
        ],
    }
    assert (
        crawl_workflows._action_allowed(
            {"action": "check", "index": 0},
            sensitive,
            generate_sample_data=True,
        )[1]
        == "Payment or secret fields need user-supplied test data."
    )


def test_completed_field_action_is_rejected_when_value_is_still_present():
    observation = {
        "url": "https://shop.test/form",
        "controls": [],
        "fields": [
            {
                "index": 0,
                "name": "title",
                "fieldName": "title",
                "fieldId": "title",
                "type": "text",
                "has_value": True,
                "invalid": False,
            }
        ],
    }
    decision = {"action": "fill", "index": 0, "value": "Test title"}
    prior = {crawl_workflows._field_action_key(decision, observation)}
    assert crawl_workflows._action_allowed(
        decision, observation, generate_sample_data=True, prior_actions=prior
    ) == (False, "This field already has that value.")
    observation["fields"][0]["has_value"] = False
    assert crawl_workflows._action_allowed(
        decision, observation, generate_sample_data=True, prior_actions=prior
    )[0]


def test_multiline_field_can_use_more_than_100_characters():
    observation = {
        "url": "https://shop.test/form",
        "controls": [],
        "fields": [
            {
                "fieldName": "details",
                "type": "textarea",
                "value_limit": 2000,
            }
        ],
    }
    decision = {"action": "fill", "index": 0, "value": "detail: value\n" * 15}
    assert crawl_workflows._action_allowed(
        decision, observation, generate_sample_data=True
    )[0]
    observation["fields"][0]["value_limit"] = 80
    assert (
        crawl_workflows._action_allowed(
            decision, observation, generate_sample_data=True
        )[1]
        == "The proposed field value is too long."
    )


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


def test_crawler_model_gets_generation_rule_for_eligible_workflow(monkeypatch):
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
    assert "Generate missing ordinary sample values" in prompts[0]
    assert "do not invent names" in prompts[1]


def test_workflow_corrects_long_generated_value_without_stopping(monkeypatch):
    prompts = []
    responses = [
        {"action": "fill", "index": 0, "value": "x" * 101},
        {"action": "fill", "index": 0, "value": "Short test description"},
    ]

    async def fake_decide(_cfg, _workflow, _observation, history):
        prompts.append(history)
        return responses.pop(0)

    monkeypatch.setattr(crawl_workflows, "_decide_action", fake_decide)
    decision = asyncio.run(
        crawl_workflows._decide_with_corrections(
            object(),
            {"generate_sample_data": True},
            {
                "url": "https://shop.test/admin/products/new",
                "fields": [{"name": "description", "fieldName": "description"}],
                "controls": [],
            },
            ["fill sku"],
        )
    )
    assert decision["value"] == "Short test description"
    assert "value_limit" in prompts[1][-1]
    assert prompts[1][0] == "fill sku"


def test_workflow_reminds_model_of_generation_approval(monkeypatch):
    prompts = []
    responses = [
        {
            "action": "stop",
            "needs_input": True,
            "request": "Please provide the missing product description and stock.",
        },
        {"action": "fill", "index": 0, "value": "Test product"},
    ]

    async def fake_decide(_cfg, _workflow, _observation, history):
        prompts.append(history)
        return responses.pop(0)

    monkeypatch.setattr(crawl_workflows, "_decide_action", fake_decide)
    decision = asyncio.run(
        crawl_workflows._decide_with_corrections(
            object(),
            {"generate_sample_data": True},
            {
                "url": "https://shop.test/admin/products/new",
                "fields": [{"name": "description", "fieldName": "description"}],
                "controls": [],
            },
            [],
        )
    )
    assert decision["action"] == "fill"
    assert "Generate ordinary test values" in prompts[1][-1]


def test_workflow_corrects_radio_selection_and_repeated_field(monkeypatch):
    prompts = []
    responses = [
        {"action": "select", "index": 0, "value": "5"},
        {"action": "fill", "index": 1, "value": "Already set"},
        {"action": "check", "index": 0},
    ]

    async def fake_decide(_cfg, _workflow, _observation, history):
        prompts.append(history)
        return responses.pop(0)

    monkeypatch.setattr(crawl_workflows, "_decide_action", fake_decide)
    observation = {
        "url": "https://shop.test/feedback",
        "controls": [],
        "fields": [
            {"fieldName": "rating", "type": "radio", "choice_value": "5"},
            {"fieldName": "title", "type": "text", "has_value": True},
        ],
    }
    prior = {("https://shop.test/feedback", "title", "fill", "Already set")}
    decision = asyncio.run(
        crawl_workflows._decide_with_corrections(
            object(), {"generate_sample_data": True}, observation, [], prior
        )
    )
    assert decision["action"] == "check"
    assert "Radio choices" in prompts[1][-1]
    assert "already has" in prompts[2][-1]


def test_long_link_uses_href_and_radio_uses_choice_value():
    class Locator:
        def __init__(self, selector):
            self.selector = selector
            self.first = self
            self.called = None

        async def click(self, **kwargs):
            self.called = ("click", kwargs)

        async def check(self, **kwargs):
            self.called = ("check", kwargs)

    class Page:
        def __init__(self):
            self.locators = []

        def locator(self, selector):
            locator = Locator(selector)
            self.locators.append(locator)
            return locator

    page = Page()
    long_name = "Product details " + "x" * 130
    observation = {
        "controls": [
            {
                "kind": "link",
                "name": long_name[:100],
                "href": "https://shop.test/product",
                "rawHref": "/product",
            }
        ],
        "fields": [{"fieldName": "rating", "type": "radio", "choice_value": "5"}],
    }
    asyncio.run(
        crawl_workflows._apply_action(
            page, {"action": "click", "index": 0}, observation
        )
    )
    assert page.locators[0].selector == 'a[href="/product"]:visible'
    assert page.locators[0].called[0] == "click"
    step = asyncio.run(
        crawl_workflows._apply_action(
            page, {"action": "check", "index": 0}, observation
        )
    )
    assert page.locators[1].selector == '[name="rating"][value="5"]:visible'
    assert page.locators[1].called == ("check", {"force": True, "timeout": 8000})
    assert step["value"] == "5"


def test_long_control_uses_verified_dom_index():
    class Locator:
        def __init__(self, expected):
            self.expected = expected
            self.index = None
            self.clicked = False

        def nth(self, index):
            self.index = index
            return self

        async def evaluate(self, _script, expected):
            return expected == self.expected

        async def click(self, **_kwargs):
            self.clicked = True

    class Page:
        def __init__(self, matches=True):
            self.locator_obj = Locator(
                {"name": "Long button" + "x" * 89, "kind": "button", "href": ""}
                if matches
                else {}
            )

        def locator(self, selector):
            assert selector == crawl_workflows._CONTROL_SELECTOR
            return self.locator_obj

    item = {
        "domIndex": 12,
        "kind": "button",
        "name": "Long button" + "x" * 89,
        "href": "",
    }
    observation = {"controls": [item]}
    page = Page()
    asyncio.run(
        crawl_workflows._apply_action(
            page, {"action": "click", "index": 0}, observation
        )
    )
    assert page.locator_obj.index == 12
    assert page.locator_obj.clicked
    with pytest.raises(ValueError, match="control changed"):
        asyncio.run(
            crawl_workflows._apply_action(
                Page(False), {"action": "click", "index": 0}, observation
            )
        )


def test_timed_out_fill_uses_visible_editable_field():
    class Locator:
        first = None

        def __init__(self):
            self.first = self

        async def fill(self, _value, *, timeout):
            assert timeout == 8000
            raise PlaywrightTimeoutError("field did not become actionable")

    class Page:
        def __init__(self, filled):
            self.filled = filled
            self.arguments = None

        def locator(self, _selector):
            return Locator()

        async def evaluate(self, _script, arguments):
            self.arguments = arguments
            return self.filled

    decision = {"action": "fill", "index": 0, "value": "Test description"}
    observation = {"fields": [{"fieldName": "description", "fieldId": "description"}]}
    page = Page(True)
    step = asyncio.run(crawl_workflows._apply_action(page, decision, observation))
    assert step["selector"] == '[name="description"]'
    assert page.arguments == {
        "selector": '[name="description"]',
        "value": "Test description",
    }

    with pytest.raises(PlaywrightTimeoutError):
        asyncio.run(crawl_workflows._apply_action(Page(False), decision, observation))


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
    assert proposals[0]["generate_sample_data"] is True


def test_crawl_notes_save_workflow_definition_without_attempt_data(isolated_db_engine):
    with Session(isolated_db_engine) as session:
        site = Site(name="Shop", base_url="https://shop.test")
        session.add(site)
        session.flush()
        run = TestRun(site_id=site.id, name="Crawl")
        session.add(run)
        session.commit()
        run_id, site_id = run.id, site.id

    workflow = {
        "name": "Checkout",
        "goal": "Complete checkout",
        "reason": "Cart found",
        "start_url": "https://shop.test/cart",
    }
    crawl_workflows._record_note(
        run_id,
        workflow,
        "needs_input",
        [],
        "Needs a payment amount",
        needs_input=True,
        request="Supply a payment amount",
        instructions="Use a private account number",
    )
    with Session(isolated_db_engine) as session:
        saved = sites.workflow_data_for_site(session.get(Site, site_id))
    assert saved == [
        {
            "name": "Checkout",
            "goal": "Complete checkout",
            "start_url": "https://shop.test/cart",
            "instructions": "",
        }
    ]

    with Session(isolated_db_engine) as session:
        sites.save_site_workflow_data(
            session,
            site_id,
            {**workflow, "goal": "Use my edited checkout goal"},
            "Use approved test data",
        )
    crawl_workflows._record_note(
        run_id, workflow, "crawled", ["Finished"], "Reached checkout"
    )
    with Session(isolated_db_engine) as session:
        saved = sites.workflow_data_for_site(session.get(Site, site_id))
    assert len(saved) == 1
    assert saved[0]["goal"] == "Use my edited checkout goal"
    assert saved[0]["instructions"] == "Use approved test data"


def test_crawl_workflow_site_limit_does_not_stop_notes(isolated_db_engine):
    with Session(isolated_db_engine) as session:
        site = Site(name="Shop", base_url="https://shop.test")
        session.add(site)
        session.flush()
        run = TestRun(site_id=site.id, name="Crawl")
        session.add(run)
        session.commit()
        run_id, site_id = run.id, site.id

    for index in range(21):
        crawl_workflows._record_note(
            run_id,
            {
                "name": f"Workflow {index}",
                "goal": f"Reach page {index}",
                "reason": "Found in crawl",
                "start_url": f"https://shop.test/page/{index}",
            },
            "needs_input",
            [],
            "More input needed",
            needs_input=True,
        )
    with Session(isolated_db_engine) as session:
        assert len(crawl_workflows.list_workflow_notes(session, run_id)) == 21
        assert len(sites.workflow_data_for_site(session.get(Site, site_id))) == 20


def test_saved_payment_and_delete_workflows_do_not_generate_data():
    site = Site(
        name="Shop",
        base_url="https://shop.test",
        workflow_data_json=json.dumps(
            [
                {
                    "name": "Update bank details",
                    "goal": "Set up a bank transfer",
                    "start_url": "https://shop.test/account",
                    "instructions": "Use supplied test payment data",
                },
                {
                    "name": "Delete address",
                    "goal": "Remove an address",
                    "start_url": "https://shop.test/account",
                    "instructions": "Use the saved account",
                },
            ]
        ),
    )
    proposals = crawl_workflows._saved_workflow_proposals(site)
    assert [item["generate_sample_data"] for item in proposals] == [True, False]
    assert [item["destructive"] for item in proposals] == [False, True]


def test_bank_account_and_billing_address_forms_use_generated_sample_data():
    site = Site(
        name="Bank",
        base_url="https://bank.test",
        workflow_data_json=json.dumps(
            [
                {
                    "name": name,
                    "goal": goal,
                    "start_url": "https://bank.test/account",
                    "instructions": "Use a test contact name",
                }
                for name, goal in [
                    (
                        "Open a bank account",
                        "Choose an account type and enter contact details",
                    ),
                    ("Update billing address", "Save a new postal address"),
                ]
            ]
        ),
    )
    proposals = crawl_workflows._saved_workflow_proposals(site)
    assert len(proposals) == 2
    assert all(item["generate_sample_data"] for item in proposals)


@pytest.mark.parametrize(
    ("action", "field", "value"),
    [
        ("fill", {"type": "text", "fieldName": "contactName"}, "Test Person"),
        (
            "select",
            {
                "type": "select-one",
                "fieldName": "bankAccountType",
                "options": [{"value": "savings"}],
            },
            "savings",
        ),
        (
            "check",
            {
                "type": "radio",
                "fieldName": "bankAccountType",
                "choice_value": "savings",
            },
            "savings",
        ),
    ],
)
def test_account_opening_fields_accept_generated_data(action, field, value):
    allowed, reason = crawl_workflows._action_allowed(
        {"action": action, "index": 0, "value": value},
        {"url": "https://bank.test/bank-account/open", "fields": [field]},
        generate_sample_data=True,
    )
    assert allowed, reason


@pytest.mark.parametrize("instructions", ["", "Use 1 Example Street"])
def test_generated_cart_data_does_not_authorize_placing_an_order(instructions):
    allowed, reason = crawl_workflows._action_allowed(
        {"action": "click", "index": 0},
        {
            "url": "https://shop.test/checkout",
            "controls": [{"kind": "button", "name": "Place order"}],
        },
        instructions,
        generate_sample_data=True,
    )
    assert not allowed
    assert "Payment" in reason


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
        await crawl_workflows._retry_tasks[(run_id, 23)]

    asyncio.run(submit())
    with Session(isolated_db_engine) as session:
        saved = sites.workflow_data_for_site(session.get(Site, site_id))
    assert saved == []
    assert _retry_state(run_id, 23)["saved_to_site"] is False
    assert attempts == [(True, False, "Use 1 Example Street")]

    async def retry_without_input():
        crawl_workflows.start_workflow_retry(run_id, note, "")
        await crawl_workflows._retry_tasks[(run_id, 23)]

    asyncio.run(retry_without_input())
    assert attempts[-1] == (False, False, "")

    async def generate():
        crawl_workflows.start_workflow_retry(
            run_id, note, "", generate_sample_data=True
        )
        await crawl_workflows._retry_tasks[(run_id, 23)]

    asyncio.run(generate())
    assert attempts[-1] == (False, True, "")

    async def retry_approved_note():
        crawl_workflows.start_workflow_retry(
            run_id, {**note, "generate_sample_data": True}, ""
        )
        await crawl_workflows._retry_tasks[(run_id, 23)]

    asyncio.run(retry_approved_note())
    assert attempts[-1] == (False, False, "")
    crawl_workflows._retry_tasks.pop((run_id, 23), None)
    crawl_workflows._retry_results.pop((run_id, 23), None)


def test_retry_keeps_saved_values_and_guards_payment_fields(monkeypatch):
    run_id = 9_720
    workflows = []

    async def fake_retry(_run_id, workflow, *, save_to_site=False):
        workflows.append(workflow)

    monkeypatch.setattr(crawl_workflows, "_run_workflow_retry", fake_retry)
    note = {
        "id": 24,
        "name": "Update bank details",
        "goal": "Set up bank transfer",
        "start_url": "https://shop.test/account",
        "instructions": "Use the supplied test account",
        "generate_sample_data": True,
    }

    async def retry():
        crawl_workflows.start_workflow_retry(
            run_id, note, "", generate_sample_data=True
        )
        await crawl_workflows._retry_tasks[(run_id, 24)]

    try:
        asyncio.run(retry())
        assert workflows[0]["generate_sample_data"] is True
        assert workflows[0]["user_instructions"] == "Use the supplied test account"
        assert _retry_state(run_id, 24)["generate_sample_data"] is True
        with pytest.raises(ValueError, match="cannot be retried"):
            crawl_workflows.start_workflow_retry(
                run_id,
                {**note, "id": 25, "name": "Delete bank account"},
                "",
                generate_sample_data=True,
            )
    finally:
        crawl_workflows._retry_tasks.pop((run_id, 24), None)
        crawl_workflows._retry_results.pop((run_id, 24), None)


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
        assert crawl_workflows._prior_workflow_identities(run.id) == {
            ("checkout", "/", "")
        }
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
    with Session(isolated_db_engine) as session:
        running = session.get(TestRun, run_id)
        running.status = "running"
        session.add(running)
        session.commit()
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
    crawl_workflows._retry_results[(run_id, 123)] = {"saved_to_site": False}
    asyncio.run(
        crawl_workflows._run_workflow_retry(run_id, workflow, save_to_site=True)
    )
    assert captured["run_id"] == run_id
    assert captured["max_pages"] == 25
    assert captured["selected_workflows"] == [workflow]
    status = _retry_state(run_id, 123)
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
    crawl_workflows._retry_results[(run_id, 123)] = {"saved_to_site": False}
    asyncio.run(
        crawl_workflows._run_workflow_retry(run_id, workflow, save_to_site=True)
    )
    assert _retry_state(run_id, 123)["status"] == "error"
    with Session(isolated_db_engine) as session:
        assert sites.workflow_data_for_site(session.get(Site, site_id)) == [
            {
                "name": "Add a delivery address",
                "goal": "Save an address",
                "start_url": "https://shop.test/account/addresses",
                "instructions": "",
            }
        ]
        notes = crawl_workflows.list_workflow_notes(session, run_id)
    assert notes[-1]["instructions"] == "Use 1 Example Street"
    assert notes[-1]["needs_input"] is True

    monkeypatch.setattr(crawl_workflows, "explore_after_crawl", fake_explore)
    result["status"] = "crawled"
    workflow["generate_sample_data"] = True
    workflow["generated_values"] = [{"field": "full_name", "value": "AESPA Test User"}]
    crawl_workflows._retry_results[(run_id, 123)] = {"saved_to_site": False}
    asyncio.run(
        crawl_workflows._run_workflow_retry(run_id, workflow, save_to_site=True)
    )
    assert _retry_state(run_id, 123)["saved_to_site"] is True
    with Session(isolated_db_engine) as session:
        saved = sites.workflow_data_for_site(session.get(Site, site_id))
    assert saved[0]["instructions"] == (
        "Use 1 Example Street\nGenerated test values:\nfull_name: AESPA Test User"
    )
    with Session(isolated_db_engine) as session:
        for index in range(19):
            sites.save_site_workflow_data(
                session,
                site_id,
                {
                    "name": f"Saved workflow {index}",
                    "goal": "Reach a page",
                    "start_url": f"https://shop.test/page/{index}",
                },
                "",
            )
    other_workflow = {
        **workflow,
        "name": "Another address",
        "start_url": "https://shop.test/account/other",
    }
    crawl_workflows._retry_results[(run_id, 123)] = {"saved_to_site": False}
    asyncio.run(
        crawl_workflows._run_workflow_retry(run_id, other_workflow, save_to_site=True)
    )
    status = _retry_state(run_id, 123)
    assert status["status"] == "complete"
    assert status["result_status"] == "crawled"
    assert status["saved_to_site"] is False
    assert "up to 20 workflows" in status["save_error"]
    crawl_workflows._retry_results.pop((run_id, 123), None)


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


def test_generated_form_data_can_use_server_validation_before_asking_for_input():
    seen_errors = {}
    initial = {"form_errors": []}
    rejected = {"form_errors": ["Specs must include: Screen Size, CPU Brand."]}
    assert crawl_workflows._submission_validation_action(
        initial, generate_sample_data=True, seen_errors=seen_errors
    ) == ("ok", "")
    assert crawl_workflows._submission_validation_action(
        rejected, generate_sample_data=True, seen_errors=seen_errors
    ) == ("retry", "Check the form data: Specs must include: Screen Size, CPU Brand.")
    assert (
        crawl_workflows._submission_validation_action(
            rejected, generate_sample_data=True, seen_errors=seen_errors
        )[0]
        == "needs_input"
    )
    assert (
        crawl_workflows._submission_validation_action(
            rejected, generate_sample_data=False, seen_errors={}
        )[0]
        == "needs_input"
    )


def test_model_reconsiders_missing_generated_data_after_server_error(monkeypatch):
    decisions = [
        {
            "action": "stop",
            "needs_input": True,
            "request": "Required specs are missing.",
        },
        {"action": "fill", "index": 0, "value": "Screen Size: 14 inches"},
    ]
    histories = []

    async def fake_decide(_cfg, _workflow, _observation, history):
        histories.append(history)
        return decisions.pop(0)

    monkeypatch.setattr(crawl_workflows, "_decide_action", fake_decide)
    result = asyncio.run(
        crawl_workflows._decide_with_corrections(
            object(),
            {"generate_sample_data": True},
            {
                "url": "https://shop.test/admin/products/new",
                "fields": [
                    {"fieldName": "specs", "type": "textarea", "has_value": True}
                ],
                "controls": [],
                "form_errors": ["Specs must include: Screen Size."],
            },
            ["click Create product"],
        )
    )
    assert result["action"] == "fill"
    assert "Generate ordinary test values" in histories[1][-1]


def test_several_workflow_retries_can_run_at_once(monkeypatch):
    run_id = 9_731
    release = asyncio.Event()
    started: list[int] = []

    async def fake_retry(_run_id, workflow, *, save_to_site=False):
        started.append(workflow["retry_of"])
        await release.wait()

    monkeypatch.setattr(crawl_workflows, "_run_workflow_retry", fake_retry)

    def note(note_id: int) -> dict:
        return {
            "id": note_id,
            "name": f"Workflow {note_id}",
            "goal": "Reach a page",
            "start_url": "https://shop.test/account",
            "needs_input": True,
        }

    async def scenario():
        for note_id in (1, 2, 3):
            crawl_workflows.start_workflow_retry(run_id, note(note_id), "Use test data")
        with pytest.raises(ValueError, match="already running"):
            crawl_workflows.start_workflow_retry(run_id, note(2), "Use test data")
        with pytest.raises(ValueError, match="at once"):
            crawl_workflows.start_workflow_retry(run_id, note(4), "Use test data")
        status = crawl_workflows.workflow_retry_status(run_id)
        assert status["status"] == "running"
        assert [item["note_id"] for item in status["retries"]] == [1, 2, 3]
        await asyncio.sleep(0)
        assert sorted(started) == [1, 2, 3]
        release.set()
        await asyncio.gather(
            *(crawl_workflows._retry_tasks[(run_id, n)] for n in (1, 2, 3))
        )
        await asyncio.sleep(0)
        assert not crawl_workflows._active_retry_notes(run_id)
        crawl_workflows.start_workflow_retry(run_id, note(4), "Use test data")
        await crawl_workflows._retry_tasks[(run_id, 4)]

    try:
        asyncio.run(scenario())
    finally:
        for note_id in (1, 2, 3, 4):
            crawl_workflows._retry_tasks.pop((run_id, note_id), None)
            crawl_workflows._retry_results.pop((run_id, note_id), None)


def test_workflows_run_at_once_in_separate_browser_sessions(monkeypatch):
    import playwright.async_api

    from aespa.services import crawler

    run_id = 9_732
    start_page = SimpleNamespace(
        id=5, replay_credential_id=None, accessible_by="[]", req_auth=False
    )
    monkeypatch.setattr(
        crawl_workflows,
        "_crawl_inventory",
        lambda _run_id: (
            [{"url": "https://shop.test/a"}],
            {crawler._norm("https://shop.test/a"): start_page},
        ),
    )
    monkeypatch.setattr(
        crawl_workflows, "_historical_credential_usernames", lambda _run_id: {}
    )
    contexts = []

    class FakePage:
        url = "https://shop.test/a"

        async def goto(self, url, **_kwargs):
            self.url = url

    class FakeContext:
        def __init__(self):
            self.closed = False
            contexts.append(self)

        async def route(self, *_args):
            return None

        async def new_page(self):
            return FakePage()

        async def close(self):
            self.closed = True

    class FakeBrowser:
        async def new_context(self, **_kwargs):
            return FakeContext()

        async def close(self):
            return None

    class FakePlaywright:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_exc):
            return None

    async def fake_launch(*_args, **_kwargs):
        return FakeBrowser()

    async def no_wait(*_args, **_kwargs):
        return None

    running = 0
    most_running = 0

    async def fake_observe(_page):
        nonlocal running, most_running
        running += 1
        most_running = max(most_running, running)
        await asyncio.sleep(0.01)
        running -= 1
        return {"url": "https://shop.test/a", "fields": [], "controls": []}

    async def fake_decide(*_args, **_kwargs):
        return {"action": "stop", "reason": "Nothing more to do."}

    notes = []
    log_lines = []
    progress_events = []
    monkeypatch.setattr(
        crawler,
        "_crawl_log",
        lambda _run_id, phase, _status, message, **_kwargs: log_lines.append(
            (phase, message)
        ),
    )
    monkeypatch.setattr(
        crawler,
        "_crawl_progress",
        lambda _run_id, **kwargs: progress_events.append(kwargs),
    )
    monkeypatch.setattr(playwright.async_api, "async_playwright", FakePlaywright)
    monkeypatch.setattr(crawl_workflows, "launch_playwright_browser", fake_launch)
    monkeypatch.setattr(crawl_workflows, "playwright_user_agent", lambda _b: "test")
    monkeypatch.setattr(
        crawl_workflows, "protect_playwright_context", lambda *_args: None
    )
    monkeypatch.setattr(
        crawl_workflows.traffic_svc, "setup_playwright_logging", lambda *a, **k: None
    )
    monkeypatch.setattr(crawler, "_wait_for_content_settle", no_wait)
    monkeypatch.setattr(crawl_workflows, "_observe", fake_observe)
    monkeypatch.setattr(crawl_workflows, "_decide_with_corrections", fake_decide)
    monkeypatch.setattr(
        crawl_workflows,
        "_record_note",
        lambda _run_id, workflow, status, *_args, **_kwargs: notes.append(
            (workflow["name"], status)
        ),
    )
    workflows = [
        {
            "name": f"Workflow {index}",
            "goal": "Reach a page",
            "reason": "Seen in the crawl",
            "start_url": "https://shop.test/a",
            "destructive": False,
        }
        for index in range(5)
    ]
    asyncio.run(
        crawl_workflows.explore_after_crawl(
            run_id,
            llm_cfg=None,
            site=SimpleNamespace(base_url="https://shop.test", login_url=""),
            creds=[],
            shared=None,
            max_pages=10,
            browser_engine="chromium",
            browser_visible=False,
            pw_proxy={},
            global_http_header={},
            selected_workflows=workflows,
        )
    )
    assert len(contexts) == 5
    assert all(context.closed for context in contexts)
    assert most_running == crawl_workflows._MAX_PARALLEL_WORKFLOWS
    assert all(workflow["generate_sample_data"] for workflow in workflows)
    assert sorted(name for name, _status in notes) == [
        f"Workflow {index}" for index in range(5)
    ]
    # Without a progress callback (the crawl path) each step still reaches
    # the Activity Log and the crawler agent card.
    for index in range(5):
        assert (
            "crawl_workflow",
            f"Workflow {index}: Choosing the next step",
        ) in log_lines
    assert progress_events == []


def test_workflow_exploration_executes_action_and_reports_step(monkeypatch):
    import playwright.async_api

    from aespa.services import crawler

    run_id = 9_734

    class FakePage:
        url = "https://shop.test/a"

        async def goto(self, *_args, **_kwargs):
            return SimpleNamespace(status=200)

    class FakeContext:
        closed = False

        async def new_page(self):
            return FakePage()

        async def route(self, *_args, **_kwargs):
            return None

        async def set_extra_http_headers(self, *_args, **_kwargs):
            return None

        async def close(self):
            self.closed = True

    class FakeBrowser:
        async def new_context(self, **_kwargs):
            return FakeContext()

        async def close(self):
            return None

    class FakePlaywright:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_exc):
            return None

    notes = []
    log_lines = []
    progress_events = []
    reported = []
    decide_count = 0

    async def fake_decide(*_args, **_kwargs):
        nonlocal decide_count
        decide_count += 1
        if decide_count == 1:
            return {"action": "click", "index": 0}
        return {"action": "stop", "reason": "Completed successfully."}

    async def fake_apply_action(page, decision, observation):
        return {"action": "click", "name": "Submit", "selector": "#submit"}

    async def no_wait(*_args, **_kwargs):
        return None

    async def fake_observe(_page):
        return {
            "url": "https://shop.test/a",
            "fields": [],
            "controls": [{"name": "Submit", "kind": "button", "submits": False}],
        }

    start_page = SimpleNamespace(
        id=1, replay_credential_id=None, accessible_by="[]", req_auth=False
    )
    monkeypatch.setattr(
        crawl_workflows,
        "_crawl_inventory",
        lambda _run_id: (
            [{"url": "https://shop.test/a"}],
            {crawler._norm("https://shop.test/a"): start_page},
        ),
    )
    monkeypatch.setattr(
        crawler,
        "_crawl_log",
        lambda _run_id, phase, _status, message, **_kwargs: log_lines.append(
            (phase, message)
        ),
    )
    monkeypatch.setattr(
        crawler,
        "_crawl_progress",
        lambda _run_id, **kwargs: progress_events.append(kwargs),
    )
    monkeypatch.setattr(playwright.async_api, "async_playwright", FakePlaywright)

    async def fake_launch(*_a, **_k):
        return FakeBrowser()

    monkeypatch.setattr(crawl_workflows, "launch_playwright_browser", fake_launch)
    monkeypatch.setattr(crawl_workflows, "playwright_user_agent", lambda _b: "test")
    monkeypatch.setattr(
        crawl_workflows, "protect_playwright_context", lambda *_args: None
    )
    monkeypatch.setattr(
        crawl_workflows.traffic_svc, "setup_playwright_logging", lambda *a, **k: None
    )
    monkeypatch.setattr(crawler, "_wait_for_content_settle", no_wait)
    monkeypatch.setattr(crawl_workflows, "_observe", fake_observe)
    monkeypatch.setattr(crawl_workflows, "_decide_with_corrections", fake_decide)
    monkeypatch.setattr(crawl_workflows, "_apply_action", fake_apply_action)
    monkeypatch.setattr(
        crawl_workflows,
        "_record_note",
        lambda _run_id, workflow, status, descriptions, detail, *_args, **_kwargs: (
            notes.append((workflow["name"], status, descriptions, detail))
        ),
    )

    workflows = [
        {
            "name": "Submit Form",
            "goal": "Submit the form",
            "reason": "Test form submission",
            "start_url": "https://shop.test/a",
            "destructive": False,
        }
    ]

    asyncio.run(
        crawl_workflows.explore_after_crawl(
            run_id,
            llm_cfg=None,
            site=SimpleNamespace(base_url="https://shop.test", login_url=""),
            creds=[],
            shared=None,
            max_pages=10,
            browser_engine="chromium",
            browser_visible=False,
            pw_proxy={},
            global_http_header={},
            selected_workflows=workflows,
            progress=lambda changes: reported.append(changes),
        )
    )

    assert len(notes) == 1
    name, status, descriptions, detail = notes[0]
    assert name == "Submit Form"
    assert status == "not_reached"
    assert descriptions == ["click Submit"]
    assert detail == "Completed successfully."
    assert any(
        msg == "Submit Form: Clicking a page control" for phase, msg in log_lines
    )
    assert any(msg == "Submit Form: Checking the result" for phase, msg in log_lines)
    assert any(r.get("stage") == "finished" for r in reported)


def test_inferred_workflows_after_payment_and_delete_are_all_tried(monkeypatch):
    import playwright.async_api

    from aespa.services import crawler

    url = "https://shop.test/account"
    start_page = SimpleNamespace(
        id=5, replay_credential_id=None, accessible_by="[]", req_auth=False
    )
    monkeypatch.setattr(
        crawl_workflows,
        "_crawl_inventory",
        lambda _run_id: ([{"url": url}], {crawler._norm(url): start_page}),
    )
    monkeypatch.setattr(crawl_workflows, "_saved_workflow_proposals", lambda _site: [])
    monkeypatch.setattr(
        crawl_workflows, "_prior_workflow_identities", lambda _run_id: set()
    )
    monkeypatch.setattr(crawl_workflows, "list_workflow_notes", lambda *_args: [])
    monkeypatch.setattr(
        crawl_workflows, "_historical_credential_usernames", lambda _run_id: {}
    )
    workflows = [
        {
            "name": name,
            "goal": goal,
            "reason": "Observed in crawl",
            "start_url": url,
            "inferred": True,
            "destructive": destructive,
        }
        for name, goal, destructive in (
            ("Make payment", "Pay for an order", False),
            ("Delete address", "Remove an address", True),
            *((f"Workflow {index}", "Update account", False) for index in range(6)),
        )
    ]

    async def infer(*_args):
        return workflows

    class Page:
        def __init__(self):
            self.url = url

        async def goto(self, target, **_kwargs):
            self.url = target

    class Context:
        async def route(self, *_args):
            pass

        async def new_page(self):
            return Page()

        async def close(self):
            pass

    class Browser:
        async def new_context(self, **_kwargs):
            return Context()

        async def close(self):
            pass

    class Playwright:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            pass

    async def launch(*_args, **_kwargs):
        return Browser()

    async def no_wait(*_args, **_kwargs):
        pass

    async def decide(*_args, **_kwargs):
        return {"action": "stop", "reason": "Nothing more to do."}

    notes = []
    monkeypatch.setattr(crawl_workflows, "_infer_workflows", infer)
    monkeypatch.setattr(playwright.async_api, "async_playwright", Playwright)
    monkeypatch.setattr(crawl_workflows, "launch_playwright_browser", launch)
    monkeypatch.setattr(crawl_workflows, "playwright_user_agent", lambda _b: "test")
    monkeypatch.setattr(
        crawl_workflows, "protect_playwright_context", lambda *_args: None
    )
    monkeypatch.setattr(
        crawl_workflows.traffic_svc, "setup_playwright_logging", lambda *a, **k: None
    )
    monkeypatch.setattr(crawler, "_wait_for_content_settle", no_wait)
    monkeypatch.setattr(
        crawl_workflows,
        "_observe",
        lambda _page: no_wait(),
    )
    monkeypatch.setattr(crawl_workflows, "_decide_with_corrections", decide)
    monkeypatch.setattr(
        crawl_workflows,
        "_record_note",
        lambda _run_id, workflow, status, *_args, **_kwargs: notes.append(
            (workflow["name"], status)
        ),
    )

    asyncio.run(
        crawl_workflows.explore_after_crawl(
            9_733,
            llm_cfg=object(),
            site=SimpleNamespace(base_url="https://shop.test", login_url=""),
            creds=[],
            shared=None,
            max_pages=10,
            browser_engine="chromium",
            browser_visible=False,
            pw_proxy={},
            global_http_header={},
        )
    )
    statuses = dict(notes)
    assert statuses["Make payment"] == "not_reached"
    assert statuses["Delete address"] == "not_attempted"
    assert [statuses[f"Workflow {index}"] for index in range(6)] == ["not_reached"] * 6
    assert [workflow["generate_sample_data"] for workflow in workflows] == [
        True,
        False,
        True,
        True,
        True,
        True,
        True,
        True,
    ]


def test_payment_opens_browser_while_delete_stays_blocked(monkeypatch):
    import playwright.async_api

    from aespa.services import crawler

    url = "https://shop.test/account"
    page = SimpleNamespace(
        id=5, replay_credential_id=None, accessible_by="[]", req_auth=False
    )
    monkeypatch.setattr(
        crawl_workflows,
        "_crawl_inventory",
        lambda _run_id: ([{"url": url}], {crawler._norm(url): page}),
    )
    monkeypatch.setattr(
        crawl_workflows, "_historical_credential_usernames", lambda _id: {}
    )
    notes = []
    monkeypatch.setattr(
        crawl_workflows,
        "_record_note",
        lambda _id, workflow, status, _steps, _detail, **kwargs: notes.append(
            (
                workflow["name"],
                status,
                kwargs.get("needs_input"),
                workflow["generate_sample_data"],
            )
        ),
    )

    class Browser:
        async def new_context(self, **_kwargs):
            raise AssertionError("Payment browser opened")

        async def close(self):
            pass

    class Playwright:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            pass

    async def launch(*_args, **_kwargs):
        return Browser()

    monkeypatch.setattr(playwright.async_api, "async_playwright", Playwright)
    monkeypatch.setattr(crawl_workflows, "launch_playwright_browser", launch)
    workflows = [
        {
            "name": name,
            "goal": goal,
            "reason": "Observed in crawl",
            "start_url": url,
            "destructive": destructive,
            "generate_sample_data": True,
        }
        for name, goal, destructive in (
            ("Make payment", "Pay for an order", False),
            ("Delete address", "Remove an address", True),
        )
    ]
    with pytest.raises(AssertionError, match="Payment browser opened"):
        asyncio.run(
            crawl_workflows.explore_after_crawl(
                9_721,
                llm_cfg=None,
                site=SimpleNamespace(base_url="https://shop.test", login_url=""),
                creds=[],
                shared=None,
                max_pages=10,
                browser_engine="chromium",
                browser_visible=False,
                pw_proxy={},
                global_http_header={},
                selected_workflows=workflows,
            )
        )
    assert notes == [("Delete address", "not_attempted", None, False)]


def _payment_observation() -> dict:
    return {
        "url": "https://shop.test/checkout",
        "controls": [],
        "fields": [
            {
                "index": 0,
                "name": "pm",
                "fieldName": "pm",
                "type": "radio",
                "label": "New card",
                "choice_value": "new",
                "checked": True,
            },
            {
                "index": 1,
                "name": "pm",
                "fieldName": "pm",
                "type": "radio",
                "label": "Bank transfer - pay after placing the order",
                "choice_value": "bank-transfer",
                "checked": False,
            },
            {
                "index": 2,
                "name": "cardNumber",
                "fieldName": "cardNumber",
                "fieldId": "cardNumber",
                "type": "text",
                "label": "Card number",
            },
        ],
    }


@pytest.mark.parametrize(
    "instructions",
    [
        "Pay by bank transfer",
        "Use bank-transfer",
        "Choose Bank transfer - pay after placing the order",
    ],
)
def test_radio_choice_is_accepted_when_instructions_name_its_label(instructions):
    assert crawl_workflows._action_allowed(
        {"action": "check", "index": 1},
        _payment_observation(),
        instructions,
        generate_sample_data=True,
    ) == (True, "")


def test_radio_choice_needs_a_whole_word_match():
    observation = _payment_observation()
    for instructions in ["Use a saved payment method", "Banking details to follow"]:
        assert crawl_workflows._action_allowed(
            {"action": "check", "index": 1},
            observation,
            instructions,
            generate_sample_data=True,
        ) == (False, "Payment or secret fields need user-supplied test data.")


def test_needs_input_request_names_the_field_or_option():
    observation = _payment_observation()
    assert crawl_workflows._input_request(
        "Payment or secret fields need user-supplied test data.",
        {"action": "check", "index": 1},
        observation,
    ) == (
        'Name the option to choose, such as "Bank transfer - pay after placing '
        'the order". Other options: "New card".'
    )
    assert (
        crawl_workflows._input_request(
            "Payment or secret fields need user-supplied test data.",
            {"action": "fill", "index": 2, "value": "4111"},
            observation,
        )
        == 'Provide a test value for the "Card number" payment or secret field.'
    )
    assert (
        crawl_workflows._input_request(
            "The field needs a value supplied by the user.",
            {"action": "fill", "index": 0},
            {"fields": [{"fieldName": "postcode", "type": "text"}]},
        )
        == 'Provide a sample value for the "postcode" field.'
    )


def test_live_account_option_and_labeled_value_need_exact_authenticated_evidence():
    option = {
        "fieldName": "from_account",
        "type": "select-one",
        "options": [{"value": "own-42", "label": "My account"}],
    }
    account = {"fieldName": "own_account_number", "type": "text"}
    observation = {
        "url": "https://bank.test/#/transfers",
        "fields": [option, account],
        "controls": [],
    }
    assert crawl_workflows._action_allowed(
        {"action": "select", "index": 0, "value": "own-42"},
        observation,
        payment_workflow=True,
        site_actor_id=7,
    ) == (True, "")
    assert not crawl_workflows._action_allowed(
        {"action": "select", "index": 0, "value": "invented"},
        observation,
        payment_workflow=True,
        site_actor_id=7,
    )[0]
    assert crawl_workflows._action_allowed(
        {"action": "select", "index": 0, "value": "own-42"},
        observation,
        payment_workflow=True,
    )[0]

    evidence = [
        {
            "source_url": "https://bank.test/#/accounts",
            "label": "Own account number",
            "value": "12345678",
            "actor_id": 7,
        }
    ]
    assert crawl_workflows._action_allowed(
        {"action": "fill", "index": 1, "value": "12345678"},
        observation,
        payment_workflow=True,
        site_actor_id=7,
        site_values=evidence,
    ) == (True, "")
    assert not crawl_workflows._action_allowed(
        {"action": "fill", "index": 1, "value": "12345678"},
        observation,
        payment_workflow=True,
        site_actor_id=8,
        site_values=evidence,
    )[0]
    assert not crawl_workflows._action_allowed(
        {"action": "fill", "index": 1, "value": "87654321"},
        observation,
        payment_workflow=True,
        site_actor_id=7,
        site_values=evidence,
    )[0]


def test_transfer_amount_cannot_use_generated_or_account_evidence():
    observation = {
        "url": "https://bank.test/#/transfers",
        "fields": [{"fieldId": "transfer-own-amount", "type": "text"}],
        "controls": [],
    }
    evidence = [
        {
            "source_url": "https://bank.test/#/accounts",
            "label": "Own account number",
            "value": "12345678",
            "actor_id": 7,
        }
    ]
    for value in ("50", "12345678"):
        assert crawl_workflows._action_allowed(
            {"action": "fill", "index": 0, "value": value},
            observation,
            generate_sample_data=True,
            payment_workflow=True,
            site_actor_id=7,
            site_values=evidence,
        ) == (False, "Payment or secret fields need user-supplied test data.")


def test_existing_shipping_address_can_fill_matching_field_only():
    evidence = [
        {
            "source_url": "https://shop.test/account/addresses",
            "label": "Shipping address",
            "value": "1 Example Street",
            "actor_id": 7,
        }
    ]
    observation = {
        "url": "https://shop.test/checkout",
        "fields": [
            {"fieldName": "shippingAddress", "type": "text"},
            {"fieldName": "billingAddress", "type": "text"},
        ],
        "controls": [],
    }
    assert crawl_workflows._action_allowed(
        {"action": "fill", "index": 0, "value": "1 Example Street"},
        observation,
        site_values=evidence,
        site_actor_id=7,
    ) == (True, "")
    assert not crawl_workflows._action_allowed(
        {"action": "fill", "index": 1, "value": "1 Example Street"},
        observation,
        site_values=evidence,
        site_actor_id=7,
    )[0]


def test_labeled_site_values_are_not_saved_in_workflow_notes(monkeypatch):
    from aespa.services import crawler

    recorded = []
    monkeypatch.setattr(
        crawler,
        "_crawl_log",
        lambda _run_id, _phase, _status, _message, **kwargs: recorded.append(
            kwargs["data"]["note"]
        ),
    )
    workflow = {
        "name": "Transfer",
        "goal": "Open transfer",
        "reason": "Found in crawl",
        "start_url": "https://bank.test/#/transfers",
        "_site_actor_id": 7,
        "_site_values": [
            {
                "source_url": "https://bank.test/#/accounts",
                "label": "Own account number",
                "value": "12345678",
                "actor_id": 7,
            }
        ],
    }
    crawl_workflows._record_note(1, workflow, "not_reached", [], "Needs amount")
    assert "12345678" not in json.dumps(recorded)
    assert "_site_values" not in recorded[0]


def test_labeled_account_values_are_read_from_live_dom_pairs(monkeypatch):
    class Page:
        url = "https://bank.test/#/accounts"

        async def evaluate(self, _script):
            return [
                {"label": "Own account number", "value": "12345678"},
                {"label": "Shipping address", "value": "1 Example Street"},
                {"label": "One-time code", "value": "123456"},
                {"label": "Card number", "value": "4111111111111111"},
            ]

    values = asyncio.run(crawl_workflows._collect_labeled_site_values(Page()))
    assert values == [
        {
            "source_url": "https://bank.test/#/accounts",
            "label": "Own account number",
            "value": "12345678",
        },
        {
            "source_url": "https://bank.test/#/accounts",
            "label": "Shipping address",
            "value": "1 Example Street",
        },
    ]


def test_account_evidence_value_is_not_sent_in_workflow_prompt(monkeypatch):
    prompts = []

    async def completion(_config, prompt):
        prompts.append(prompt)
        return '{"action":"stop"}'

    monkeypatch.setattr(crawl_workflows.llm_svc, "plain_completion", completion)
    workflow = {
        "name": "Transfer",
        "goal": "Open transfer",
        "_site_values": [
            {
                "source_url": "https://bank.test/#/accounts",
                "label": "Own account number",
                "value": "12345678",
                "actor_id": 7,
            }
        ],
    }
    asyncio.run(
        crawl_workflows._decide_action(
            object(),
            workflow,
            {
                "fields": [{"_current_value": "12345678"}],
                "_hidden_amounts": [{"name": "order_total", "value": "12345678"}],
            },
            [],
        )
    )
    assert "Own account number" in prompts[0]
    assert "12345678" not in prompts[0]


def test_labeled_site_value_index_resolves_to_exact_value(monkeypatch):
    async def decision(*_args):
        return {"action": "fill", "index": 0, "site_value_index": 0}

    monkeypatch.setattr(crawl_workflows, "_decide_action", decision)
    workflow = {
        "name": "Transfer",
        "goal": "Open transfer",
        "_site_actor_id": 7,
        "_site_values": [
            {
                "source_url": "https://bank.test/#/accounts",
                "label": "Own account number",
                "value": "12345678",
                "actor_id": 7,
            }
        ],
    }
    observation = {
        "url": "https://bank.test/#/transfers",
        "fields": [{"fieldName": "own_account_number", "type": "text"}],
        "controls": [],
    }
    result = asyncio.run(
        crawl_workflows._decide_with_corrections(object(), workflow, observation, [])
    )
    assert result["value"] == "12345678"


def test_form_value_sources_are_explicit_and_actor_bound():
    field = {"fieldName": "billing_address"}
    evidence = [
        {
            "source_url": "https://shop.test/profile",
            "label": "Billing address",
            "value": "1 Test Lane",
            "actor_id": 7,
        }
    ]
    decision = {"action": "fill", "value": "1 Test Lane"}
    assert (
        crawl_workflows._value_source(
            decision, field, "", site_values=evidence, site_actor_id=7
        )
        == "site_value"
    )
    assert (
        crawl_workflows._value_source(
            decision, field, "", site_values=evidence, site_actor_id=8
        )
        == "generated"
    )
    assert crawl_workflows._value_source(decision, field, "1 Test Lane") == "user"
    option = {"fieldName": "from_account", "options": [{"value": "own-1"}]}
    assert (
        crawl_workflows._value_source(
            {"action": "select", "value": "own-1"}, option, ""
        )
        == "site_option"
    )


def test_stopping_retry_before_it_starts_settles_its_status(monkeypatch):
    async def retry(*_args, **_kwargs):
        await asyncio.sleep(60)

    monkeypatch.setattr(crawl_workflows, "_run_workflow_retry", retry)
    note = {
        "id": 991,
        "name": "Account form",
        "goal": "Open account form",
        "start_url": "https://bank.test/account",
    }

    async def run():
        crawl_workflows.start_workflow_retry(991, note, "")
        crawl_workflows.request_retry_stop(991)
        await asyncio.gather(
            crawl_workflows._retry_tasks[(991, 991)], return_exceptions=True
        )
        await asyncio.sleep(0)
        assert (
            crawl_workflows.workflow_retry_status(991)["retries"][0]["status"]
            == "stopped"
        )
        await crawl_workflows.stop_retries_and_wait(991)
        assert crawl_workflows.workflow_retry_status(991)["retries"] == []

    asyncio.run(run())


def test_reached_page_keeps_exact_site_fill_in_local_replay(
    isolated_db_engine, monkeypatch
):
    from aespa.services import crawler

    with Session(isolated_db_engine) as session:
        site = Site(name="Bank", base_url="https://bank.test")
        session.add(site)
        session.flush()
        run = TestRun(site_id=site.id, name="Transfer test")
        session.add(run)
        session.commit()
        run_id = run.id

    class Page:
        url = "https://bank.test/#/transfers/complete"

        async def title(self):
            return "Transfer complete"

        async def evaluate(self, script):
            return [] if "a[href]" in script else "Transfer complete"

    async def snapshot(*_args, **_kwargs):
        return {"key": "transfer-complete"}

    async def no_intelligence(**_kwargs):
        return None

    async def analyze(*_args):
        return "Transfer complete", None, {}

    monkeypatch.setattr(crawler, "_interactive_state_snapshot", snapshot)
    monkeypatch.setattr(crawler, "_record_page_intelligence", no_intelligence)
    monkeypatch.setattr(crawler, "_save_credential_view", lambda *_args: None)
    monkeypatch.setattr(crawler, "_update_accessible_by", lambda *_args: None)
    monkeypatch.setattr(crawler, "_save_link", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(crawl_workflows.llm_svc, "analyse_page", analyze)
    step = {"kind": "fill", "selector": '[name="fromAccount"]', "value": "12345678"}
    shared = crawler._CrawlShared(
        crawled_norms={}, state_keys={}, pages_done=0, run_id=run_id
    )
    page_id = asyncio.run(
        crawl_workflows._save_discovered_page(
            run_id=run_id,
            page=Page(),
            root_url="https://bank.test/#/transfers",
            steps=[step],
            parent_id=None,
            credential_id=None,
            username="test",
            shared=shared,
            max_pages=10,
            llm_cfg=object(),
        )
    )
    with Session(isolated_db_engine) as session:
        saved = session.get(CrawledPage, page_id)
        assert json.loads(saved.replay_steps_json)["steps"] == [step]
        assert session.get(TestRun, run_id).pages_discovered == 1


def test_clear_rejects_an_active_workflow_retry(
    isolated_db_engine, isolated_client, monkeypatch
):
    with Session(isolated_db_engine) as session:
        site = Site(name="Bank", base_url="https://bank.test")
        session.add(site)
        session.flush()
        run = TestRun(site_id=site.id, name="Transfer test")
        session.add(run)
        session.commit()
        run_id = run.id

    monkeypatch.setattr(
        crawl_workflows,
        "workflow_retry_status",
        lambda _run_id: {"status": "running", "retries": []},
    )
    response = isolated_client.post(f"/api/test-runs/{run_id}/crawl/clear")
    assert response.status_code == 409
    with Session(isolated_db_engine) as session:
        assert session.get(TestRun, run_id) is not None


def test_delete_waits_for_workflow_retries(
    isolated_db_engine, isolated_client, monkeypatch
):
    with Session(isolated_db_engine) as session:
        site = Site(name="Bank", base_url="https://bank.test")
        session.add(site)
        session.flush()
        run = TestRun(site_id=site.id, name="Transfer test")
        session.add(run)
        session.commit()
        run_id = run.id

    waited = []

    async def stop_retries(_run_id):
        with Session(isolated_db_engine) as session:
            waited.append((_run_id, session.get(TestRun, _run_id) is not None))

    monkeypatch.setattr(crawl_workflows, "stop_retries_and_wait", stop_retries)
    response = isolated_client.delete(f"/api/test-runs/{run_id}")
    assert response.status_code == 204
    assert waited == [(run_id, True)]
    with Session(isolated_db_engine) as session:
        assert session.get(TestRun, run_id) is None


def test_transfer_submit_requires_user_supplied_amount_even_when_prefilled():
    url = "https://bank.test/#/transfers"
    observation = {
        "url": url,
        "controls": [{"name": "Transfer", "kind": "button", "submits": True}],
        "fields": [
            {
                "fieldId": "transfer-own-from",
                "label": "From Account",
                "type": "select-one",
                "selected_value": "own-1",
                "options": [{"value": "own-1", "label": "My account"}],
            },
            {
                "fieldId": "transfer-own-amount",
                "type": "number",
                "has_value": True,
                "_current_value": "5.00",
            },
        ],
    }
    decision = {"action": "click", "index": 0}
    allowed, reason = crawl_workflows._action_allowed(
        decision, observation, payment_workflow=True
    )
    assert not allowed
    assert '"transfer-own-amount"' in reason
    assert crawl_workflows._action_allowed(
        decision,
        observation,
        "Use 5.00 for this transfer",
        payment_workflow=True,
        prior_actions={(url, "transfer-own-amount", "fill", "5.00")},
    ) == (True, "")

    observation["fields"][1]["_current_value"] = "50.00"
    assert not crawl_workflows._action_allowed(
        decision,
        observation,
        "Use 5.00 for this transfer",
        payment_workflow=True,
        prior_actions={(url, "transfer-own-amount", "fill", "5.00")},
    )[0]


def test_js_confirm_payment_checks_the_amount():
    observation = {
        "url": "https://example.test/checkout",
        "controls": [{"name": "Confirm", "kind": "button", "submits": False}],
        "fields": [
            {
                "fieldId": "amount",
                "type": "number",
                "has_value": True,
                "_current_value": "50",
            }
        ],
    }
    assert not crawl_workflows._action_allowed(
        {"action": "click", "index": 0}, observation, payment_workflow=True
    )[0]
    observation["fields"][0]["fieldId"] = "order_total"
    assert not crawl_workflows._action_allowed(
        {"action": "click", "index": 0}, observation, payment_workflow=True
    )[0]


def test_js_confirm_payment_checks_a_hidden_total():
    observation = {
        "url": "https://example.test/checkout",
        "controls": [{"name": "Confirm", "kind": "button", "submits": False}],
        "fields": [],
        "_hidden_amounts": [{"name": "orderTotal", "value": "50"}],
    }
    decision = {"action": "click", "index": 0}
    assert not crawl_workflows._action_allowed(
        decision, observation, payment_workflow=True
    )[0]
    assert crawl_workflows._action_allowed(
        decision, observation, "Use 50 for this order", payment_workflow=True
    ) == (True, "")


def test_payment_amount_must_match_a_complete_supplied_value():
    observation = {
        "url": "https://example.test/checkout",
        "controls": [],
        "fields": [{"fieldId": "amount", "type": "number"}],
    }
    assert not crawl_workflows._action_allowed(
        {"action": "fill", "index": 0, "value": "5"},
        observation,
        "Use 50 for this transfer",
        payment_workflow=True,
    )[0]


def test_counterparty_account_text_cannot_fill_own_account_field():
    field = {"fieldName": "fromAccount", "type": "text"}
    counterparty = {
        "source_url": "https://bank.test/#/transactions/123",
        "label": "Counterparty account",
        "value": "98765432",
        "actor_id": 7,
    }
    own = {
        "source_url": "https://bank.test/#/accounts",
        "label": "Own account number",
        "value": "12345678",
        "actor_id": 7,
    }
    assert not crawl_workflows._site_evidence_matches(
        field, "98765432", [counterparty], 7
    )
    assert crawl_workflows._site_evidence_matches(field, "12345678", [own], 7)


def test_payment_tab_can_open_before_form_values_are_supplied():
    observation = {
        "url": "https://bank.test/#/transfers",
        "controls": [{"name": "Pay Someone", "kind": "button", "submits": False}],
        "fields": [],
    }
    assert crawl_workflows._action_allowed(
        {"action": "click", "index": 0}, observation, payment_workflow=True
    ) == (True, "")


def test_site_value_lookup_uses_relevant_pages_accessible_to_same_account():
    pages = {
        "summary": SimpleNamespace(
            url="https://example.test/dashboard/overview",
            title="Your savings and checking accounts",
            page_text="Savings balance and account number",
            accessible_by="[7]",
            replay_credential_id=None,
            depth=2,
        ),
        "other": SimpleNamespace(
            url="https://example.test/customer/details",
            title="Your savings account",
            page_text="Account number",
            accessible_by="[8]",
            replay_credential_id=None,
            depth=1,
        ),
        "help": SimpleNamespace(
            url="https://example.test/help",
            title="Help",
            page_text="Contact support",
            accessible_by="[7]",
            replay_credential_id=None,
            depth=1,
        ),
    }
    selected = crawl_workflows._site_value_pages(
        pages,
        {"name": "Move money between savings accounts", "goal": "Transfer savings"},
        7,
        "example.test",
    )
    assert [page.url for page in selected] == [
        "https://example.test/dashboard/overview",
        "https://example.test/help",
    ]
