from __future__ import annotations

import asyncio
import hashlib
import json
from collections import deque
from pathlib import Path

import pytest

from aespa.services.route_sampling import (
    LAYOUT_SKETCH_SIZE,
    RouteSampler,
    _candidate_keys,
    _cluster,
    _member_identity,
    page_features,
    page_similarity,
)

REAL_SITES = json.loads(
    (Path(__file__).parents[1] / "fixtures" / "route_sampling_layouts.json").read_text()
)

PRODUCT = {"kind": "product", "layout": list(range(1000, 1200)), "size": 200}


def _page(name: str) -> dict:
    """A page whose layout shares nothing with other pages."""
    start = int(hashlib.sha256(name.encode()).hexdigest()[:6], 16) * 1000
    return {"kind": "page", "layout": list(range(start, start + 200)), "size": 200}


def _links(path: str, count: int, start: int = 0) -> list[dict]:
    return [
        {
            "url": f"https://shop.test/{path}/{index}",
            "depth": 1,
            "parent_id": 1,
            "incoming_action": {"action_kind": "navigate"},
        }
        for index in range(start, start + count)
    ]


def _visit_all(sampler: RouteSampler, items: list[dict], features, phase: str) -> list:
    """Observe examples until the sampler stops asking for more."""
    queue = list(items)
    released = []
    while queue:
        item = queue.pop(0)
        more = sampler.observe(item["url"], features(item["url"]), phase)
        queue.extend(more)
        released.extend(more)
    return released


def _phase(sampler: RouteSampler, phase: str, key: str | None = None) -> dict:
    group = sampler.groups[key] if key else next(iter(sampler.groups.values()))
    return group["phases"][phase]


def test_catalogue_links_are_held_before_queue_and_five_examples_confirm() -> None:
    sampler = RouteSampler()
    admitted = sampler.offer(_links("products", 40_000), "anonymous")
    assert len(admitted) == 3
    assert len(sampler.resume_items("anonymous")) == 3

    more = []
    for item in admitted:
        more.extend(sampler.observe(item["url"], PRODUCT, "anonymous"))
    assert len(more) == 2
    for item in more:
        sampler.observe(item["url"], PRODUCT, "anonymous")
    summary = sampler.summaries()[0]
    assert summary["label"] == "Product pages"
    assert summary["links_seen"] == 40_000
    assert summary["pages_sampled"] == 5
    assert summary["examples_different"] == 0
    assert RouteSampler(sampler.snapshot()).summaries() == sampler.summaries()


def test_different_feature_pages_release_held_links() -> None:
    sampler = RouteSampler()
    admitted = sampler.offer(_links("features", 10), "anonymous")
    assert len(admitted) == 3
    released = _visit_all(sampler, admitted, _page, "anonymous")
    assert len(released) == 7
    assert sampler.summaries() == []
    assert len(sampler.offer(_links("features", 5, start=50), "anonymous")) == 5


def test_one_odd_page_is_reported_without_rejecting_the_route() -> None:
    sampler = RouteSampler()
    admitted = sampler.offer(_links("products", 40), "anonymous")
    odd = admitted[1]["url"]
    _visit_all(
        sampler,
        admitted,
        lambda url: _page(url) if url == odd else PRODUCT,
        "anonymous",
    )
    summary = sampler.summaries()[0]
    assert summary["examples_different"] == 1
    assert odd in summary["example_urls"]
    assert summary["pages_sampled"] == 5


def test_mixed_routes_are_rejected_after_twelve_examples() -> None:
    sampler = RouteSampler()
    admitted = sampler.offer(_links("items", 60), "anonymous")
    alternate: dict[str, int] = {}

    def features(url: str) -> dict:
        alternate.setdefault(url, len(alternate) % 2)
        return PRODUCT if alternate[url] else {**PRODUCT, "layout": list(range(200))}

    returned = _visit_all(sampler, admitted, features, "anonymous")
    phase = _phase(sampler, "anonymous")
    assert phase["status"] == "rejected"
    assert len(phase["samples"]) == 12
    sampled = {item["url"] for item in phase["samples"]}
    assert len([item for item in returned if item["url"] not in sampled]) == 48


