# Grouped crawling without limiting security tests

Status: implemented and under final verification. The signature sketch remains conceptual; production names and evidence are recorded below.

## Problem

A crawl may discover 200 product or order links and visit five to learn the page layout. All 200 links should remain available for testing. Keeping a link must not create a page-analysis job, a specialist job, or a required coverage row. Security results must describe the objects and accounts actually tested.

The audit reproduced five problems: query variants lost by the sampler, held links removed before inventory recording, access observations overwritten by route, Standard completion based on the best result in a group, and specialist handoffs merging query IDs. The first two require grouped crawling; the last three also affect Visit each URL.

## Usage, from the caller

The crawler records discoveries before sampling. Recording a link sends no target request.

```python
catalog.record_discoveries(
    run_id,
    source=DiscoverySource(page_id, source_state_key, current_actor, "dom_link"),
    targets=tuple(ExactTarget(link["href"]) for link in eligible_raw_links),
)
admitted = sampler.offer(link_items, phase_key, route_is_queued)
```

The lead can retrieve later pages of a group's exact URLs. The response distinguishes a link sighting from a successful fetch.

```python
page = catalog.targets(
    run_id, TargetQuery(route=route_pattern, after=cursor, limit=50),
)
```

The workprogram selects a bounded comparison with a real baseline. The request uses the existing scope, session, logging, and policy checks. Its source page is a navigation hint, separate from the target being tested. `send_with_existing_policy` below is pseudocode for the existing request and evidence-evaluation path. It returns the persisted traffic/evaluation references and evaluated outcome, not an inferred result from status alone.

```python
cases = workprogram.select_idor_checks(run_id, active_actors, IdorBudget())
for case in cases:
    response = await send_with_existing_policy(
        request=case.scope.request, acting_as=case.scope.actors.comparison,
    )
    result = EvaluatedCheckResult(
        target=case.scope.request.target,
        actors=case.scope.actors,
        execution=DirectResponseRef("traffic", response.traffic_id),
        evaluation=EvaluationRef(response.coverage_evidence_id),
        outcome=response.outcome,
    )
    workprogram.record_result(run_id, case.id, result)
progress = workprogram.completion(run_id, mode="standard", target_percent=60)
```

A specialist receives an exact scope and references to supporting evidence. The claim service decides whether the evidence supports a new investigation. It does not accept a model-invented revision string.

```python
claim = handoffs.claim(
    run=RunRef("web", run_id), scope=case.scope,
    evidence=EvidenceSet((baseline_ref, changed_access_ref)),
)
```

These calls correspond to the companion [type and signature sketch](grouped-route-testing-sketch.py). The sketch is deliberately unimplemented.

## Shape

Use a small relational target inventory. Keep the current crawler, scan engine, workprogram, and specialist executor.

| Record | Meaning | Creates required scan work? |
| --- | --- | --- |
| `DiscoveredTarget` | One exact URL and browser state observed in this run. | No. |
| `TargetDiscovery` | Which page/state and account exposed a link to that target. | No. |
| `TargetAccessObservation` | A direct response for an exact target, method, and account, with an evidence reference. | No. |
| `CrawledPage` / `PageCredentialView` | An actually loaded or replayed page and its recorded views. | Existing applicability rules apply. |
| Object-scoped `ScanObligation` | One deliberately selected security check, including its target and account comparison. | Yes, only when selected. |
| `ProbeExecution` / `CoverageEvidence` | What was attempted and what the evidence supports. | Records results for the selected check. |

`TargetAccessObservation` is an index of direct evidence in traffic or page views. It stores no second response body and no independent ownership claim. Access observations remain append-only; the route summary is a read projection. `record_response` accepts only a direct traffic, page-view snapshot, or executed-probe reference. It verifies the source run, exact requested target/state, method, and actual actor before classification. Leads, link sightings, retry requests, and endpoint descriptions cannot create reached or denied observations.

### Exact identity and crawl admission

Target identity preserves the complete path, trailing slash, raw query string, repeated keys, empty values, query order, and browser fragment. An explicit interactive state key distinguishes replay states that share a URL. Resolve relative links and validate schemes at the discovery boundary. Lowercasing scheme/hostname is permitted; do not decode or reorder the resource selector. Route patterns and layout groups are separate labels.

