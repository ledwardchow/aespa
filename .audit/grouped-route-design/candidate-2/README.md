# Grouped-route design candidate 2

## Usage (caller first)

The crawler records every eligible raw DOM link before the route sampler decides which links to visit. It does this in bounded batches, without the current `raw_links[:300]` intelligence cap. A link's presence under Alice's session means Alice saw a link, not that Alice owns the target or fetched it successfully.

```python
catalog = TargetCatalog(session_factory)
source = DiscoverySource(run_id=run_id, page_id=page_id, state_key=state_key,
                         credential_id=credential_id, kind="dom_link")
for batch in batches(same_domain_links, 200):
    catalog.record_discoveries(source, [DiscoveredLink(url=url, text=text) for url, text in batch])
admitted = sampler.offer(link_items, phase_key, route_is_queued)
```

The crawl and scan record direct fetch results against the exact target and actor. They keep response evidence separate from discovery. The projection for a route can display access observations, but it never compares text from different concrete URLs to decide that anonymous and signed-in content is equivalent.

```python
catalog.record_fetch(FetchObservation(run_id=run_id, url=final_url, state_key=state_key,
    credential_id=credential_id, page_id=page_id, traffic_id=traffic_id,
    result="reached", content_fingerprint=body_digest))
page = catalog.targets(run_id, after_id=cursor, limit=100)
cursor = page.next_after_id
```

At scan start, the planner selects a small set of object/identity checks from concrete positive baselines. The scanner's existing request policy still checks scope and safety immediately before sending each request. A discovered URL by itself never enters the completion denominator.

```python
selection = catalog.select_idor_tests(run_id, active_credential_ids=set(cred_sessions),
                                       max_targets=80, max_other_actors=3)
for test in selection:
    result = await fetch_with_existing_policy(test.url, test.other_credential_id)
    catalog.record_selected_result(test.obligation_id, result.to_evidence())
```

Specialists claim an exact target, attack class, parameter, browser state, and actor scope. The evidence token identifies a persisted observation or traffic row, not free-form rationale. Repeated dispatch with the same evidence returns `duplicate`; a terminal handoff can reopen only when new evidence is supplied. An active handoff for the same exact scope remains exclusive.

```python
claim = claim_specialist_handoff(session_factory, run_id=run_id, run_kind="web",
    scope=SpecialistScope(attack_class="idor", url="https://site/orders?id=202",
        state_key=None, parameter="id", actor_ids=(alice_id, bob_id)),
    evidence=EvidenceToken(source="traffic", source_id=traffic_id))
if claim.status == "created":
    queue_specialist(claim.handoff_id)
```

`sketch.py` contains the matching type and signature sketch. `rationale.md` compares this design with a structurally different fact-journal design and records the chosen shape. No production code or database was changed.
