# Candidate 3: Exact target catalog with separate evidence and work

## Problem

Grouped crawling deliberately visits only a few similar pages, but the sampler currently also controls which links survive as durable inventory. Route identity also drops query values for path-only groups. Later, recon merges access observations by canonical route, coverage promotes a group to its best status, and specialist handoffs treat terminal work as a permanent duplicate. Those are separate facts with different lifetimes. The design keeps discovered targets, observed access, selected tests, and test results in separate records. A target being discovered never makes it required work.

The current source confirms that `PageLink` records navigation edges only for pages the crawler actually queues, while `_record_page_intelligence` persists only the first 300 raw links and `_save_intel_item` truncates values and uses check-then-insert without a uniqueness constraint. The Test Lead inventory reads at most 1,000 intel rows before filtering and returns no cursor. Those paths cannot serve as a lossless target catalog. `CrawledPage` remains a record of a visited or replayed page.

## Usage (caller's view)

The crawl service records every in-scope same-domain navigation target before the sampler chooses browser work. The catalog stores the exact URL and meaningful interactive state separately from the discovery evidence. The sampler still decides which URLs enter the queue.

```python
from aespa.services.target_catalog import (
    Discovery,
    TargetFilter,
    page_targets,
    record_discoveries,
)
from aespa.services.web_workprogram import select_idor_work

record_discoveries(
    session,
    run_id=run.id,
    discoveries=[
        Discovery(
            url="https://shop.test/orders?id=101&view=full",
            state_key=None,
            source_page_id=page.id,
            source_state_key=page.state_key,
            identity=active_identity,
            source="dom_link",
        ),
    ],
)

page = page_targets(
    session,
    run_id=run.id,
    filter=TargetFilter(kind="navigation"),
    after=cursor,
    limit=100,
)

selected = select_idor_work(session, run_id=run.id, object_limit=80, identities_per_object=3)
```

`page_targets` returns a stable page of exact targets and their discovery identities. It does not create scan obligations. `select_idor_work` returns only bounded, concrete targets with a successful credential baseline; the caller persists work only for the returned selections.

At the crawl boundary, links are retained before sampling, including links held for later layout checks:

```python
discoveries = discoveries_from_links(
    raw_links, source_page_id=page_id, source_state_key=state_key,
    identity=phase_identity, base_netloc=base_netloc,
)
record_discoveries(session, run_id=run_id, discoveries=discoveries)
admitted = route_sampler.offer(link_items, phase_key, is_queued)
enqueue(admitted)
```

When a Test Lead dispatches specialist work, it supplies the source evidence identity. The same evidence remains idempotent, while a later lead about the same URL can create a new episode after prior work is terminal:

```python
handoff_id, created = create_or_get_handoff(
    session,
    HandoffRequest(
        run_id=run_id,
        run_kind="web",
        attack_class="idor",
        target_url="https://shop.test/orders?id=202",
        parameter="id",
        session_label="customer-b",
        evidence_key=f"lead:{lead.id}:revision:{lead.revision}",
    ),
)
```

## Shape

### Data model

`DiscoveredTarget` is one exact target in a run, keyed by a digest of the verbatim URL plus the explicit browser `state_key`. The URL string is retained unchanged, including query order, duplicate keys, blank values, and meaningful fragments. Path templates are a separate derived grouping key and never replace target identity.

`TargetDiscoveryEvidence` is one idempotent observation linking a target to its source page/state and crawler identity. Its unique discovery key includes the run, target, source state, and identity key. Identity is `anonymous`, a current credential ID, or an explicit unknown label. A link observed under a credential is discovery provenance only; it does not mean that credential owns the object or successfully opened it.

This separation follows **Model the Domain**: discovery, access, selected work, and results are different records with different evidence. `target_catalog.py` parses crawler and archive inputs into domain values at the boundary, following **Boundary Discipline**, then owns catalog key generation and persistence behind one interface. Per-observation inserts avoid shared JSON read-modify-write state, following **Separate Before Serializing Shared State**. Unique keys make retries converge after a restart, following **Make Operations Idempotent**. The archive migration moves directly to this final shape, following **Outcome-Oriented Execution**.

Access evidence stays attached to the exact visited `CrawledPage` and its `PageCredentialView`. Recon emits per-target, per-identity observations and does not overwrite them by canonical path. A positive view means that identity reached that exact object. Missing views, failed requests without an explicit denial status, and unmatched identities remain unknown. Do not compare page text across different target keys. A same-target comparison may use captured content as evidence, but is not by itself proof of ownership.

Only selected work enters `ScanObligation`. Add optional `target_key` and exact `target_url` for an object-specific check, the baseline and comparison identity IDs for access-control work, and a stable `scope_fingerprint`. A unique `(run_kind, run_id, scope_fingerprint)` constraint makes insertion retry-safe. Existing route-level obligations keep `target_key` null. New object-specific obligations are created only from an explicit bounded selection result, never by enumerating the catalog.

