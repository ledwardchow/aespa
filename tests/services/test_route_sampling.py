from __future__ import annotations

import asyncio
from collections import deque

from aespa.services.route_sampling import (
    RouteSampler,
    features_match,
    page_features,
)

PRODUCT = {
    "kind": "product",
    "forms": [
        {"method": "POST", "fields": ["input:id:hidden", "input:quantity:number"]}
    ],
    "actions": ["add to cart"],
    "requests": ["GET /api/products/{value}"],
    "text": None,
}


def _page(name: str) -> dict:
    return {"kind": "page", "forms": [], "actions": [], "requests": [], "text": name}


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


def _phase(sampler: RouteSampler, phase: str) -> dict:
    return next(iter(sampler.groups.values()))["phases"][phase]


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
    assert RouteSampler(sampler.snapshot()).summaries() == sampler.summaries()


def test_different_feature_pages_release_held_links() -> None:
    sampler = RouteSampler()
    admitted = sampler.offer(_links("features", 10), "anonymous")
    assert len(admitted) == 3
    released = _visit_all(sampler, admitted, lambda url: _page(url), "anonymous")
    assert len(released) == 7
    assert sampler.summaries() == []
    # Later links to a rejected route are crawled normally.
    assert len(sampler.offer(_links("features", 5, start=50), "anonymous")) == 5


def test_action_routes_are_not_grouped() -> None:
    sampler = RouteSampler()
    items = _links("products", 10)
    items[0]["url"] = "https://shop.test/products/delete"
    admitted = sampler.offer(items, "anonymous")
    assert items[0] in admitted


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


def test_second_account_reuses_examples_and_releases_different_pages() -> None:
    sampler = RouteSampler()
    links = _links("products", 20)
    first = sampler.offer(links, "anonymous")
    _visit_all(sampler, first, lambda _url: PRODUCT, "anonymous")
    anonymous_examples = set(sampler.summaries()[0]["example_urls"])

    second = sampler.offer(links, "member")
    assert len(second) == 3
    assert {item["url"] for item in second} <= anonymous_examples
    member_product = {**PRODUCT, "actions": ["add to cart", "add to wishlist"]}
    released = _visit_all(sampler, second, lambda _url: member_product, "member")
    assert len(released) == 17
    assert _phase(sampler, "member")["status"] == "rejected"
    assert sampler.summaries()[0]["pages_sampled"] == 5


def test_one_account_rejection_does_not_discard_another_accounts_samples() -> None:
    sampler = RouteSampler()
    links = _links("products", 10)
    first = sampler.offer(links, "anonymous")
    second = sampler.offer(links, "member")
    _visit_all(sampler, first, lambda url: _page(url), "anonymous")
    _visit_all(sampler, second, lambda _url: PRODUCT, "member")
    assert sampler.summaries()[0]["pages_sampled"] == 5


def test_siblings_are_counted_across_pages() -> None:
    sampler = RouteSampler()
    admitted = []
    for page in range(5):
        admitted.extend(sampler.offer(_links("products", 4, start=page * 4), "anon"))
    # Two pages of four related links are crawled normally. The third page
    # reaches ten siblings, and from then on only examples are admitted.
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


def test_product_features_ignore_size_buttons_but_keep_actions() -> None:
    class FakePage:
        def __init__(self, url: str, product: bool, heading: str, controls) -> None:
            self.url = url
            self.product = product
            self.heading = heading
            self.controls = controls

        async def evaluate(self, _script: str) -> dict:
            return {
                "controls": self.controls,
                "links": [],
                "forms": [],
                "product": self.product,
                "heading": self.heading,
                "mainText": self.heading,
            }

    def features(page: FakePage) -> dict:
        return asyncio.run(page_features(page))

    shirt = FakePage(
        "https://shop.test/products/a", True, "Shirt", ["s", "m", "add to cart"]
    )
    shoe = FakePage(
        "https://shop.test/products/b",
        True,
        "Shoe",
        ["7", "8", "9", "add to cart - $20"],
    )
    assert features_match(features(shirt), features(shoe))
    sold_out = FakePage("https://shop.test/products/c", True, "Hat", ["notify me"])
    assert not features_match(features(shirt), features(sold_out))
    shirt.product = shoe.product = False
    assert not features_match(features(shirt), features(shoe))


def test_request_patterns_allow_small_differences() -> None:
    base = {**PRODUCT, "requests": [f"GET /api/r{index}" for index in range(10)]}
    close = {**PRODUCT, "requests": [f"GET /api/r{index}" for index in range(9)]}
    far = {**PRODUCT, "requests": [f"GET /api/r{index}" for index in range(5)]}
    assert features_match(base, close)
    assert not features_match(base, far)


# ── Crawl simulation ─────────────────────────────────────────────────────────

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
    sampler: RouteSampler, phase: str, crawled: set[str], max_pages: int = 500
) -> list[str]:
    """Drive the sampler with the crawler's queue rules for one account."""
    queue: deque[tuple[str, int]] = deque([(ROOT, 0)])
    queued = {ROOT}
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
            enqueue(sampler.observe(url, _site_features(url), phase, is_queued))
        if depth < 4:
            items = [
                {
                    "url": link,
                    "depth": depth + 1,
                    "parent_id": None,
                    "incoming_action": {},
                }
                for link in _site_links(url)
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
    assert summary["links_seen"] > 500
    for group in sampler.groups.values():
        for phase in group["phases"].values():
            assert not (phase["status"] == "candidate" and phase["pending"])


def test_paused_crawl_resumes_with_examples_still_to_visit() -> None:
    sampler = RouteSampler()
    sampler.offer(_links("products", 40), "anonymous")
    resumed = RouteSampler(sampler.snapshot())
    examples = resumed.resume_items("anonymous")
    assert len(examples) == 3
    _visit_all(resumed, examples, lambda _url: PRODUCT, "anonymous")
    assert resumed.summaries()[0]["pages_sampled"] == 5
