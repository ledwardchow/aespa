# Refactor implementation plan

Prepared 5 September 2026 against the current working tree, including the frontend folder cleanup. Implementation is recorded below; the original sequence remains as the reference for review. It follows [the frontend cleanup plan](frontend-cleanup-plan.md) without replacing its history.

## Implementation record

Implemented 5 September 2026. The existing frontend folder structure was retained.

| Area | Result |
| --- | --- |
| Component ownership | `TestRunDetail` keeps run metadata and its event subscription. `FindingsDataProvider` holds shared findings/status data; the mounted findings panel owns editing, grouping, resizing, and file interactions. `WebRunChatProvider` holds chat sessions and panel expansion. Activity log, agent display, and specialist display are separate components. |
| Findings UI | Web and API tabs use `FindingEditor`, `FindingDetails`, and `FindingFileControls`. A typed editor hook preserves their different editable fields and keeps drafts after failed saves. |
| Backend routes | `crawl_archives.py` owns archive serialization, validation, restoration, and completion persistence. `run_graph.py` constructs the stored sitemap. `campaign_activity.py` handles activity ordering and reconnect cursors. Routers retain HTTP decoding and error mapping. |
| Settings | Provider CRUD, profile CRUD, integration persistence, and shared values live in `settings_providers.py`, `settings_profiles.py`, `settings_integrations.py`, and `settings_values.py`. The settings router calls these owners directly. Resolution, discovery, and configuration import/export stay in `settings.py`. |
| API types | `shared/api/findings.ts` owns typed finding reads and edits with explicit web/API identity. The editor hook, editor, details, and file controls are checked TypeScript. Other endpoint modules remain JavaScript as part of the incremental adoption described in step 5. |
| CSS | The old `run.css` is split into run header/layout, shared findings/activity, and web intelligence/attack-surface styles. The shared editor uses a CSS Module. `styles/index.css` retains the original section order. |

State and behavior recorded before extraction:

- Findings drafts, expanded groups, widths, activity sub-tabs, and log expansion survived web-run tab switches. Their owners remain mounted to preserve that behavior. Switching runs remounts the run providers.
- Findings and validation data have a stable provider because the route's event subscription also writes to them. Existing findings and validation polling intervals remain 4 and 3 seconds respectively; this change does not combine or retime the existing refreshes.
- Chat sessions, replay, input, resizing, and popout-close handling retain a stable run-scoped owner. The route consumes only the chat state/actions required by its header and findings interactions.
- Web and API editors retain separate field sets: web edits include likelihood and CVSS; API edits include OWASP API category and evidence. Shared numeric conversion applies only to web edits.
- Archive record restoration retains rollback on invalid records. Import completion retains its original commit location. Graph filtering, metadata redaction, and activity cursor ordering were moved without changing their algorithms.

Compatibility exports remain deliberately in `services/settings.py`: runtime services, console code, and existing tests still import that interface. Provider/profile/integration implementations import their dependencies directly and do not import back into the facade. The old web/API finding read/edit names also remain as forwarding functions for JavaScript callers. Remove these only when their remaining consumers are migrated; no duplicate implementations remain.

Validation added: shared editor save/retry/cancel/pending-state tests; typed endpoint identity and abort-signal tests; archive rollback and invalid-input service tests; browser checks for a populated finding deep link, draft retention across tabs, web/API IDs that match, cancellation, save, and activity-tab bounds. Browser tests use synthetic fixtures and installed Chrome against the production preview. Screenshots are stored outside the repository.

The initial frontend baseline passed 67 tests; the affected backend baseline passed 106 tests. Final checks passed: 1,324 backend tests, 72 frontend unit/component tests, all 42 production browser cases (40 navigation cases plus 2 findings cases), frontend formatting/lint/type/architecture/build checks, and repository Ruff checks. The backend suite required loopback access for its startup tests. New tests do not use a populated local database or execute scans. Native packaging and cached service-worker upgrades remain separate release checks.

## Scope and order

The work covers component ownership, shared findings UI, backend read/import/export services, settings organization, API types, and CSS ownership. Preserve product behavior, existing URLs, response formats, storage keys, and database schema. Scan execution, agent instructions, and provider execution behavior are outside this plan.

| Step | Deliverable | Dependency | Relative size |
| --- | --- | --- | --- |
| 0 | Record behavior and add missing regression coverage | None | Small |
| 1 | Move local state into findings and activity components | Step 0 | Large |
| 2 | Share findings editor, details, and file controls | Step 1 | Medium |
| 3 | Extract data processing from backend routers | Step 0 | Medium per extraction |
| 4 | Separate settings persistence and configuration responsibilities | Step 0 | Medium per extraction |
| 5 | Type endpoint modules and affected consumers | Start with steps 1 and 2; finish after response contracts are confirmed | Medium |
| 6 | Move panel CSS beside its owners | Steps 1 and 2 for affected panels | Medium |

