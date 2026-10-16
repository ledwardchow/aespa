- [x] Route through the **how** skill. For motivation questions, also route through the **why** skill.
- [x] Throughput checkpoint stays one line: `throughput checkpoint: n/a, read-only investigation`.
- [x] Produce the `how`-shaped output (Overview / Key Concepts / How It Works / Where Things Live / Gotchas), or a recommendation with a tradeoffs table if the request is a decision between alternatives.
- [x] Apply the **unslop** skill to the reply.

Read-only audit. Three source investigations cover deterministic authorization/IDOR, planning/coverage, and discovery/context. No product changes authorized by this audit request.

Confirmed findings and follow-up work.
- [ ] Preserve security-significant query variants in RouteSampler membership and rejection release. Reproduction discovered 11 URLs, rejected group, visited 10, account_id=2 absent, drain empty.
- [ ] Retain exact discovered unsampled URLs separately from crawl visit/indexing. Reproduction offered 200 links, sampled 5, snapshot retained zero exact unsampled URLs. Crawler removes held links before saving endpoint intel.
- [ ] Aggregate recon access observations without overwriting concrete object differences. Reordering private/public object pages changed canonical anonymous flag and credential IDs.
- [ ] Avoid using highest-status grouped coverage for Standard completion. In-memory probe had one covered A01 and one untouched A01; grouped completion was 100% while raw gaps still contained one untouched cell.
- [ ] Preserve query object identity and accept new evidence in specialist handoffs. Query ID variants fingerprint identically, path ID variants do not. Existing handoff returned as duplicate even after terminal completion.

The first two are specific to grouped crawling. The latter three are pre-existing canonical-route issues also present in Visit each URL. No product changes, live scan, actual database inspection, GitHub issue or PR creation performed. Deep query-operation merging was inspected but excluded from the main confirmed list because the complete worker execution path was not reproduced.