### Caller and module responsibilities

- `route_sampling.py` owns queue admission and layout confirmation. Candidate grouping can still infer a shared route shape, but member identity always includes the full semantic URL and meaningful state. The sampler may hold a target from browser work while the catalog records it immediately.
- `target_catalog.py` owns discovery parsing, target identity, persistence, archive representation, and keyset-paginated reads. It accepts domain `Discovery` values, not ORM or archive dictionaries. Bulk SQLite inserts use a unique key with `ON CONFLICT DO NOTHING`; retries converge without a shared JSON read-modify-write.
- `crawler.py` extracts all same-domain links and JS navigation targets, records those exact targets, then offers them to the sampler. The 300-item `TargetIntelItem` limit stays a cap on descriptive intelligence, not on route discovery. Catalog writes are batched and do not enqueue requests.
- `recon_summary.py` joins visited pages and their credential views to exact target keys. It emits observed reachability by target and identity, and leaves other combinations unknown. The current scalar canonical-URL access map is removed.
- `web_workprogram.py` owns selection and coverage semantics. UI route groups show `mixed` when member cells differ. Group display rows do not determine completion. Standard and Enforce completion read the raw applicable `PageOwaspTest` cells and selected `ScanObligation` rows. The discovery catalog is excluded from both denominators.
- `resolve_web_page_id` keeps source/replay attribution separate from exact target evidence. An explicit page ID identifies the source page. A URL-only target maps to a page only when its exact target key matches; path-only fallback is forbidden for object-bearing URLs. If no exact visited page exists, store the object target on its selected obligation and evidence, with no invented `CrawledPage` or unrelated page cell. On-demand object probes therefore cannot make `/orders/101` cover `/orders/202`. Existing non-object route fallback may remain where the URL has no variable object identity.
- `scanner.py` uses a bounded IDOR selector and the existing request-time scope policy. It selects at most 80 unique in-scope object targets and at most 3 identified comparison identities per target. A candidate requires an actual successful `CrawledPage` plus a positive `PageCredentialView` for an identified credential on that same exact target. Missing access observations do not mean denied. The existing successful-response and same-object body-evidence checks remain; no request is sent for an inventory-only URL.
- `specialist_handoffs.py` owns scope and episode identity. Scope includes exact query and fragment semantics, normalized attack class, parameter, and identity label. Active work conflicts only with the same exact scope. The evidence fingerprint adds a stable lead/evidence revision. Repeating the same dispatch is a duplicate; a new evidence revision can reopen completed scope as a new handoff row.
- `crawl_archives.py` exports targets and evidence with the source credential username and state keys. Import remaps usernames to destination credential IDs, reconstructs target/discovery keys, and keeps unknown identities unknown. `saved_crawls.py` uses the same archive payload path.

### Persistence and archive migration

Add `discovered_target` and `target_discovery_evidence` tables through Alembic. The target table has unique `(test_run_id, target_key)` and stores the exact URL and optional state key. The evidence table has unique `(test_run_id, discovery_key)`, a target foreign key, source page/state, identity key, optional credential foreign key, and source kind. Keep `CrawledPage` and `PageLink` semantics unchanged.

Version the route-sampler snapshot's member identity. On resume from an older snapshot, discard old path-only group membership and decisions, then let newly encountered links pass through the exact-identity sampler. Re-offered exact URLs can be grouped again; the old snapshot is not used to invent catalog entries or recover query variants already lost from memory. Existing archive group summaries remain display data only.

Add `target_key`, `target_url`, `baseline_credential_id`, `comparison_credential_id`, and `scope_fingerprint` to `ScanObligation`. Existing obligations receive stable legacy fingerprints during migration, preserving their statuses. New selected obligations are inserted with conflict-safe uniqueness. Keep object-specific fields null on existing route-level obligations.

For `SpecialistHandoff`, add `scope_fingerprint` and `evidence_fingerprint`; change uniqueness from `(run_kind, run_id, fingerprint)` to `(run_kind, run_id, evidence_fingerprint)`. Backfill existing rows from stored target URL, attack class, parameter, and session label, retaining their old IDs and outcomes. The new canonical scope keeps query and fragment values exactly. A legacy row for `id=101` therefore cannot suppress `id=202`; old handoffs whose lost query distinctions cannot be reconstructed remain single legacy rows and do not block a different new evidence fingerprint.

Increment the crawl archive version. Export exact target URLs and each provenance row; import maps credentials by username and rebuilds digests from the destination identity. Archives without the new fields import as before. Do not infer targets from route summaries, synthesize unvisited `CrawledPage` rows, or claim to recover URLs already lost before this change. Target inventory reads use a stable keyset cursor over `target_key`; the existing 1,000-row intel query remains a separate, bounded descriptive view. New Alembic data needs no frozen-app asset bundling because it is schema and ordinary application data.