Change sampler member identity to this exact identity, regardless of how the group pattern was found. Different query values remain separate pending members and must all be released if grouping is rejected. Confirmation still stops extra layout visits. It does not delete targets from inventory.

Batch-record every eligible extracted DOM or JS navigation link before sampling or queue filtering. Do not route this through `raw_links[:300]` or the truncated `TargetIntelItem.value`. Remove the old DOM-link inventory writer after its consumers move; leave script, form, input, and other intelligence in `TargetIntelItem`. Old DOM-link rows remain historical evidence and are converted at migration/import boundaries.

Inventory reads filter in SQL before a stable-ID keyset limit and return an opaque cursor tied to the query and run. Search must reach results beyond the old first 1,000 rows. Do not load the complete inventory into the lead's opening prompt. Existing scope restrictions still apply at dispatch, including explicit exclusions. A discovery is never permission to make a request.

A storage or write failure must be reported as an incomplete discovery stage. Do not continue by silently losing the remaining links. Batch size limits transaction size, not total retained links. No new arbitrary inventory cutoff is introduced by this fix.

### Access observations

Use explicit anonymous, configured-credential, and unknown actors. Unknown does not mean anonymous. Session labels and rotating tokens resolve to stable principal identities before attribution or handoff checks. Seeing a link as Alice proves only that Alice saw the link.

Recon first groups observations by exact target, state, method, and actor. It then derives route summaries containing the concrete differences. A later public object cannot replace an earlier protected object. Compare anonymous and signed-in content only for the same object and state, under comparable request conditions. Do not compare different orders' bodies to infer identity-dependent content.

Keep `anonymous`, `authenticated`, `mixed`, and `unknown` as display classifications, with concrete member observations alongside them. Add a derived `needs_anonymous_comparison` field for planning. It remains true when any concrete member has evidence requiring a sign-in comparison; a different public member cannot clear it. A successful signed-in response alone does not prove that anonymous access is denied. Uncertain cases remain possible tests rather than being labelled protected or safe.

### Selected checks and coverage

Extend `ScanObligation` with an explicit `scope_kind` of `route` or `object`. An object check stores exact target ID, method, test class, parameter, ordered baseline/comparison actors, baseline observation reference, and a unique selection key. A body-based object reference is part of request scope too. Route templates are search/group labels, never object check identity.

Use existing `ProbeExecution` and `CoverageEvidence` for attempts and outcomes. Add an exact target reference and immutable request identity to executions, so evidence remains identifiable even without a page. An evaluated outcome must reference an actual comparison execution and evaluation. A blocked outcome instead requires a reason and its supporting evidence. Neither result shape can substitute a discovered link for a request. An outcome can change only its selected check. Completing one route-level check cannot complete every object check on that route.

`resolve_web_page_id` is no longer the identity function for security evidence. Preserve the source/replay page separately. For coverage or finding attribution, a page can match only the exact target and explicit replay state. A page hint for `/orders/101` cannot make a probe of `/orders/202` update the first object's cell. Arbitrary mutated payloads and inventory-only links create no `CrawledPage` rows. Real browser navigation can still create pages normally.

Define completion as a set of distinct root units, not the sum of overlapping tables:

1. Keep each applicable raw page/category unit, expanding the existing A03 test classes as today.
2. If an object check matches a visited page by exact URL and explicit target state, and its category/test class matches one raw unit, attach it through `parent_page_cell_id` and `parent_test_class`. The parent is a page/category aggregate; method and ordered account pair remain in each child key. It is not another denominator entry. Never use a source page, route template, query-stripped URL, or ambiguous same-URL state to choose that parent.
3. If no exact page unit exists, the deliberately selected object check is one additional root unit. A source page or canonical route match cannot make it a child of an unrelated page.
4. Route-level `ScanObligation` rows describe the workprogram and are not added again on top of their page units. Unselected inventory contributes zero units.

For a root unit with no selected children, preserve the current raw-cell policy: in-progress, covered, and finding count as exercised; covered or finding are resolved, and justified skips follow the existing exclusion policy. For a unit with selected children, derive progress from those children. Every applicable child must have a recorded comparison attempt before the unit is exercised. An inconclusive attempted comparison is exercised for Standard but unresolved for Full. Every child must be passed, finding, or blocked with a supported reason before the unit is resolved. A blocked child without an executed comparison is not exercised. A previously covered raw cell cannot satisfy a newly selected child or hide it; the raw result remains history. The root's finding badge is independent of these progress flags.

