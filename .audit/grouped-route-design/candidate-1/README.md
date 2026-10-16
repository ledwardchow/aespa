# Candidate 1 - durable exact targets

The caller records links before asking the sampler which pages to visit. A target is an exact observed URL plus its browser state key. It is inventory, not a crawled page or a coverage test. The scanner reads it in pages and chooses a few targets when evidence supports a test.

```python
from aespa.services.discovered_targets import (
    DiscoveredLink, TargetQuery, record_links, list_targets,
)

# crawler.py, after extracting DOM links and before RouteSampler.offer
targets = record_links(
    run_id=run_id,
    links=[
        DiscoveredLink(
            exact_url=link["href"], source_page_id=page_id,
            source_state_key=state_key, credential_id=credential_id,
            link_text=link["text"],
        )
        for link in raw_links if _same_domain(link["href"], base_netloc)
    ],
)
admitted = shared.route_sampler.offer(link_items, phase_key, route_is_queued)
# targets includes held links. Neither this call nor the sampler seeds coverage.
```

```python
# scanner.py target_inventory tool, with a stable cursor instead of a 1,000-row prefetch
page = list_targets(run_id, TargetQuery(search=args.get("search"),
                                        route=args.get("route"),
                                        credential_id=args.get("credential_id"),
                                        source=args.get("source"),
                                        source_page_id=args.get("page_id"),
                                        limit=limit, cursor=args.get("cursor")))
return {"tool": "target_inventory", "items": page.items,
        "next_cursor": page.next_cursor}
```

```python
from aespa.services.discovered_targets import IdorBudget, select_idor_probes

# scanner.py deterministic IDOR setup. This returns a small number of exact URLs.
probes = select_idor_probes(run_id, IdorBudget(total=80, per_route=4,
                                                identity_pairs_per_route=2))
for probe in probes:
    result = await _fetch_matrix_url(run_id, probe.target.exact_url,
                                     session=cred_sessions[probe.test_credential_id],
                                     site_id=site_id)
    # Compare this response only with probe.positive_baseline for this exact target.
    # A finding needs separate entitlement evidence; an unobserved identity is unknown.
```

```python
from aespa.services.specialist_handoffs import claim_handoff, EvidenceRef, Scope

# scanner.py specialist dispatch. The traffic row or lead id is stable across retries.
claim = claim_handoff(run_id=run_id, run_kind="web",
    scope=Scope(attack_class="idor", exact_url=target_url, state_key=None,
                method="GET", parameter="id", session_label="alice"),
    evidence=EvidenceRef(kind="traffic", id=traffic_id),
    agent_id=agent_id, rationale=rationale, priority=priority)
if claim.created:
    enqueue_specialist(claim.handoff_id)
```

The inventory endpoint applies the site's scope filter when listing candidates and the request path checks scope again. It never turns discovery into permission to request a URL. A URL with repeated query keys, empty values, a different query value, or a meaningful browser fragment remains distinct. The display route can group those targets without changing their IDs.

The implementation keeps `CrawledPage` for visited or replayed pages. HTTP probes of a discovered URL link to the target and their traffic record. They do not create a synthetic `CrawledPage` or mark another object's page cell complete.