def test_action_routes_are_not_grouped() -> None:
    sampler = RouteSampler()
    items = _links("products", 10)
    items[0]["url"] = "https://shop.test/products/delete"
    admitted = sampler.offer(items, "anonymous")
    assert items[0] in admitted


def test_admin_pages_group_but_action_pages_do_not_merge() -> None:
    sampler = RouteSampler()
    admin_products = [
        {
            "url": f"https://shop.test/admin/products/cases-model-{index}-black",
            "depth": 2,
            "parent_id": 1,
            "incoming_action": {},
        }
        for index in range(40)
    ]
    forms = [
        {
            "url": f"https://shop.test/admin/{kind}/new",
            "depth": 2,
            "parent_id": 1,
            "incoming_action": {},
        }
        for kind in ("products", "orders", "promos", "users", "reviews", "pages")
        + ("customers", "coupons", "banners", "settings-x", "regions", "taxes")
    ]
    admitted = sampler.offer(admin_products + forms, "admin")
    assert "https://shop.test/admin/products/{value}" in sampler.groups
    assert all(item in admitted for item in forms)
    assert len([item for item in admitted if item in admin_products]) == 3


def test_record_actions_group_by_id_only() -> None:
    assert "https://shop.test/orders/{value}/edit" in _candidate_keys(
        "https://shop.test/orders/12/edit"
    )
    assert _candidate_keys("https://shop.test/admin/products/new") == []
    assert _candidate_keys("https://shop.test/products/delete") == []


def test_product_id_query_links_share_a_route_without_merging_actions() -> None:
    sampler = RouteSampler()
    links = _links("products", 10)
    for index, item in enumerate(links):
        item["url"] = f"https://shop.test/product?id={index}"
    assert len(sampler.offer(links, "anonymous")) == 3
    assert next(iter(sampler.groups)) == "https://shop.test/product?id={value}"


def test_links_already_queued_are_not_chosen_as_examples() -> None:
    sampler = RouteSampler()
    links = _links("products", 40)
    queued = {item["url"] for item in links[:4]}
    admitted = sampler.offer(links, "anonymous", lambda url: url in queued)
    examples = [item for item in admitted if item["url"] not in queued]
    assert len(examples) == 3
    _visit_all(sampler, examples, lambda _url: PRODUCT, "anonymous")
    assert sampler.summaries()[0]["links_seen"] == 40
    assert _phase(sampler, "anonymous")["status"] == "confirmed"


def test_drain_releases_held_links_when_an_example_is_skipped() -> None:
    sampler = RouteSampler()
    admitted = sampler.offer(_links("products", 40), "anonymous")
    for item in admitted[1:]:
        sampler.observe(item["url"], PRODUCT, "anonymous")
    later = sampler.offer(_links("products", 20, start=100), "anonymous")
    assert later == []
    released = sampler.drain("anonymous")
    assert len(released) == 57
    assert sampler.drain("anonymous") == []
    assert len(sampler.offer(_links("products", 5, start=500), "anonymous")) == 5


def test_second_account_confirms_with_three_links_and_holds_nothing() -> None:
    sampler = RouteSampler()
    first = sampler.offer(_links("products", 40), "anonymous")
    _visit_all(sampler, first, lambda _url: PRODUCT, "anonymous")

    second = sampler.offer(_links("products", 3), "member")
    assert len(second) == 3
    _visit_all(sampler, second, lambda _url: PRODUCT, "member")
    assert _phase(sampler, "member")["status"] == "confirmed"
    assert sampler.offer(_links("products", 50, start=1000), "member") == []
    assert sampler.drain("member") == []


def test_second_account_waits_for_more_links_instead_of_rejecting() -> None:
    sampler = RouteSampler()
    first = sampler.offer(_links("products", 40), "anonymous")
    _visit_all(sampler, first, lambda _url: PRODUCT, "anonymous")

    one = sampler.offer(_links("products", 1, start=1000), "member")
    _visit_all(sampler, one, lambda _url: PRODUCT, "member")
    assert _phase(sampler, "member")["status"] == "candidate"
    more = sampler.offer(_links("products", 10, start=2000), "member")
    assert len(more) == 2
    _visit_all(sampler, more, lambda _url: PRODUCT, "member")
    assert _phase(sampler, "member")["status"] == "confirmed"