The workprogram owns this mapping and returns the same completion object to the lead's `done` callback, final run outcome, progress display, and gap list. Standard retains its configured exercised-percentage policy. Full retains its requirement to resolve selected checks or record a justified block. This design does not promise every discovered record is tested.

For example, 200 discovered links, five visited pages, and one selected check on an unvisited object produce five applicable page units plus that one extra check for the category in question. A check on one of the five visited objects attaches to its existing unit. One covered page and one untouched page remain one of two exercised, even if both display under the same route.

Grouped rows show `tested / selected` counts and unresolved children. Finding badges remain visible independently. A finding or covered child never hides another child's pending work. Useful completion progress comes from a new selected check result, evidence, or coverage transition; changing random IDs alone must not defeat existing repetition or budget limits.

### Access control and IDOR selection

Retain current request budgets: at most 80 selected object targets and at most three comparison actors per target in the deterministic pass. Spread selection across routes and observed identities before consuming more targets from one group. Existing rate, step, and request limits still apply. No inventory iteration dispatches a request by itself.

A deterministic comparison requires a successful, identified baseline for that exact object. A missing view is unknown, not an unauthorized account. Compare the second response with that object's baseline. Denial-like content, login shells, failed authentication, or ambiguous responses cannot confirm access.

Discovered-only links stay available to the lead. If it selects one, it first establishes an authorized baseline through the ordinary request tools. That request consumes the existing request budget. It can then select a comparison check; do not automatically fetch every discovered link to obtain baselines.

A confirmed IDOR needs evidence of the intended boundary, such as an object created under one account, a trusted ownership field, or an account-scoped fixture, plus evidence that another account crossed it. Public products fetched by two customers are not IDOR. Without evidence of the boundary, retain the cross-account observation as inconclusive and let the validator investigate it.

### Specialist scope and follow-up evidence

Separate an investigation's exact scope from its evidence revision. Scope includes run kind and ID, HTTP method, exact URL/state, body object references or request-body identity, attack class, parameter, and the ordered account comparison. Resolve the default session before constructing scope. Do not use absent actors as wildcards. Token refresh does not create a new account identity.

The same scope plus the same evidence revision is idempotent. An active investigation owns only its exact scope; `/orders?id=101` cannot block `id=202`, nor can one account pair block a different pair. A new supporting fact for an active scope is retained as a deferred attempt rather than silently dropped. Identical evidence still returns the existing attempt.

After completion, materially new evidence can create another attempt. The core claim service resolves supplied evidence references and admits a revision only for a new object/operation/account scope or a supported change in the same object's baseline, access outcome, or entitlement evidence. A new traffic row, timestamp, nonce, session label, or rephrased rationale alone is not a revision. Evidence without a demonstrated change returns `already_investigated` or `insufficient_new_evidence`, with the earlier result. UI-requested retries use a durable retry request ID and the existing retry budget rather than pretending to be new evidence.

Use two database constraints: unique `(run_kind, run_id, scope_key, revision_key)` and a partial unique `(run_kind, run_id, scope_key)` where status is queued or running. Claim and follow-up retention occur in one short write transaction. No network work runs inside it. Persist an accepted follow-up as its own `SpecialistHandoff` row with status `deferred`. It has its own revision key and does not hold the active-scope constraint. After the current attempt ends, the scheduler can atomically activate it within the existing queue budget. This keeps independent evidence out of a shared mutable JSON list and survives restarts. On resume, the existing job recovery requeues durable queued work and reconciles stale running ownership before another claim.

### Modules and consumers

