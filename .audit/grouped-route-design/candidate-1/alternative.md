# Candidate 2 - typed intelligence facts and a read projection

## Caller usage first

This option makes `TargetIntelItem` an append-only fact log for exact targets and actor observations. The scanner reconstructs a target view from those facts. It avoids a new target table, but requires stronger structure in the existing table.

```python
# crawler.py, before RouteSampler.offer and without raw_links[:300]
intel.record_target_facts(run_id, source_page_id=page_id,
    source_state_key=state_key, credential_id=credential_id,
    links=raw_links)
admitted = shared.route_sampler.offer(link_items, phase_key, route_is_queued)

# scanner.py target_inventory. SQL applies filters before keyset paging.
page = intel.list_exact_targets(run_id, search=search, route=route,
                                credential_id=credential_id,
                                after_fact_id=cursor, limit=limit)

# scanner.py IDOR. Returned rows carry exact URL and a positive same-URL response.
for candidate in intel.select_idor_targets(run_id, total=80,
                                            per_route=4, actor_pairs=2):
    await test_same_object(candidate)
```

The signatures are `record_target_facts(run_id: int, *, source_page_id: int, source_state_key: str | None, credential_id: int | None, links: list[dict]) -> None`, `list_exact_targets(run_id: int, *, search: str | None, route: str | None, credential_id: int | None, after_fact_id: int | None, limit: int) -> TargetPage`, and `select_idor_targets(run_id: int, *, total: int, per_route: int, actor_pairs: int) -> list[IdorProbe]`. The `TargetPage` and `IdorProbe` contracts have the same meaning as candidate 1. Probe outcome, scope, and coverage calls use the shared signatures in `design.py`.

## Data shape and ownership

Extend `TargetIntelItem` with `exact_target_url TEXT`, `target_state_key`, `source_state_key`, `credential_id`, `traffic_id`, `fact_key`, and `fact_type`. `fact_type` is one of `target_link`, `target_response`, or the legacy intelligence types. `exact_target_url` stores the full observed URL and is never passed through the current 2,000-character `value` truncation. A `target_link` fact is one `(run, URL, target state, source page/state, actor)` observation. A `target_response` fact is one `(run, URL, target state, actor, source event)` response with a status class and evidence pointer. `fact_key` is a stable digest of the full tuple and has a run-scoped unique constraint. A second unique index on `(run, fact_type, traffic_id)` handles retried response events. Unknown actors and anonymous actors need distinct values, not both SQL NULL. `TargetIntelItem` remains the only writer of these facts; recon, archive, and the lead read through one projection function.

The projection groups rows by exact URL and state key, then joins source and response facts. It emits route summaries separately, with per-object/per-actor observed access and `unknown` where evidence is missing. It never compares response text from different object URLs. Query strings retain byte order, duplicate keys, and empty values; browser state keys distinguish same-URL interactive views. The sampler changes `_member_identity` to full identity for every candidate key, but still controls only browser admission. No fact is dropped because it was held.

## Work and outcome behavior

`CrawledPage` remains visited pages. The scanner can page through the projected target list and send any selected in-scope URL to its existing request tools. The request dispatcher checks scope again. Candidate selection spends fixed total, route, and actor-pair budgets. A discovered-only URL needs a positive request baseline before any cross-account comparison. A link from Alice gives no ownership claim. Confirmed IDOR needs separate entitlement evidence; otherwise the result is inconclusive. This applies to deterministic and lead-driven checks.

Coverage remains over persisted page cells and selected route obligations, not all target facts. Grouped UI rows show unresolved child counts and a partial state. Both Standard completion call sites read raw progress from one function. An on-demand object probe attaches its full URL and fact ID to `ProbeExecution`/`TrafficEntry`; it may satisfy its selected route obligation, but does not close another object's page cell. `resolve_web_page_id` accepts only an exact URL and state match for evidence attribution. Remove its path-only and normalized route fallbacks for coverage and findings. Browser visits still create real pages.

Specialist handoffs use candidate 1's exact `Scope` and `EvidenceRef` contract, with a v2 migration and attempt-level uniqueness. Active conflict is exact scope; a terminal same-evidence retry is duplicate, and a new durable event reopens. Per-operation queue limits control fan-out. The `run_kind` field is mandatory in every lookup. No existing broad legacy fingerprint may suppress v2 work.

## Persistence, archive, and concurrency

Alembic adds the new `TargetIntelItem` columns and indexes. The existing `_save_intel_item` can keep its behavior for old intelligence kinds, but `record_target_facts` must use batch insert-on-conflict and never call the check-then-insert path or truncate exact URL. This means two write paths within one model. SQLite uniqueness makes resumed and concurrent crawling idempotent; each source/actor fact is independent, so workers do not edit one shared JSON snapshot. For long URLs, use `exact_target_url TEXT` plus a digest index and verify the full URL on digest collision. Never deduplicate by path or route template.

Archive export includes the typed target facts and their source page URL/state, actor username, and traffic identity. Import remaps page, actor, and traffic IDs before computing new `fact_key` values. Old archives retain only the facts actually saved, and imports cannot recreate dropped links. In-place backfill uses persisted page, intel, and traffic URLs without inventing access outcomes. The archive version increments. Handoffs migrate as described for candidate 1, including exact rekeying of active legacy rows.

## Checks and tradeoff

Tests use 200 held URLs, a link beyond position 300, query-only object variants, duplicate and empty query keys, two same-URL interactive states, two actor observations, a concurrent retry, and an archive import with remapped IDs. Standard stays below 100% for one covered and one untouched page cell. An on-demand `/orders/202` probe never closes `/orders/101`. Search after the first 1,000 facts returns later matches through a cursor.

This option accepts fewer new tables in exchange for a larger, more specialized `TargetIntelItem` and a nontrivial read projection. Its public interface is still small, but the fact table carries target identity, provenance, response state, and unrelated intelligence. It lost to candidate 1 because changes to target rules would affect more existing writers and archive paths, and the current truncation and missing uniqueness make a narrow fix unreliable.