def test_second_account_reuses_examples_and_may_see_a_different_page() -> None:
    sampler = RouteSampler()
    links = _links("products", 20)
    first = sampler.offer(links, "anonymous")
    _visit_all(sampler, first, lambda _url: PRODUCT, "anonymous")
    anonymous_examples = set(sampler.summaries()[0]["example_urls"])

    second = sampler.offer(links, "member")
    assert len(second) == 3
    assert {item["url"] for item in second} <= anonymous_examples
    member_product = {**PRODUCT, "layout": list(range(1100, 1300))}
    _visit_all(sampler, second, lambda _url: member_product, "member")
    assert _phase(sampler, "member")["status"] == "confirmed"


def test_one_account_rejection_does_not_discard_another_accounts_samples() -> None:
    sampler = RouteSampler()
    links = _links("products", 10)
    first = sampler.offer(links, "anonymous")
    second = sampler.offer(links, "member")
    _visit_all(sampler, first, _page, "anonymous")
    _visit_all(sampler, second, lambda _url: PRODUCT, "member")
    assert sampler.summaries()[0]["pages_sampled"] == 5


def test_siblings_are_counted_across_pages() -> None:
    sampler = RouteSampler()
    admitted = []
    for page in range(5):
        admitted.extend(sampler.offer(_links("products", 4, start=page * 4), "anon"))
    assert len(admitted) == 8 + 3
    assert len(sampler.groups) == 1


def test_failed_example_is_replaced() -> None:
    sampler = RouteSampler()
    first = sampler.offer(_links("products", 40), "anonymous")
    failed_url = first[0]["url"]
    _visit_all(
        sampler,
        first,
        lambda url: None if url == failed_url else PRODUCT,
        "anonymous",
    )
    summary = sampler.summaries()[0]
    assert summary["pages_sampled"] == 5
    assert failed_url not in summary["example_urls"]


def test_login_blocked_example_rejects_the_route() -> None:
    sampler = RouteSampler()
    first = sampler.offer(_links("products", 40), "anonymous")
    blocked_url = first[1]["url"]
    released = _visit_all(
        sampler,
        first,
        lambda url: {"kind": "blocked"} if url == blocked_url else PRODUCT,
        "anonymous",
    )
    assert len(released) == 37
    assert sampler.summaries() == []


def test_known_template_confirms_a_new_section_from_one_article() -> None:
    sampler = RouteSampler()
    article = {**PRODUCT, "kind": "article"}

    def section(name: str, count: int) -> list[dict]:
        return [
            {
                "url": f"https://news.test/{name}/{1000 + index}/story-about-thing-{index}",
                "depth": 1,
                "parent_id": 1,
                "incoming_action": {},
            }
            for index in range(count)
        ]

    tech = sampler.offer(section("tech", 12), "anonymous")
    _visit_all(sampler, tech, lambda _url: article, "anonymous")
    assert sampler.summaries()[0]["label"] == "Articles"

    games = sampler.offer(section("games", 2), "anonymous")
    assert len(games) == 1
    _visit_all(sampler, games, lambda _url: article, "anonymous")
    key = "https://news.test/games/{value}/{value}"
    assert _phase(sampler, "anonymous", key)["status"] == "confirmed"
    assert sampler.offer(section("games", 40)[2:], "anonymous") == []

    other = sampler.offer(section("tv", 12), "anonymous")
    assert len(other) == 1
    returned = _visit_all(sampler, other, _page, "anonymous")
    assert len(returned) == 2 + 9
    assert sampler.groups["https://news.test/tv/{value}/{value}"]["status"] == (
        "rejected"
    )


def test_snapshot_saves_status_changes_now_and_counts_later() -> None:
    sampler = RouteSampler()
    sampler.offer(_links("products", 40), "anonymous")
    assert sampler.take_snapshot(now=100.0) is not None
    sampler.offer(_links("products", 5, start=100), "anonymous")
    assert sampler.take_snapshot(now=101.0) is None
    assert sampler.take_snapshot(now=106.0) is not None
    sampler.offer(_links("products", 5, start=200), "anonymous")
    assert sampler.take_snapshot(now=107.0, force=True) is not None
    assert sampler.take_snapshot(now=200.0, force=True) is None


