# Alternative: Enriched TargetIntelItem catalog

## Usage

The crawl service writes target observations through the existing intelligence service. The Test Lead asks that service for pages of exact targets. Selection remains a separate call and does not make every intel row required work.

```python
from aespa.services.target_intel import (
    NavigationTarget,
    TargetIntelFilter,
    page_navigation_targets,
    record_navigation_targets,
)

record_navigation_targets(
    session,
    run_id=run.id,
    observations=[NavigationTarget(
        url="https://shop.test/orders?id=101&view=full",
        source_page_id=page.id,
        source_state_key=page.state_key,
        identity_key="credential:12",
        source="dom_link",
    )],
)
targets = page_navigation_targets(
    session,
    run_id=run.id,
    filter=TargetIntelFilter(),
    after=cursor,
    limit=100,
)
```

## Shape and persistence

`TargetIntelItem` becomes the sole discovery record. `kind="endpoint"` rows represent exact navigation targets, and metadata stores source state, source identity, and target state. Add deterministic `identity_key`, `target_key`, and `source_page_key` columns, plus a database uniqueness constraint on `(test_run_id, target_key, identity_key, source_page_key)`. The table keeps multiple provenance rows while endpoint queries group by target key. Do not store access or ownership on these rows.

The crawler records all same-domain DOM and JS navigation URLs as endpoint intel before it calls `RouteSampler.offer`. This bypasses the current first-300 limit for this kind while leaving other intel kinds unchanged. `_save_intel_item` becomes a batched upsert on the unique key. The target-inventory tool filters and searches in SQL, orders by `(target_key, identity_key, source_page_key)`, and returns an opaque keyset cursor rather than loading 1,000 rows first. Exact URL data uses a new unbounded text column or a dedicated exact-url field; it cannot keep the current 2,000-character value truncation.

Path templates are derived grouping keys only. The target key hashes the exact URL and explicit state key, preserving query order, repeated and blank values, and meaningful fragments. The evidence key retains source page/state and identity. The sampler keeps this exact member key even when it groups candidates using a path-only shape.

Access stays on exact visited pages and credential views. Recon emits reached observations per exact target and identity; absent evidence is unknown. A visible link is not an access or ownership result. Text from distinct exact target keys is never compared. A failed request without an explicit denial status stays unknown.

Only explicit bounded IDOR selection creates object-specific `ScanObligation` rows. Selection requires an in-scope visited object page, a successful positive baseline for an identified credential, and another configured identified session. It chooses at most 80 objects and 3 comparison sessions per object, ordered stably by route and target key. It never requests inventory-only URLs. The existing same-object response evidence and denial checks remain required for a finding. Obligations have an exact target key and unique scope fingerprint, so retries return the same work. Inventory rows and unselected objects never enter completion totals.

Route groups are presentation rows only. Conflicting member statuses show as mixed. Both Standard total reads use raw applicable visited-page cells plus selected object obligations; the target intel query count and group status are not completion evidence. On-demand object leads retain exact URL evidence. `resolve_web_page_id` does not path-fallback for object URLs or create coverage pages for mutated values.

Specialist scope fingerprints keep exact query and fragment strings and include attack class, parameter, and session identity. A separate evidence fingerprint includes the lead ID and revision. Same evidence is idempotent, active handoffs conflict only within the exact active scope, and new evidence can create a new row after an earlier row completes.

`route_sampling.py` always uses the full URL semantics, query and meaningful fragment included, as member identity even when the candidate grouping key is path-only. `recon_summary.py` groups access observations by exact URL/state and credential view, preserving unknown values and never comparing text across different object URLs. `web_workprogram.py` derives display-only route group rows, marks disagreement as mixed, and leaves completion based on raw applicable page cells and explicitly selected obligations.

The selector reads exact endpoint URLs but creates IDOR work only for an exact in-scope `CrawledPage` with a successful positive view under an identified credential. It selects at most 80 objects and 3 comparison identities per object, in stable route/object order, and does not request inventory-only URLs. Missing access remains unknown. Object-specific `ScanObligation` records get exact target keys, baseline/comparison IDs, and a unique scope fingerprint. The same success plus same-object evidence checks remain required for a finding.

Specialist handoffs use query-preserving scope identity and a separate evidence fingerprint. The unique key becomes `(run_kind, run_id, evidence_fingerprint)`; active conflict checks use exact scope only while a handoff is queued or running. New evidence can create a new episode after completion. Legacy rows are backfilled from stored target URLs and do not suppress distinct query targets.

The archive already exports `target_intelligence`; increment the archive version only to encode the new exact target identity and provenance fields. Restore remaps credential usernames, rebuilds keys, tolerates older archives without those fields, and does not recreate targets that were not retained in the source. No data is transformed into visited pages. SQLite upserts make crawler retries and imports idempotent. The migration adds the exact identity/provenance columns and uniqueness constraint, adds exact target and baseline/comparison fields plus a fingerprint to selected obligations, and replaces handoff scope uniqueness with evidence-fingerprint uniqueness. Existing outcomes and archives remain readable.

The `target_intel` module owns extraction normalization, upserts, stable keyset pagination, and the archive form for these rows. `route_sampling.py`, `recon_summary.py`, `web_workprogram.py`, `scanner.py`, and `specialist_handoffs.py` follow the same boundaries and outcome rules as the recommended option. In particular, `resolve_web_page_id` uses exact target identity for object URLs and never promotes evidence to a route-matched representative page. Both Standard completion reads use raw page cells and selected obligations, while UI group rows render disagreements as mixed.

This option has a smaller public surface because the crawler, recon, and inventory tool reuse one model. It loses because target discovery now shares a table and APIs with forms, scripts, response fields, and user-input intelligence. Exact URLs need exceptions around the current key/value truncation and grouping rules, and a developer changing generic intel persistence can silently break the route catalog. It is viable only if those constraints are made explicit in the type and migration contracts.


