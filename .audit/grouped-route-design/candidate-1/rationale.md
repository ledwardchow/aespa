# Candidate 1 rationale

## Problem

Grouped crawling is meant to reduce page visits, but the current sampler identifies some members without their query values and filters held links before endpoint persistence. Later, recon collapses access by route, coverage takes the best page status in a group, and specialist handoffs strip query values. A route layout is useful for display and budget allocation; it cannot stand in for an exact object or a test result. The design keeps those identities separate while retaining the current sampler, workprogram, and specialist executor.

## Usage (caller's view)

The first file in this package, `README.md`, is the usage contract. The crawler calls `record_links` before `RouteSampler.offer`; the lead calls `list_targets` with a cursor; deterministic IDOR calls `select_idor_probes`; the specialist scheduler calls `claim_handoff` with an exact scope and durable evidence reference. The signatures in `design.py` match those calls. A direct HTTP probe calls `attribute_test_result` with a target ID and traffic ID. There is no call that promotes every discovered target into a page or coverage cell.

## Shape

`DiscoveredTarget` is keyed by `(test_run_id, exact_url, target_state_key)` with a full URL text value and stable ID. `TargetDiscovery` is keyed by `(target_id, source_page_id, source_state_key, credential_id, source_kind)` and records the link or interaction and when it was seen. Anonymous is an explicit actor value, separate from a missing/unknown actor. `TargetResponseObservation` is keyed by a durable event key and points to one exact target, actor, and `TrafficEntry` or `PageCredentialView`. Its result says what response was observed. It does not say who owns the object or who should have access. `CrawledPage` still means an actual visited or replayed page.

The crawler writes all eligible DOM links before sampling. The current `raw_links[:300]` cap in `_record_page_intelligence` cannot be the inventory path. Move DOM-link persistence into this batch write and leave forms, scripts, and other intelligence in `TargetIntelItem`. The existing `TargetIntelItem` check-then-insert and value truncation cannot guarantee exact URL retention. Keep the in-memory sampler state for admission and group layout only. A group rejection can still release queued links; a confirmation no longer deletes their identities from the scan. An interactive target with the same URL has a distinct `target_state_key`. The target key preserves path spelling, trailing slash, raw query bytes, and meaningful browser fragments. The sampler's `_member_identity` must use this full target identity for every member, irrespective of which candidate key grouped it; the current `_identity` still strips a trailing slash and some fragments, so it cannot be reused unchanged.

The target read uses SQL filters and keyset pagination by stable ID, returning `next_cursor`; it removes the current first-1,000-row prefetch in `scanner.py`. Search must not claim a full count if it only examined a page. The route projection can show a bounded set of examples and total discovered count, while the lead can retrieve later pages or filter by route and actor. Scope is checked again by the request dispatcher. The inventory does not grant scope or authorization.

Recon keeps access observations under exact target and actor, then derives a route summary with `mixed` or `unknown` where appropriate. It never assigns one object's content to another object because their paths normalize to the same route. `req_auth` and `accessible_by` are observations about successful reachability, not ownership or proof that another actor was denied. Route summaries link back to exact evidence. Legacy page views can be indexed by their exact URL and state key at read time; missing observations remain unknown.

`PageOwaspTest` and selected `ScanObligation` rows remain the coverage units. Standard completion reads raw applicable cells and unresolved selected obligations; the UI grouped row reports child counts and a partial state when some members are untouched. A finding on one child can appear in the group without hiding untouched children. The same raw progress function serves the completion check around `scanner.py:9675` and the earlier progress report around `scanner.py:9148`, so they cannot disagree. Newly discovered URLs do not grow the denominator. An on-demand test on a different object records its exact target on `ProbeExecution` and traffic, while the route obligation receives the result. `resolve_web_page_id` must stop falling back from `/orders/202` to `/orders/101` for evidence or coverage. An explicit page ID is accepted only after exact URL and state verification. Page creation belongs to actual browser visits or replay, not arbitrary HTTP payloads.

IDOR selection uses positive response baselines for the same exact target, including a small budget of baseline fetches for discovered-only links. The selector caps total probes, probes per route, and actor pairs per route before requests are issued. It can prefer targets with a positive baseline from one identified account and a different identified account available to test. It never treats a missing response as denial. Response comparison is between the baseline and second request for the same object. A confirmed ownership violation also needs separate entitlement evidence; without that evidence, successful cross-account access is an inconclusive or reviewable signal. One account seeing a link is not entitlement evidence. Existing deterministic IDOR code uses crawled pages as baselines, so this selection can be added without turning all discovered links into requests.