def test_resumed_state_keeps_link_counts_without_double_counting() -> None:
    sampler = RouteSampler()
    links = _links("products", 40)
    first = sampler.offer(links, "anonymous")
    _visit_all(sampler, first, lambda _url: PRODUCT, "anonymous")
    resumed = RouteSampler(sampler.snapshot())
    resumed.offer(links + _links("products", 10, start=40), "anonymous")
    assert resumed.summaries()[0]["links_seen"] == 50


def test_paused_crawl_resumes_with_examples_still_to_visit() -> None:
    sampler = RouteSampler()
    sampler.offer(_links("products", 40), "anonymous")
    resumed = RouteSampler(sampler.snapshot())
    examples = resumed.resume_items("anonymous")
    assert len(examples) == 3
    _visit_all(resumed, examples, lambda _url: PRODUCT, "anonymous")
    assert resumed.summaries()[0]["pages_sampled"] == 5


@pytest.mark.parametrize(
    ("url", "key"),
    [
        (
            "https://www.newegg.com/sapphire-pulse-radeon-rx-9060-xt/p/N82E16814202457",
            "https://www.newegg.com/{value}/p/{value}",
        ),
        (
            "https://www.newegg.com/GPUs-Video-Graphics-Cards/SubCategory/ID-48",
            "https://www.newegg.com/{value}/SubCategory/{value}",
        ),
        (
            "https://www.amazon.com.au/Palit-RTX-5060-Infinity/dp/B0FXRGCMBG/ref=sr_1_5"
            "?dib=abc&dib_tag=se&keywords=graphics+card&qid=1&sr=8-5",
            "https://www.amazon.com.au/{value}/dp/{value}/{value}",
        ),
        (
            "https://www.amazon.com.au/dp/B0FXRGCMBG",
            "https://www.amazon.com.au/dp/{value}",
        ),
        (
            "https://www.theverge.com/tech/1009324/how-apple-can-win-the-smart-home",
            "https://www.theverge.com/tech/{value}/{value}",
        ),
        (
            "https://www.theverge.com/2024/10/23/24277962/character-ai-lawsuit",
            "https://www.theverge.com/{value}/{value}/{value}/{value}/{value}",
        ),
        (
            "https://www.afr.com/politics/federal/pm-rallies-colleagues-20261013-p614yu",
            "https://www.afr.com/politics/federal/{value}",
        ),
        ("https://blog.test/?p=123", "https://blog.test/?p={value}"),
        ("https://news.test/archive?page=7", "https://news.test/archive?page={value}"),
    ],
)
def test_real_site_url_shapes_have_a_route(url: str, key: str) -> None:
    assert key in _candidate_keys(url)


def test_query_strings_and_fragments_do_not_create_new_route_members() -> None:
    product = "https://www.example.test/card/p/N82E16814202457"
    key = "https://www.example.test/{value}/p/{value}"
    for variant in (
        "#IsFeedbackTab",
        "?cm_sp=Head-_-Nav&icid=1",
        "?any_tracking_name=xyz",
        "?sort=price&page=2",
    ):
        assert _member_identity(product + variant, key) == _member_identity(
            product, key
        )
    assert _member_identity("https://app.test/a/#/orders", key) != _member_identity(
        "https://app.test/a/", key
    )
    query_key = "https://blog.test/?p={value}"
    assert _member_identity("https://blog.test/?p=1", query_key) != _member_identity(
        "https://blog.test/?p=2", query_key
    )


def test_route_members_are_counted_once_across_tracking_variants() -> None:
    sampler = RouteSampler()
    links = []
    for index in range(12):
        for ref in ("a", "b", "c"):
            links.append(
                {
                    "url": f"https://shop.test/items/item-{index}?from_listing={ref}",
                    "depth": 1,
                    "parent_id": 1,
                    "incoming_action": {},
                }
            )
    admitted = sampler.offer(links, "anonymous")
    assert len(admitted) == 3
    assert len({_member_identity(i["url"], "x") for i in admitted}) == 3
    _visit_all(sampler, admitted, lambda _url: PRODUCT, "anonymous")
    assert sampler.summaries()[0]["links_seen"] == 12