These sizes describe scope, not elapsed-time estimates. Complete the frontend ownership changes first. Backend extractions can be reviewed independently. Introduce types and move CSS with a component when doing so makes the change easier to review; avoid a repository-wide conversion.

## 0. Establish the behavior baseline

1. Record existing uncommitted changes before implementation. Keep unrelated changes intact and review each patch against this baseline.
2. Inventory state in `TestRunDetail`, `useFindings`, `WebRunFindingsTab`, and `WebRunActivityTab`. For each value, record its readers, writers, persistence, and expected lifetime across tab switches and run navigation.
3. Identify which displayed data is updated by the route's event subscription and which is polled. Record the existing refresh intervals and ordering rules.
4. Extend the existing Vitest and Playwright fixtures only where coverage is missing. Existing route smoke tests establish rendering, but do not by themselves prove editing or state preservation.
5. Run the existing frontend checks and affected backend tests. Record pre-existing failures separately from refactor regressions.

Required fixture cases: populated and empty findings, failed save, cancelled edit, direct finding links, tab switching, navigation between runs, and web/API runs with the same numeric ID. Use synthetic data, mocked HTTP responses, and simulated display events. Do not start scans or call live providers.

Done when the ownership inventory and relevant baseline checks are recorded with the implementation change.

## 1. Move state into the components that use it

Starting points: `frontend/src/features/web-runs/TestRunDetail.jsx`, `useFindings.js`, `WebRunFindingsTab.jsx`, and `WebRunActivityTab.jsx`.

`useFindings` already contains much of the findings behavior, but the route destructures it and forwards dozens of values and setters. Moving the hook unchanged into a conditionally mounted tab could alter background updates and discard drafts. Settle those lifetimes before moving state.

1. Separate shared server data from local interaction state. Keep run-wide data and the existing event subscription under one stable owner.
2. Move finding edit drafts, save/cancel interactions, row expansion, grouping controls, and column resizing into the findings feature components or focused hooks.
3. Give cross-panel updates explicit callbacks or a narrowly scoped run-data context. Use context only where several descendants actually share the data. Avoid exposing every setter through a replacement object.
4. Split activity presentation into log, agent display, and chat layout components. Move local expansion and sizing state with their views. Preserve the existing chat transport and session owner.
5. Keep owners mounted where state currently survives tab changes, or retain that state in a stable feature controller. Preserve current reset behavior on run navigation.

Validation: edit/save/cancel behavior, draft lifetime across tab switches, expansion and width preferences, background display updates, and subscription cleanup on navigation. Confirm web/API identity isolation with matching numeric IDs.

Done when the route composes panels without forwarding their local setters, each displayed resource has one owner, and tab navigation preserves the established behavior. File length and prop count are review signals, not acceptance thresholds.

## 2. Share findings UI

Starting points: the web and API findings tabs and `frontend/src/shared/findings/`.

1. Compare editable fields, defaults, status labels, grouping, and expansion behavior in both tabs. Record differences that must remain.
2. Add shared typed components for the finding editor and common details. Keep the draft and local form interactions with the editor; receive saved data and save/cancel callbacks through small contracts.
3. Extract common file-selection and export controls around the existing parsing and formatting utilities. Keep endpoint calls and refresh behavior in each feature.
4. Migrate the web tab first, then the API tab. Remove duplicated UI only after both consumers use the replacement.
5. Keep web-specific grouping and API-specific presentation in their features. Do not add numerous mode flags to force different tables into one component.

Validation: editing every supported field, failed saves retaining drafts, cancellation restoring saved values, direct-link expansion, and Markdown import/export compatibility. Check that each feature calls its own endpoint and refreshes the correct run.

Done when common editors and details have one implementation, their interaction tests exercise both consumers, and feature-specific behavior remains explicit.

## 3. Extract data processing from routers

Starting points: `src/aespa/api/test_runs.py` and `src/aespa/api/applications.py`.

Use separate changes for these boundaries:

- Crawl archive serialization and import persistence, currently mixed into `test_runs.py`.
- Sitemap graph queries and response construction.
- Campaign activity queries, ordering, and cursor handling.

1. Inspect existing service modules and tests before adding files. Reuse an appropriate owner rather than introducing a second implementation.
2. Move pure conversion and query helpers first. Keep HTTP request decoding, upload handling, response selection, and HTTP error mapping in the router.
3. Move the remaining database work into focused services with explicit inputs and return values. Preserve session ownership, flush/commit boundaries, and rollback behavior.
4. Keep existing archive fields, redaction, validation rules, graph output, and activity cursor behavior unchanged. Treat any newly discovered behavioral defect as a separate fix.
5. Update callers and tests. Avoid service imports back into API modules.

Validation: archive round trips using synthetic records, malformed-input rejection, rollback without partial imports, equivalent graph output, and activity ordering and reconnect cursors. Exercise colliding run IDs wherever shared tables are queried. Retain HTTP tests to verify status codes and response contracts.

Done when these handlers mainly translate HTTP input/output and the extracted behavior can be tested through services without a live server. No schema migration should be needed.

