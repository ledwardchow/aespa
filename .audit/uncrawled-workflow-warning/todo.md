- [x] Trace shared fresh-start and separate resume handlers.
- [x] Choose one pre-start check with latest workflow notes and an accessible dialog.
- [x] Implement warning, confirm/cancel/review actions, and behavior tests in an isolated worktree.
- [x] Integrate, run frontend checks/build, and drive the real local browser journey.
- [x] Independent review, cleanup, and hand back.

Blocking first steps. Inspect fresh-start/resume and workflow retry semantics before editing.
Independent workstreams. UI owner implements in its worktree; primary owns runtime verification and release notes.
Shared mutable state. No shared source writes; integrate only after owner stops.
Smallest safe decomposition. One UI owner keeps handler, dialog, and tests together.

Design. Read current workflow notes at each fresh-start click. Non-superseded notes that have not reached crawled state trigger a modal. Preserve action kind and scan mode until confirmation. Cancel does nothing, View workflows opens the workflow list, and confirmation dispatches the original new-scan action once. Resume bypasses this path. Failed preflight fetch shows the error without starting silently.

Verification completed. All 389 frontend tests passed, along with lint, typecheck, architecture, build, build-contract, formatting of changed files, and diff checks. Independent source review passed. A real local UI/API journey checked cancel, Escape, workflow navigation, combined-start warning, selected-mode confirmation, one actual start request, and resume without a warning. Screenshots checked at 1440px and 736px. Local target/model mocks excluded real external systems. Prove It Works determined the real UI check; the shared start boundary keeps every new-scan caller consistent. No commit or PR requested.
