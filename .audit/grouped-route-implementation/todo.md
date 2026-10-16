# Full grouped-route fix

- [x] Read the Principles section of poteto-mode.
- [x] Phase A: Frame. Done means all five reproduced defects pass regression tests, inline UI uses actual saved data, and a local two-account fixture demonstrates testing an uncrawled object while only a sample is indexed.
- [x] Phase B: Design the workflow. Reuse the reviewed design and approved inline details. Do not repeat arena.
- [x] Phase C: Run the loop.
- [x] Implement catalog, exact sampler identity, and archives in the isolated backend checkout.
- [x] Implement exact access attribution, selected checks, completion, and specialist/deep consumers.
- [x] Implement approved inline details in a separate UI checkout after freezing the API contract.
- [x] Integrate against saved preexisting changes without replacing unrelated work.
- [x] Run focused and full checks, independent code review, and local runtime/UI fixture verification.
- [x] Phase D: Keep the audit trail.
- [x] Phase E: Verify and hand back.

Throughput checkpoint.
- Blocking first steps. Preserve the current dirty tree, then freeze catalog/coverage API before UI work.
- Independent workstreams. One backend owner and one UI owner in separate worktrees. Primary owns runtime fixture and integration.
- Shared mutable state. Workers never write the primary checkout or each other's checkout. Database writes use constraints and core ownership.
- Smallest safe decomposition. Backend is one coupled unit; UI consumes frozen read contracts. No new scanner engine.

User-reported workflow regression.
- [x] Stop generic page flags and simple navigation from adding workflow rows.
- [x] Keep named workflows and saved results; exclude stray legacy rows from active counts.
- [x] Reproduce and verify with in-memory service tests. Ten tests passed; independent source review found no further issue.

Consumer review closure required before completion.
- [x] Deep exact child scope and execution-based child completion.
- [x] API deferred drain and resume use API run kind.
- [x] Semantic handoff revisions reject nonce-only changes and admit supported baseline changes.
- [x] All conflict callers carry method/body/state and ordered actors.
- [x] POST body identity stays exact through baseline, selection, execution, and result.
- [x] Selected-object finding creates no synthetic crawled page.
- [x] Recon and gaps use the same root mapping as completion.

Final startup recovery.
- [x] Reproduce partial migration on a read-only backup of the user database.
- [x] Reconcile partial DDL and interrupted batch tables without replacing saved rows.
- [x] Reproduce and fix batch rebuild failure with foreign keys enabled and saved child rows.
- [x] Verify automatic recovery through the actual launcher on a fresh database copy.
- [x] Run final full backend suite and independent review of final migration source.

Final verification completed. Backend suite passed 2,314 tests. Frontend suite passed 378 tests, lint, type checks, and build. Independent final migration review passed. Actual `uv run aespa` resumed the previous revision on the private database copy, returned HTTP 200, stayed running, and passed quick_check and foreign_key_check. Fixture processes were stopped and worktrees archived.