## 4. Separate backend settings responsibilities

Starting point: `src/aespa/services/settings.py`. Read the configuration sections of `docs/architecture.md` before implementation.

1. Map public callers, internal dependencies, and test monkeypatch targets. Distinguish provider connections, saved model profiles, and role-based profiles by their model names; the current names are easy to confuse.
2. Move provider CRUD and serialization into a focused module, then saved-profile CRUD, then integration configuration persistence. Choose final module names after checking existing `model_discovery.py` and `resolved_llm_config.py` ownership.
3. Keep configuration resolution and provider execution behavior unchanged. Preserve defaults, secret masking, activation rules, and configuration snapshots.
4. Retain explicit compatibility exports in `settings.py` while migrating imports. Check callers and patch targets before removing each export. Avoid wildcard re-exports and circular imports.
5. Move one responsibility per reviewable change. Keep transaction boundaries unchanged.

Validation: existing settings API and resolved-configuration tests, plus focused coverage for activation, duplicate names, deletion of referenced records, masked output, and integration save/read round trips. Stub discovery calls where existing tests require them.

Done when settings responsibilities have clear owners, existing callers and tests use the intended boundary, and compatibility exports have either been removed or listed with their remaining consumers.

## 5. Type API modules and their consumers

Starting points: `frontend/src/shared/api/request.ts`, the adjacent JavaScript endpoint modules, and `frontend/tsconfig.json`.

1. Start with finding response/update contracts and run identity needed by steps 1 and 2. Match backend schemas, including nullability and fields omitted from updates.
2. Convert one endpoint module at a time to TypeScript, supplying the response types to `req<T>` and typing request bodies.
3. Convert affected data hooks or components alongside those modules. Typed wrappers alone provide limited protection while their consumers remain unchecked JavaScript.
4. Distinguish JSON responses from empty responses, file downloads, and multipart uploads. Preserve the request helper's error behavior.
5. Maintain explicit contracts initially. Evaluate deterministic generation from local OpenAPI only if maintaining the contracts becomes substantial work; generation must not require a populated database or running scan.
6. Keep `unknown` at untrusted boundaries and narrow it where needed. Do not use broad `any`, blanket suppressions, or enable `checkJs` across the whole legacy tree in one change.

Validation: `npm run typecheck`, transport tests, and affected component tests. Verify that nullable responses are handled and invalid request fields fail type checking. Types do not replace runtime input validation.

Done per module when request/response contracts and at least their affected consumers are checked, with no untyped escape added to silence errors.

## 6. Move CSS to its owners

Starting point: `frontend/src/shared/runs/run.css`.

1. Inventory selector consumers, import order, dynamically constructed classes, and rules shared across run kinds.
2. Extract one panel at a time after its component ownership is settled. Put shared finding styles with shared findings components and feature-specific styles beside their feature.
3. Use CSS Modules for migrated local styles where practical. Retain genuinely shared layout rules globally.
4. Move declarations without redesigning them. Keep specificity and cascade order equivalent during extraction; remove obsolete rules only after checking all consumers.
5. Preserve full-width nested tab wrappers, sticky headers, panel resizing, and overflow behavior.

Validation: inspect built pages at desktop and narrow widths, capture screenshots, and compare computed bounds of nested tab bars with their parents. Check findings, activity, API runs, and campaign consumers affected by shared selectors. Verify focus indicators and horizontal scrolling.

Done when migrated selectors have an identifiable owner and affected pages retain their layout. A shorter shared stylesheet alone does not establish completion.

## Checks and delivery

For each substantive frontend change, run `npm run check` from `frontend/` and the affected Playwright tests. The check command includes formatting, lint, architecture checks, type checks, unit tests, build, and generated-output checks. Inspect compiled production pages for CSS changes, using the existing production-preview browser configuration.

For backend extractions, run affected pytest files and Ruff checks. Existing starting points include `tests/api/test_applications.py`, `tests/api/test_settings.py`, and `tests/providers/test_resolved_llm_config.py`; locate archive and graph coverage by behavior before adding tests. Run the full backend suite after the backend changes are integrated. Tests use isolated data and mocked external calls.

Suggested review sequence:

1. Baseline cases and ownership notes.
2. Findings state ownership with the minimum typed contracts.
3. Activity presentation and local state ownership.
4. Shared findings editor/details and file controls.
5. Archive service extraction.
6. Graph and campaign activity extraction, separately if needed.
7. Settings modules, one responsibility at a time.
8. Remaining API type adoption, one module and its consumers at a time.
9. Remaining CSS extraction and visual checks.

Keep file moves distinguishable from behavior changes. Rebuild generated frontend assets through Vite. Apply the repository version rule on implementation turns with substantive code changes; this documentation-only plan does not require a version bump.

Each change should report what moved, which behavior was preserved, tests actually run, and remaining limitations. Update the frontend development notes when ownership conventions change. Keep changes independently revertible and do not combine a schema change, visual redesign, or new dependency with these extractions.