def test_single_top_level_pages_are_not_grouped() -> None:
    assert _candidate_keys("https://shop.test/about") == []
    assert _candidate_keys("https://shop.test/very-long-landing-page-name") == []


@pytest.mark.parametrize("site", sorted(REAL_SITES))
def test_real_site_pages_from_one_template_group_together(site: str) -> None:
    """Layouts captured from real sites with page_features in Chromium."""
    same = REAL_SITES[site]["same"]
    other = REAL_SITES[site]["other"]
    medoid, members, cutoff = _cluster(same)
    assert len(members) >= 0.75 * len(same)
    template = same[medoid]
    for page in other:
        assert page_similarity(template, page) < cutoff, page["url"]


def test_real_site_odd_product_template_is_reported_as_different() -> None:
    same = REAL_SITES["mwave"]["same"]
    _medoid, members, _cutoff = _cluster(same)
    odd = [page["url"] for index, page in enumerate(same) if index not in members]
    assert odd == ["https://www.mwave.com.au/products/intel-12th-13th-gen-nuc"]


def test_large_layouts_are_compared_from_a_fixed_size_sketch() -> None:
    def sketch(values: set[int]) -> dict:
        hashed = sorted(
            int(hashlib.sha256(str(value).encode()).hexdigest()[:8], 16)
            for value in values
        )
        return {
            "kind": "page",
            "layout": hashed[:LAYOUT_SKETCH_SIZE],
            "size": len(hashed),
        }

    first = sketch(set(range(0, 2000)))
    second = sketch(set(range(500, 2500)))
    assert abs(page_similarity(first, second) - 0.6) < 0.1
    assert page_similarity(first, first) == 1.0


def test_empty_and_blocked_pages_are_not_similar_to_real_pages() -> None:
    empty = {"kind": "page", "layout": [], "size": 0}
    assert page_similarity(empty, empty) == 0.0
    assert page_similarity({"kind": "blocked"}, {"kind": "blocked"}) == 1.0
    assert page_similarity({"kind": "blocked"}, PRODUCT) == 0.0


def test_page_features_keeps_a_bounded_layout_sketch() -> None:
    class FakePage:
        url = "https://shop.test/p/1"

        async def evaluate(self, _script: str) -> dict:
            return {"kind": "article", "layout": list(range(400)) + ["x"], "size": 400}

    features = asyncio.run(page_features(FakePage()))
    assert features["kind"] == "article"
    assert len(features["layout"]) == LAYOUT_SKETCH_SIZE
    assert features["size"] == 400


ROOT = "https://shop.test/"
PRODUCTS = 40_000


def _site_links(url: str) -> list[str]:
    path = url.removeprefix("https://shop.test")
    if path == "/":
        return (
            [f"{ROOT}collections/c{index}" for index in range(20)]
            + [f"{ROOT}products/p{index}" for index in range(4)]
            + [f"{ROOT}checkout", f"{ROOT}account/orders", f"{ROOT}about"]
        )
    if path.startswith("/collections/c"):
        start = int(path.removeprefix("/collections/c")) * 2_000
        return [f"{ROOT}products/p{start + index}" for index in range(24)]
    if path.startswith("/products/p"):
        number = int(path.removeprefix("/products/p"))
        return [
            f"{ROOT}products/p{(number * 7 + step) % PRODUCTS}" for step in range(1, 5)
        ] + [f"{ROOT}cart"]
    if path == "/account/orders":
        return [f"{ROOT}account/orders/{index}" for index in range(30)]
    return []


def _site_features(url: str) -> dict:
    return PRODUCT if "/products/" in url else _page(url)


