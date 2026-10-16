# Coverage findings navigation

- [x] `how` over the affected subsystem.
- [x] `architect` for design exploration. Independent read-only comparison checked the chosen shape. Selected existing Findings tab over a separate coverage-only table to retain finding tools and detail pages.
- [x] Write the throughput checkpoint as four todo items.
  - Blocking first steps. Inspect web/API marker handlers, route parser, run containers, findings table.
  - Independent workstreams. One isolated implementation worker; parent owns changelog, version, browser verification and integration.
  - Shared mutable state. Worker uses its own worktree. Original workflow edits remain in parent checkout.
  - Smallest safe decomposition. One worker owns the coupled web/API route and findings changes.
- [x] Delegate code-writing to a subagent using your configured feature model.
- [x] Verify on the matching surface. 368 frontend tests, 3 coverage browser journeys, 2 existing finding editing browser journeys, lint, typecheck, architecture, build checks passed.
- [ ] Rebase into small, ordered commits. skip: user requested local changes, no commit needed.
- [ ] If the design is contested, `interrogate` before shipping. skip: existing Findings table matches requested behavior.
- [ ] Run **Opening a PR**. skip: user requested local changes.
