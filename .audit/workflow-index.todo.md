- [x] `how` over the affected subsystem.
- [x] `architect` for parallel design exploration.
- [x] Blocking first steps. Read current dirty source, compare normalized inventory with derived inventory, choose identity before delegation.
- [x] Independent workstreams. Read-only design exploration in parallel; one isolated writer owns coupled backend/UI changes.
- [x] Shared mutable state. Implementation uses isolated snapshot checkout under /private/tmp, preserving current workspace changes.
- [x] Smallest safe decomposition. One writer owns inventory, coverage and notifications because their identity/status contracts are coupled.
- [x] Delegate code-writing to a subagent using your configured feature model.
- [x] Verify on the matching surface. 115 backend tests, 370 frontend tests, lint, typecheck, build, real UI import/reload and notification drawer.
- [ ] Rebase into small, ordered commits. Stack follow-ups.
  skip: Local implementation requested; preserve existing uncommitted work, no main-workspace commits.
- [x] If the design is contested, `interrogate` before shipping.
  skip: Design judge and independent final reviewer agreed on the final shape; no shipping requested.
- [ ] Run **Opening a PR**.
  skip: Local implementation requested, no publishing requested.