| Owner | Responsibility and callers to migrate |
| --- | --- |
| `services/target_catalog.py` | Exact target identity, discovery/access inserts, actor provenance, paged inventory. Crawler, context tools, recon, archives read this interface. |
| `services/route_sampling.py` | Queue admission and layout grouping only. Share the pure target-identity definition; stop stripping queries for member identity. |
| `services/recon_summary.py` | Derive per-object access and descriptive route summaries. No access-map overwrite by route. |
| `services/web_workprogram.py` | Select object checks, exact evidence attribution, root-unit mapping, authoritative completion and gap reads. |
| `services/specialist_handoffs.py` | Exact scope claims, evidence admission, active ownership, retries and deferred follow-ups. API and web callers use the same key rules. |
| `services/scanner.py` | Record discoveries/results through owners; use the completion read in both Standard locations; resolve actors before scope checks. Keep existing request enforcement. |
| `services/deep_scan.py` | Preserve each selected check's exact target and actors in the campaign child and worker brief. Grouping may bundle work but cannot replace its target or close unexecuted children. |
| `services/crawl_archives.py` | Serialize portable target/provenance references, remap on import, accept older archives. Saved crawls use this same path. |
| Frontend workprogram and Attack Surface | Show grouped member progress and concrete access differences. Read authoritative completion rather than highest-status display totals. |

Ordinary, Team, Deep, and focused scans must retain their existing mode and explicit scope restrictions. A selected target outside the current scope remains blocked; discovery does not override that decision. Shared tables always filter on run kind as well as ID.

## Persistence and old data

Use Alembic for the three catalog tables, selected-check fields, execution attribution fields, and versioned handoff keys. Use non-null encoded identity keys for anonymous, unknown, and absent state values; SQLite nullable unique columns alone do not deduplicate them. Upserts use database unique constraints, not check-before-insert or a shared JSON snapshot. If identity digests are indexed, verify the full stored tuple on a matching digest; a collision must never merge two targets. Commit discovery batches before advancing the sampler.

Backfill only exact URLs present in pages, stored endpoint facts, or traffic. Backfill access only from identifiable direct evidence. Do not reconstruct missing URLs from group counts or infer ownership. Existing page/category outcomes stay historical results for their recorded pages; backfill does not assert new object-specific coverage.

Version sampler snapshots. Old path-only membership cannot suppress newly seen query variants. Carry forward only exact pending/sample entries and replay them through the new member-key logic; rebuild decisions as needed. Do not turn the retained target catalog into an automatic full crawl on resume. Already-lost URLs remain unavailable until rediscovered.

Archive v2 carries portable references for targets, source pages/states, actors, and access evidence. Use archive-local page and actor IDs, not URL-only or username-only matching. If duplicate usernames or missing destination credentials prevent a safe match, preserve an unknown actor with its source reference rather than assign the wrong account. Export no new response bodies or credentials. Import remaps page, actor, target, and traffic references before computing keys.

The reader explicitly accepts v1 and v2. Convert v1 facts actually present into the new inventory; mark discovery completeness as legacy/unknown. Missing links cannot be recovered. Import creates fresh test selections and coverage, as current saved crawls do; past access observations may be retained with their age and must be revalidated before new security claims.

Legacy handoffs retain their history. Reconstruct exact scope only where method, target, and actors are evidenced. Unreconstructible old query-free scopes cannot remain broad active blockers. Quiesce/reconcile those jobs before enabling new claims. Legacy terminal rows suppress no new revision without an exact evidence match. Apply the new claim rules consistently to lead requests, browser checks, finding writes, automatic dispatch, Burp dispatch, Team, Deep, and API callers.

No new runtime asset or library is proposed. Check that the existing frozen-app migration bundle includes the added Alembic revision. Update API schemas for inventory cursors and completion/member summaries. The implementation turn will update version and Unreleased notes; this document does neither.

## Synthesis decision

Use candidate 2's dedicated catalog as the base. The independent judge scored it 22/24, against 21/24 for each other candidate. The primary comparison agreed on the catalog boundary. All three candidates preferred a catalog over extending generic intelligence, but differed in access indexing and work attribution.

Graft candidate 1's strict ownership evidence and source-page separation. Graft candidate 3's sampler-version and old-archive handling. Resolve gaps identified by the judge with an explicit root-unit mapping, method and ordered account scope, and core-owned evidence revision admission. These resolutions are part of the proposed design, not claims about implemented behavior.

This applies Model the Domain to separate links, access observations, chosen tests, and results. Boundary Discipline keeps parsing and provenance validation at service inputs. Make Operations Idempotent and Separate Before Serializing Shared State require fact rows and database constraints. Laziness Protocol keeps the existing scan engine and result records. Prove It Works requires the behavior tests below rather than treating a valid signature sketch as a working fix.

## Tradeoffs accepted