### Outcome and coverage semantics

Discovery means "this exact target was observed in a link or script." It creates no coverage obligation. A visited page means "the crawler loaded or replayed this exact state." A credential view means "this identity reached this target." A missing view means unknown. A selected obligation means "the scan intentionally chose this exact security check." A `ProbeExecution` and its `CoverageEvidence` report attempted and evaluated outcomes.

For object checks, the denominator contains only selected obligations. For page/category coverage, the denominator contains applicable visited-page cells. Route-group rows are display summaries; mixed members render mixed. Finding, covered, skipped, or in-progress status on one representative never promotes a different object's cell or makes a grouped column complete. Standard completion computes its percentage from raw applicable cells and selected obligations, not group rollups or discovered links. Both Standard total reads in `scanner.py` must use this ungrouped calculation, and the web work-program UI must label group disagreements as mixed.

### Bounded IDOR selection

Selection starts from exact, in-scope `CrawledPage` targets that have an object-reference signal and a successful credential-specific view. It deduplicates by exact target key, never by route template. It requires at least one positive, identified baseline and a second configured, identified session to compare. It selects no more than 80 objects per run and no more than 3 comparison identities per object, in stable round-robin order by route template and target key. The ordinary request budget and rate limit still apply. No request is made for merely discovered URLs. The selector does not mark a missing credential view as denial or ownership; the only positive finding path remains a successful response containing evidence for the same target object, with the existing denial and SPA-shell exclusions. A later lead for an unvisited object keeps its exact URL as selected-test evidence; it does not fall back to a path-matched representative page.

### Handoff idempotence and concurrency

Catalog writes use deterministic target/discovery keys and SQLite conflict-ignore inserts. Replaying a crawl batch cannot add duplicates. Each crawler worker submits its own rows; there is no shared mutable inventory snapshot. Archive import uses the same idempotent key construction after identity remapping.

Coverage obligation creation uses a unique scope fingerprint, so retry after a crash returns the existing row. Specialist creation uses a unique evidence fingerprint; the database constraint is the final race guard if two lead workers dispatch the same evidence concurrently. Active conflict checks query the same exact scope and active statuses only. Completion closes an episode, not the scope forever. A new lead revision produces a distinct evidence fingerprint and can start another episode. Legacy scope values are rebuilt from stored URLs during migration so path-only suppression ends for future dispatches.

## Synthesis decision

This candidate chooses a relational exact-target catalog with separate discovery evidence because the existing `TargetIntelItem` path truncates and paginates incorrectly, and its check-then-insert has no unique key. It also makes it possible to retain multiple discovery identities without treating them as access or ownership. The design keeps selected scan work in `ScanObligation`, so catalog size cannot silently become the completion denominator.

The alternative in `alternative.md` retains discovery as enriched `TargetIntelItem` rows and repairs their identity and pagination. It has fewer tables but couples an exact catalog to the descriptive-intelligence schema and its current limits. This candidate accepts two catalog tables to make exact target identity and provenance independently queryable and idempotent.

## Tradeoffs accepted

- We accept two small relational tables and an archive version change in exchange for preserving exact targets and multiple provenance identities without mutable JSON aggregates.
- We accept a larger archive for all discovered links in exchange for preserving what the sampler held back.
- We accept that an exact target can be known while access remains unknown; this prevents link visibility from being presented as authorization evidence.
- We accept that only selected object targets appear in the coverage denominator; the remaining inventory is available for deliberate follow-up without claiming mandatory work.
- We accept that the existing fixed per-run IDOR caps may leave targets untested; increasing those caps requires a separate budget decision.

## Alternatives considered

The concrete alternative is to keep `TargetIntelItem` as the only catalog, store exact URLs plus provenance in its metadata, and add cursor pagination. That hides target storage behind fewer modules, but callers inherit the intel table's 500-character key and 2,000-character value limits, the archive's current metadata path, and the need to coordinate a query-level uniqueness rule across mixed intel kinds. It also leaves discovery semantics mixed with scripts, forms, and response fields. It loses on a complete exact-target contract.

## Implementation reconciliation

No implementation deviations have been accepted. This candidate is a design artifact only.

## Open questions and risks

- Should the IDOR cap remain 80 exact targets per run when those targets come from multiple route shapes?
- Should `PageCredentialView` gain an explicit response outcome so explicit 401/403 observations can be distinguished from a missing observation? Until then, this design records reachability and leaves other outcomes unknown.
- Archive growth follows the number of discovered link targets. The browser already extracts those links, but very large applications may need an operator-visible storage limit in a later product decision.

## Next implementation step

Add the catalog models and Alembic migration, then wire the crawler to persist exact same-domain discoveries before route sampling.

