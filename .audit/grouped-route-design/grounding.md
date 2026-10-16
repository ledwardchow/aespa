# Grouped route testing design grounding

## User goal

Sample page crawling and indexing for repeated content, without restricting what records security tests can reach. Do not turn 200 products into 200 required page-analysis jobs or imply that every record must be security tested. Preserve exact discovered targets, object/identity differences, and evidence-limited coverage. The present request asks for a design.

## Current flow

`crawler.py` extracts raw DOM links. `RouteSampler.offer` controls which are added to browser queues. Each visited page becomes a `CrawledPage`, with identity views in `PageCredentialView`. `_record_page_intelligence` persists endpoints in `TargetIntelItem`. The sampler saves group layout state on `TestRun`, and summaries contain patterns, counts, and sample URLs.

`recon_summary.build_recon_summary` reads pages, identity views, endpoint intel, traffic, and page coverage. It produces a route projection for the lead. `web_workprogram` derives route obligations and tracks page/category coverage. The lead can send an HTTP or browser request to any in-scope URL; `page_id` is optional. Successful new URLs can gain a placeholder page. Deterministic auth uses pages plus endpoint/script intel. Deterministic IDOR requires concrete crawled positive baselines and identified account sessions.

Specialist handoffs are persisted by `specialist_handoffs.py`. The lead avoids an active specialist's claimed scope. Scope fingerprints currently use attack class, query-stripped URL, parameter, and one session label. The same persisted row is returned even if completed. Deep groups obligations into operation campaigns and shares ordinary specialist execution; Team runs ordinary lead conversations sequentially.

## Confirmed defects

1. `route_sampling.py:75-95,467-478` strips query from path group member identity. Reproduction used 11 URLs including `/users/100?account_id=1` and `account_id=2`; group rejected, only 10 visited, second account never released. Queries cannot be assumed to be tracking noise.
2. `crawler.py:1677-1689,1726-1731` removes held links before endpoint intel persistence. Sampler offered 200 URLs, visited 5, saved zero exact unsampled URLs. Captured bodies/traffic may still contain links, but normal inventory and automatic planning omit them. Archives retain group summaries, not sampler queues.
3. `recon_summary.py:251` overwrites access by canonical URL. Private object then public object loses private observation; reverse order changes output. `web_workprogram.py:305` may omit authenticated-versus-anonymous work. Fix cannot equate observed access with ownership, nor infer denial from absence.
4. `web_workprogram.py:1719-1798` promotes grouped coverage to the highest status. `scanner.py:9674` uses grouped column totals for Standard completion. One covered A01 and one untouched A01 produced 100% while raw gaps still contained one untouched cell. Full enforce uses raw page cells. Existing route normalization can attribute new numeric object probes to a representative page.
5. `specialist_handoffs.py:82-94,115-130,153-168` drops query from scope fingerprints. `/orders?id=101` and `id=202` collide for the same session; path IDs do not. Scheduler at `scanner.py:5554` treats a later object-specific lead as duplicate even after terminal handoff. Active conflict checks can also block the new object. Must retain duplicate-probe control without closing a whole route forever.

Defects 1-2 are specific to grouped crawling. Defects 3-5 also occur in each_url mode.

## Constraints

- Existing unrelated working-tree changes must stay untouched.
- No live LLM/network calls, actual database inspection, or deployment for design.
- UI groups are display/layout units, not proof of shared security rules.
- CrawledPage remains an actually visited/replayed page, not an inventory placeholder for every discovered URL.
- Preserve exact query values, duplicate keys, empty values, and meaningful browser fragments. Do not sort or discard URL semantics casually.
- User-defined scope and policy remain enforced at request time. Discovery grants neither scope nor authorization.
- Seeing a link as Alice is not proof Alice owns or can read it. No baseline means unknown, not denied.
- Sampling and ordinary scan budgets remain. Inventory availability must not create a request storm, one specialist per URL, or N squared account/object automatic checks.
- Page access aggregation must retain concrete URL and identity provenance, not compare unrelated object texts as if they were the same object across users.
- Completion must use unresolved tests rather than display ranking. Adding inventory alone must not expand the coverage denominator to all catalog records.
- Archives/import must preserve retained targets and identity provenance with remapped IDs, tolerate old archives, and never fabricate previously lost URLs. Schema changes require Alembic, API schemas as relevant, and frozen-app bundling checks if new runtime data files.
- SQLite writes need unique keys/upserts or core single-writer handling rather than snapshot JSON read-modify-write lost updates. Extension main-DB restrictions remain in force.
- Shared run IDs require run_kind filters.

## Source map

- `src/aespa/services/route_sampling.py`, `crawler.py`, `crawl_archives.py`, `saved_crawls.py`
- `src/aespa/models.py` classes CrawledPage, PageCredentialView, TargetIntelItem, PageOwaspTest, ScanObligation, ProbeExecution, CoverageEvidence, SpecialistHandoff
- `src/aespa/services/recon_summary.py`, `web_workprogram.py`, `scanner.py`, `specialist_handoffs.py`, `deep_scan.py`
- `src/aespa/services/prompts/test_lead.py`, `specialist.py`
- Tests `tests/services/test_route_sampling.py`, `test_recon_summary.py`, `test_web_coverage.py`, `test_scope.py`, relevant archive and handoff tests.

## Design task

Produce a coherent minimal architecture solving all five defects. Compare two structurally different whole designs, such as retaining discovery facts through existing intelligence versus a dedicated inventory with relational provenance. Write caller usage first, then typed signatures, module responsibilities, persistence/migration/archive changes, concurrent/retry behavior, and evidence-based tests. Choose the design that has the smallest reliable public interface and preserves the user's sampling goal. Include per-object and per-identity testing scope without making each discovered target mandatory test work. Separate inventory, observed access, selected tests, and proven results.

## Additional integration checks

`crawler._record_page_intelligence` has a 300 DOM-link cap. `_save_intel_item` truncates value to 2000 characters and key to 500, then does check-before-insert without a unique constraint. `target_inventory` reads only 1000 rows before Python filtering and offers no cursor. Reusing it requires these retention and pagination limitations to be fixed, not merely passing unfiltered links to it.

`resolve_web_page_id` prefers a supplied page ID, then exact, query-stripped, and canonical route matches. Exact object evidence must not inherit that display attribution. Avoid a new CrawledPage or mandatory coverage cell for every arbitrary mutated URL. The same-URL interactive replay identity must remain distinct.

Standard progress consumes matrix display column totals both inside the done callback (`scanner.py:9675`) and during final outcome calculation (`scanner.py:9148`). Frontend workprogram totals have the same display dependency. Both backend callers and the UI summary need the same authoritative completion read.

Archive validation currently accepts only version 1. Any format version change needs an explicit read-v1/read-v2 path rather than replacing the one constant and rejecting old saved crawls.

Git history identifies 6ad2207b as the grouped crawler change, with the message "new route grouping crawler". The sampler documents ignoring tracking/sorting query variants, but does not prove any query is security-irrelevant. Preserve cheap content indexing. Change the use of that heuristic for concrete target identity. Broader historical rationale was not needed to override the user's stated testing requirement.