Specialist `Scope` includes exact URL, browser state, method, attack class, parameter, and actor. Raw query semantics survive in the digest. The scheduler still has its queue and per-operation caps, so exact scopes do not cause one specialist per discovered URL. Active claims conflict only for the same scope. A completed claim suppresses retries carrying the same durable traffic/lead/finding evidence reference; a new evidence event can create a new attempt in the same scope. The database claim runs in one short transaction with a unique `(run_kind, run_id, scope_digest, evidence_kind, evidence_id)` constraint and an active-scope uniqueness rule, with conflict reread on concurrent inserts. It does not depend on process-local state. API and web run IDs are always paired with `run_kind`.

The public target interface hides URL validation, deduplication, persistence, pagination, and provenance joins. Callers supply domain inputs and receive exact refs. It is deeper than exposing ORM rows and does not require the crawler or scanner to coordinate insert stages. This follows the model-the-domain, boundary-discipline, make-operations-idempotent, and separate-before-serializing-shared-state principles from the pstack guidance.

## Persistence, archive, and rollout

Add the three target tables and indexes through Alembic. Add nullable `target_id` to `ProbeExecution` and to the traffic/evidence path used for freeform tests, or a single exact-target association table keyed by traffic ID if changing `TrafficEntry` is too broad. Either representation must give every new object-specific result a direct target reference. Add a scoped evidence key and scope version to `SpecialistHandoff`, replacing the old unique fingerprint constraint with attempt-level uniqueness and an active-scope uniqueness mechanism that SQLite supports. Keep completion history.

Archive export includes target rows, provenance rows, and response observations with source page URL/state, credential username, and traffic reference. Import remaps target IDs, page IDs, credential IDs, and traffic IDs in one transaction, then rebuilds the unique keys. The archive version increments; old archives import as they did before, with targets synthesized only from URLs actually present in archived pages/intelligence/traffic. They cannot recover links already dropped by the old crawler. Do not infer ownership or denied access from old JSON. An in-place migration likewise only backfills known exact URLs and marks old observations as unknown where positive response evidence is absent.

For handoffs, migrate old rows to scope version 2 using each stored `target_url` and its existing method/default and session fields. Old terminal rows remain history but cannot suppress a new v2 claim without a matching durable evidence key. Old active rows may block only the rekeyed exact scope. The migration handles duplicate legacy rows by retaining history and choosing one active claim per exact scope. New claims never consult the old query-free `canonical_url` as their conflict key.

Ship in verifiable units: target persistence and archive round trip; exact access and page attribution; raw coverage progress; bounded IDOR selection; handoff scope and reopen. Each unit has a service/API test with two object URLs differing only in query, repeated query keys and empty values, two same-URL interactive states, two actors, and a retry/concurrent insert case. The coverage test asserts one completed and one untouched cell remains below 100% in Standard. The attribution test asserts `/orders/202` evidence cannot close `/orders/101`. The archive test imports into new IDs and checks old archives remain importable. No live LLM is needed.

## Synthesis decision

Choose this candidate as the base. The existing-intelligence option in `alternative.md` has fewer tables but puts exact URL identity, per-actor provenance, observations, and pagination into a general intelligence row that already truncates values and has no uniqueness constraint. A dedicated target owner gives the crawler and scanner a small stable interface and keeps `TargetIntelItem` useful for non-link facts.

## Tradeoffs accepted

- We accept a migration and more rows in exchange for exact retained targets and reliable upserts during concurrent crawling.
- We accept bounded baseline requests in exchange for testing some discovered-only objects without visiting every page.
- We accept that unknown entitlement yields an inconclusive cross-account signal in exchange for avoiding unsupported IDOR claims.
- We accept a partial grouped coverage state in exchange for an honest display when child tests differ.

## Alternatives considered

The complete `TargetIntelItem`-based alternative is in `alternative.md`. It hides storage churn from the crawler but exposes more row reconstruction and collision rules to recon, inventory search, archives, and the scanner. A JSON list on `TestRun` was rejected because concurrent crawler workers could lose updates and archives would still need per-actor remapping. Treating every discovered URL as a `CrawledPage` was rejected because it changes the coverage denominator and page meaning.

## Implementation reconciliation

No production implementation was made in this design turn. If implementation changes the exact target key, page attribution rule, or completion denominator, update the usage and signatures here before proceeding.

## Open questions and risks

- Which existing evidence can prove object entitlement for a confirmed IDOR finding in a given target? If none exists, keep the result inconclusive until a validator or user-provided fixture supplies it.
- Should inventory search index full URL text in SQLite FTS, or use bounded route/actor filters and keyset pages first? Either choice must search beyond the first 1,000 rows.
- How much archived response body evidence should be retained beyond the existing traffic archive? The new target rows should point to existing evidence rather than duplicate sensitive bodies.

## Next implementation step

Add the target and provenance migration plus the crawler `record_links` call before sampling, then test that all 200 held product URLs remain discoverable across a saved archive.