- We accept three indexed fact tables and larger saved crawls in exchange for retaining exact targets and account provenance.
- We accept bounded security testing, with unselected targets still available, instead of a test job for every retained link.
- We accept unknown access and inconclusive IDOR outcomes where evidence is missing.
- We accept a migration and coordinated consumer updates in exchange for one target identity, one completion read, and one handoff scope rule.

## Alternatives considered

Extending `TargetIntelItem` is viable only after changing its truncation, uniqueness, provenance, and pagination rules. That spreads exact-target requirements across unrelated intelligence writers. A fact journal gives simple append-only writes but requires folding events for routine inventory, baseline, and progress reads. Neither hides those complexities as well as the catalog's small interface.

Promoting every link to `CrawledPage` was rejected because it misrepresents discovery as a visit and can turn all 200 objects into coverage work. One large JSON inventory on `TestRun` was rejected because concurrent identity phases can overwrite one another's updates.

## Implementation order and checks

1. Add exact target identity and catalog persistence. Reproduce rejected-group query loss; then prove all variants survive. Keep 200 discovered links while visiting only the existing small sample. Test links beyond positions 300 and 1,000, long URLs, repeated/empty query keys, trailing slashes, fragments, and distinct interactive states.
2. Add archive v2 and restart behavior. Round-trip 200 targets and two accounts under different destination IDs. Import v1 without fabricating data. Concurrently submit the same batch, retry it after a partial failure, and verify no duplicates or missing sightings.
3. Repair access projection and exact result attribution. Reverse private/public object order and obtain identical summaries and selected checks. Test unknown versus anonymous actors. Probe `/orders/202` from a `/orders/101` source page and verify the first object's cell stays unchanged.
4. Add object selection and authoritative completion. Verify one covered and one untouched object remain one of two exercised. Verify a selected child is not double-counted, an unrelated public object cannot clear a protected member's comparison, and 200 retained targets alone add zero coverage units or requests.
5. Replace handoff keys and evidence admission. Query IDs, methods, body IDs, states, and account pairs remain distinct. Identical evidence retries produce one attempt. Repeated identical traffic does not reopen terminal work; supported new evidence does. Concurrent claims produce one active owner. Test stale legacy blockers and restart recovery.
6. Migrate Deep, Team, API, Burp, context tools, and frontend consumers. Verify bundled Deep checks retain exact targets and do not close siblings without evidence. Drive a local two-account fixture with a vulnerable object outside the initial layout sample. Show that it is selectable and testable without indexing the full population. Check screenshots and computed table bounds after the frontend build.

Use service tests with an in-memory database and no live LLM calls. The live fixture requires local loopback access. Run focused tests, Ruff, frontend checks/build, and applicable migration/archive tests at each implementation unit. Do not call the feature verified until the local fixture demonstrates access to the unsampled vulnerable object.

## Implementation reconciliation

Production uses `DiscoveredTarget`, `TargetDiscovery`, and `TargetAccessObservation` for retained links. `ScanObligation` and `ProbeExecution` carry exact object scope and actor pairs. The discovered-target context query and `select_object_check` tool allow testing without creating synthetic crawled pages. Archive v2 remaps identities and requires fresh access baselines after import. Completion shares root units between route and selected object checks.

The local fixture retained 206 targets while the crawl fetched six order pages. The scanner requested uncrawled order 297 as both accounts and saved its selected A01 check. Other records remained unfinished. Generated address data completed its workflow; payment and deletion submissions stayed stopped. Local test logs and startup evidence are no longer stored in the repository.

## Open questions and risks

The proposed defaults are fixed for implementation: preserve all extracted eligible links, keep current request budgets, keep stale or ambiguous evidence inconclusive, and use ordinary request tools to baseline a discovered-only object. No product preference blocks the first unit.

Response classifiers and archive identity mapping need implementation tests because a login shell is not a positive object baseline and usernames need not be unique. Large inventories increase database/archive size; batch and cursor behavior should be checked with a large synthetic catalog without claiming a performance improvement. Historical missing targets cannot be recovered by migration.

## Recorded verification

The implementation checklist recorded 2,314 passing backend tests and 378 passing frontend tests, plus frontend lint, type checks, and build. Startup recovery was checked by launching AESPA against a private database copy. The server returned HTTP 200, and SQLite integrity and foreign-key checks passed. These results describe the implementation session; the checks have not been rerun for this documentation cleanup.