def _simulate_crawl(
    sampler: RouteSampler,
    phase: str,
    crawled: set[str],
    max_pages: int = 500,
    links=None,
    features=None,
    root: str = ROOT,
) -> list[str]:
    """Drive the sampler with the crawler's queue rules for one account."""
    links = links or _site_links
    features = features or _site_features
    queue: deque[tuple[str, int]] = deque([(root, 0)])
    queued = {root}
    visits = []

    def is_queued(url: str) -> bool:
        return url in queued

    def enqueue(items: list[dict]) -> None:
        for item in items:
            if item["url"] not in queued:
                queued.add(item["url"])
                queue.append((item["url"], item["depth"]))

    enqueue(sampler.resume_items(phase))
    while True:
        if not queue:
            enqueue(sampler.drain(phase))
        if not queue:
            break
        url, depth = queue.popleft()
        if url not in crawled:
            if len(crawled) >= max_pages:
                continue
            crawled.add(url)
        visits.append(url)
        if sampler.wants_observation(url, phase):
            enqueue(sampler.observe(url, features(url), phase, is_queued))
        if depth < 4:
            items = [
                {
                    "url": link,
                    "depth": depth + 1,
                    "parent_id": None,
                    "incoming_action": {},
                }
                for link in links(url)
            ]
            enqueue(sampler.offer(items, phase, is_queued))
    return visits


def test_large_catalogue_crawl_stays_small_and_reaches_other_sections() -> None:
    sampler = RouteSampler()
    crawled: set[str] = set()
    anonymous = _simulate_crawl(sampler, "anonymous", crawled)
    member = _simulate_crawl(sampler, "member", crawled)

    for visits in (anonymous, member):
        products = [url for url in visits if "/products/" in url]
        assert len(products) <= 20
        assert f"{ROOT}checkout" in visits
        assert f"{ROOT}account/orders/29" in visits
        assert all(f"{ROOT}collections/c{index}" in visits for index in range(20))
    assert len(crawled) < 120

    product_group = sampler.groups["https://shop.test/products/{value}"]
    assert product_group["status"] == "confirmed"
    assert {phase["status"] for phase in product_group["phases"].values()} == {
        "confirmed"
    }
    summary = next(
        item
        for item in sampler.summaries()
        if item["route_pattern"] == "https://shop.test/products/{value}"
    )
    assert summary["links_seen"] >= 480
    for group in sampler.groups.values():
        for phase in group["phases"].values():
            assert not (phase["status"] == "candidate" and phase["pending"])


NEWS = "https://news.test/"
SECTIONS = [
    f"desk-{chr(97 + index // 26)}{chr(97 + index % 26)}" for index in range(30)
]
ARTICLE = {"kind": "article", "layout": list(range(3000, 3200)), "size": 200}
LISTING = {"kind": "page", "layout": list(range(3100, 3300)), "size": 200}


def _news_links(url: str) -> list[str]:
    path = url.removeprefix("https://news.test")

    def article(section: str, number: int) -> str:
        return f"{NEWS}{section}/{number}/headline-about-story-{number}"

    if path == "/":
        return [f"{NEWS}{s}" for s in SECTIONS] + [
            article(s, n) for s in SECTIONS for n in range(3)
        ]
    parts = path.strip("/").split("/")
    if len(parts) == 1 and parts[0] in SECTIONS:
        return [article(parts[0], n) for n in range(20)] + [
            f"{NEWS}{parts[0]}?page={page}" for page in range(2, 6)
        ]
    if len(parts) == 3:
        number = int(parts[1])
        return [article(parts[0], (number * 7 + step) % 300) for step in range(1, 6)]
    return []


def _news_features(url: str) -> dict:
    parts = url.removeprefix(NEWS).split("?")[0].strip("/").split("/")
    return ARTICLE if len(parts) == 3 else LISTING


def test_news_site_visits_a_few_articles_per_section_not_the_archive() -> None:
    sampler = RouteSampler()
    visits = _simulate_crawl(
        sampler,
        "anonymous",
        set(),
        links=_news_links,
        features=_news_features,
        root=NEWS,
    )
    articles = [url for url in visits if url.count("/") == 5]
    sections = [url for url in visits if url.rstrip("/").count("/") == 3]
    assert len(articles) <= 2 * len(SECTIONS) + CONFIRMED_LEAD_EXAMPLES
    assert len(sections) >= len(SECTIONS)
    pagination = [url for url in visits if "?page=" in url]
    assert len(pagination) <= 2 * len(SECTIONS)
    confirmed = [s for s in sampler.summaries() if s["label"] == "Articles"]
    assert len(confirmed) == len(SECTIONS)
    for group in sampler.groups.values():
        for phase in group["phases"].values():
            assert not (phase["status"] == "candidate" and phase["pending"])


CONFIRMED_LEAD_EXAMPLES = 5
