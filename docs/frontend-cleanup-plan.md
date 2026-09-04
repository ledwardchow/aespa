# Frontend cleanup plan

Reviewed 5 September 2026. This is an implementation plan, not a completed refactor.

The goal is a frontend where a developer can find a feature, change its behavior, and test it without understanding the former monolithic application. Keep the existing product behavior and URLs while establishing clear component ownership, reliable state handling, and a predictable Vite development workflow.

## What the current code shows

The frontend already uses React 19, Vite 8, StrictMode, lazy imports, shared components, and several focused hooks. These are useful foundations.

| Area | Evidence | Cleanup needed |
| --- | --- | --- |
| Settings dependencies | `Settings.jsx` imports form components which import conversion functions back from `Settings.jsx`. Provider constants live in `BurpRestApiSettings.jsx`; specialist defaults live in `UpstreamProxySettings.jsx`. | Remove cycles and give constants and conversion functions appropriate owners. |
| Large page modules | `SiteDetail.jsx` is 904 lines and includes both site detail and run detail. `Settings.jsx` is 606 lines. `SastRuns.jsx` is 534 lines and includes `LegacySastRunDetail`. | Separate route components, feature logic, and compatibility code. Verify reachability before deleting legacy exports. |
| Cross-feature imports | API sessions import the web sessions panel; API leads import the web leads tab; campaign findings import column resizing from web helpers; web coverage imports constants from API endpoints. | Move genuinely shared behavior out of page internals. |
| Chat UI | `aliceRender.jsx` is 831 lines, `useAliceChat.jsx` is 592, and `ApiRunAgentsTab.jsx` is 675. | Separate parsing, rendering, session persistence, and transport lifecycle. Preserve protocol behavior. |
| API access | `lib/api.js` contains a single 327-line object, a request helper, and several direct-fetch variants. The request helper currently does not forward an abort signal. | Give feature endpoints owners and unify transport behavior. |
| Navigation | `lib/router.js` parses hashes through a sequence of regular expressions. `App.jsx` separately selects pages and sidebar states. Lazy imports load groups of page exports. | Define routes and link builders centrally, with direct imports of route modules. |
| Styles | `styles.css` has 2,102 lines and `styles/run.css` has 1,186. All four stylesheets are imported by `main.jsx`. | Separate shared foundations from feature styles and make cascade dependencies explicit. |
| Validation | ESLint explicitly checks undefined identifiers; oxlint also runs. Four explicitly listed test files contain 14 passing tests. `check` runs lint and build, but not tests. | Add hook, component, route, and browser coverage; make one complete verification command. |
| Build integration | Fixed `app.js` and `styles.css` names, a version-placeholder plugin, custom chunk groups, and a service worker work with FastAPI asset serving. | Treat these as a deployment contract that needs testing before simplification. |

Baseline checks passed: `npm run lint`, `npm test` (14 tests), and a production build written to a temporary directory. The temporary build avoided overwriting existing generated assets in the working tree. Output included 110.88 kB CSS, 138.09 kB common JavaScript, and 177.70 kB SiteDetail JavaScript before gzip. These are file sizes, not measured initial-page transfer costs.

This review covered structure and representative implementations. It did not include rendered-page QA, a complete dependency graph, or live-run testing. Several files already have uncommitted changes, including `lib/api.js`; implementation must preserve that work.

## Target structure and rules

Use feature folders with small route entry points. Introduce directories when there is code to put in them.

```text
frontend/
  src/
    app/
      App.jsx
      AppShell.jsx
      Sidebar.jsx
      routes.js
      navigation.js
      preferences.js
    features/
      sites/
      web-runs/
      api-collections/
      api-runs/
      sast-runs/
      applications/
      campaigns/
      settings/
      active-jobs/
      statistics/
    shared/
      api/                 # request transport and errors
      ui/                  # tabs, fields, dialogs, loading states
      hooks/               # generic browser and React behavior
      runs/                # shared run identity and display helpers
      findings/            # shared finding display and file conversion
      leads/
      sessions/
      alice/               # shared chat UI and existing session protocol
      lib/                 # small, named generic utilities
    styles/
      tokens.css
      base.css
      layout.css
    test/
      fixtures/
      setup.js
    main.jsx
```

A feature can contain route components, components, hooks, API functions, model/conversion functions, tests, and styles. Avoid empty layers or a directory per trivial function.

- `app` composes features. Features use shared modules. Shared modules never import pages or features.
- Features may use another feature's deliberately exported contract, but not its internal tabs or hooks. Prefer moving truly common functionality into a named shared domain.
- Route components resolve parameters and compose screens. They do not implement every table, form, and request lifecycle.
- A component owns its local interactions. Extract its state, handlers, and effects with its JSX. Avoid replacing a large page with a large hook returning dozens of setters.
- Keep server responses, editable form drafts, URL state, and display preferences separate. Derive values instead of storing duplicate copies.
- Generic UI components take data and callbacks. They do not know API endpoints or run kinds.
- Run-scoped caches, storage keys, and subscriptions use both run kind and ID. Web and API IDs can collide.
- Use named module files such as `providerForm.js`, `columnResize.js`, and `runStatus.js` instead of growing `_helpers` or `utilities` files.

React's guidance supports hooks organized around concrete behavior and avoiding redundant state: [custom hooks](https://react.dev/learn/reusing-logic-with-custom-hooks) and [state structure](https://react.dev/learn/choosing-the-state-structure).

## Implementation sequence

### 1. Establish the checks and behavior baseline

1. Inventory routes, tab aliases, query parameters, browser storage keys, exports, and feature dependencies. Generate a cycle report and identify unreachable modules from actual entry points.
2. Capture representative screens with deterministic local fixtures: lists, settings, web/API/SAST run tabs, campaigns, and the chat popout. Include loading, empty, error, and populated states.
3. Add component and hook testing with a DOM-capable runner. Choose one runner for new frontend tests and migrate the existing Node tests when practical. Test discovery must include newly added files automatically.
4. Add browser smoke tests with mocked API responses and simulated events. Tests must not launch scans, call live LLMs, or need a populated local database.
5. Enable hook correctness and dependency checks, import-cycle checks, and basic accessibility checks. Fix existing findings in bounded commits rather than adding blanket suppressions.
6. Make `check` include lint, tests, type checking once introduced, and build. Add pull-request CI, a pinned supported Node version, and `npm ci`.

Completion: current routes have a baseline, failures are repeatable locally, and CI catches broken imports, hooks, and critical interactions. Keep new tests focused on observable behavior rather than snapshots of large JSX trees.

### 2. Clean up Settings as the first feature

1. Move defaults, labels, and form conversions into pure modules within settings, organized by provider/profile/integration responsibility.
2. Remove every child-to-`Settings.jsx` import. Move provider metadata out of the Burp component and specialist defaults out of the proxy component.
3. Separate the settings route, provider list, profile list, and their forms. Preserve the existing save and connection-test behavior.
4. Give each form its own draft, validation, pending state, and error handling. Keep saved server data separate from unsaved edits.
5. Move `ScopeHostsPanel` to a shared location if its confirmed consumers need the same behavior.

Completion: no settings import cycles; form conversion tests cover empty values, defaults, number conversion, and edit/save round trips; visible tabs and form behavior match the baseline.

### 3. Establish routing and the application shell

1. Extract `AppShell`, `Sidebar`, preferences, and application metadata loading from `App.jsx`.
2. Define route matching, page loaders, tab validation, sidebar grouping, and link builders in a single routing area. Keep existing hash URLs, finding/lead links, aliases, and popout URLs.
3. Load actual route modules directly instead of importing whole feature barrels and selecting named exports.
4. Handle invalid routes and failed lazy imports explicitly. Provide route-level error recovery and a consistent loading state.
5. Document which navigation changes preserve state and which remount a page. Preserve tab state, drafts, scroll behavior, and intentional `key` behavior.

Default decision: retain hash routing during cleanup. A router package can replace the parser later if nested layouts and route tooling justify it; adopting one is not required to organize this code.

Completion: direct links, refresh, back/forward, tab aliases, query references, sidebar selection, and popout navigation pass tests.

### 4. Separate API transport and data ownership

1. Move request execution, response decoding, and error normalization to `shared/api`. Preserve the recently changed handling of non-JSON error responses.
2. Move endpoint functions into their owning features or shared domains. Keep a temporary compatibility export so migration can proceed one consumer at a time, then remove it.
3. Support abort signals, JSON, multipart uploads, empty responses, and consistent error objects. Do not set a JSON content type for multipart bodies. Keep download and stream URL construction explicit.
4. Introduce feature-specific data hooks with narrow responsibilities. Give each displayed resource a documented owner and refresh policy.
5. Audit overlapping requests, responses arriving after navigation, event-triggered refreshes, and polling cleanup. Preserve existing refresh cadence and event contracts during extraction.
6. Consolidate polling and EventSource lifecycle where semantics match. Keep specialized chat streaming separate where cursor replay or transport behavior differs. Test cleanup under StrictMode, visibility changes, disconnection, and remounting.

Default decision: keep local React state and focused hooks initially. Consider a server-state library only after documenting repeated cache and invalidation needs. Do not introduce a global store for every form and tab.

Completion: transport behavior is tested; migrated screens have one clear resource owner; stale responses cannot overwrite another run's screen; run identity remains isolated across kinds.

### 5. Refactor the remaining screens by responsibility

Use separate changes for each feature:

| Order | Scope | Intended result |
| --- | --- | --- |
| 1 | Sites and web-run route entry points | Split `SiteDetail.jsx` into site detail and run detail. Keep list editing with the site screen; move run-specific UI into web-runs. |
| 2 | Findings, leads, sessions, coverage display | Remove API-to-web and campaign-to-web internal imports. Share tables, formatting, and interaction hooks only where behavior matches; keep endpoint access in adapters. |
| 3 | Web activity and sitemap | Separate list selection, resizing, graph lifecycle, event presentation, and tab composition. Keep D3 DOM ownership inside its graph component and clean up simulations/listeners. |
| 4 | API collections and run screens | Separate collection CRUD, files, endpoints, and run display. Keep form state with forms and tab state with navigation. |
| 5 | SAST | Split list/form/detail modules. Check references to `LegacySastRunDetail`, progress, and leads exports; remove only unreachable compatibility code after preserving aliases. |
| 6 | Applications and campaigns | Preserve existing focused hooks such as `useCampaign` and `useTargets`; split review-table interactions and wizard steps where ownership is still mixed. |
| 7 | Chat presentation | Split `aliceRender.jsx` into pure parsers and rendering components. Separate session persistence from UI interactions in the web and API chat screens. Preserve message order, replay, active-tab selection, and popout behavior. |
| 8 | Remaining small pages and utilities | Standardize Active Jobs and Statistics, split report/file/date/storage utilities, and remove temporary compatibility exports. |

Completion for each feature: no imports of another page's internals, no giant prop bag, relevant interaction tests pass, and the rendered screen matches its baseline. File size is a review signal, not a pass/fail metric. Keep existing agent instructions and backend execution behavior unchanged.

### 6. Make styles and shared UI maintainable

1. Inventory global selectors and their consumers before moving CSS. Record cascade order and dynamically constructed classes.
2. Retain tokens, reset/base rules, and app layout globally. Move feature rules next to their owner, using CSS Modules for new or migrated local styles.
3. Extract repeated tabs, fields, alerts, dialogs, table controls, and resizable panels when real consumers share behavior. Preserve semantic HTML and keyboard interactions.
4. Replace repeated static inline styles with classes. Keep computed widths, coordinates, and other truly dynamic values inline or in CSS variables.
5. Remove obsolete selectors after source and visual checks. Do not delete classes based only on a text search.
6. Verify focus handling, accessible names, dialog dismissal, tab semantics, and overflow behavior while migrating components.

Completion: feature styles have identifiable owners; shared UI has focused interaction tests; desktop and narrow layouts match baselines. For nested tab bars, inspect computed bounds and screenshots, especially Agent Settings and the full-width run panels. Check gutters, horizontal clipping, sticky headers, split panes, and scrolling.

CSS Modules are supported directly by Vite. See [Vite features](https://vite.dev/guide/features.html#css-modules).

### 7. Add types incrementally

Adopt TypeScript for API contracts, run identity, event payloads, conversion functions, and shared component props first, then migrate features as they are cleaned up. Enable strict checks for migrated code while temporarily allowing existing JavaScript. Avoid widespread `any` or one large conversion commit.

Decide whether API types should be generated from a reproducible local OpenAPI snapshot or maintained explicitly. Generated output must be deterministic and must not require a running scan or expose stored configuration values. Use discriminated types for run kinds and events where useful.

Completion: migrated boundaries are type checked in CI, existing JavaScript still works, and public interfaces do not rely on untyped catch-all objects. Types complement tests for incoming data; they do not validate responses at runtime.

Vite transpiles TypeScript without checking types, so this needs a separate `tsc --noEmit` step. See [Vite TypeScript support](https://vite.dev/guide/features.html#typescript).

### 8. Simplify the build and release contract

1. Check `htm` usage across source, scripts, and build tooling before removing it. Review `esbuild`, `keepNames`, and custom chunk groups against their actual purpose and measured output.
2. Measure route loading and chunk dependencies before changing grouping. Prefer direct lazy route imports; load graph or other heavy modules with their actual consumers.
3. Preserve the current fixed asset names initially. Evaluate standard hashed entry/CSS assets in a separate change covering FastAPI serving, caching, service-worker updates, and packaged desktop builds together.
4. Audit the forced single CSS filename before introducing multiple asynchronously loaded stylesheets. Confirm every emitted stylesheet remains reachable and correctly loaded.
5. Move service-worker registration into a small owned module and disable registration in Vite development. Provide a documented way to clear previously registered development workers.
6. Test both a fresh install and an upgrade with an old cached shell. Include a failed lazy-chunk request and recovery without losing unsaved work unnecessarily.
7. Keep `src/aespa/web` generated. Build it from `frontend` for release; document how its checked-in outputs are refreshed and verified. Check startup staleness detection against configuration and public-asset changes, not only JSX changes.

Completion: development refresh works, production routes load from FastAPI, cached upgrades work, desktop assets are present, and generated files are reproducible. Keep build changes separate from feature moves so regressions are easier to locate.

## Delivery and acceptance

Use one reviewable change per responsibility. A practical sequence is baseline checks, settings helpers, settings components, shell/routes, transport, then one feature at a time. Add types and scoped styles alongside each migrated feature once their supporting configuration exists. Finish with dependency removal and build simplification.

For each change:

1. Record the affected behavior and its current tests.
2. Separate file moves from behavioral fixes where practical.
3. Run lint, relevant unit/component tests, and the required frontend build.
4. Run browser checks for the routes and interactions touched. Include populated and failure states rather than only successful initial render.
5. Inspect generated output and screenshots. Update the frontend development notes and module ownership guidance when conventions change.
6. Apply the repository's version bump rule for substantive code changes. Documentation-only planning does not need a version bump.

The cleanup is complete when:

- Every route has an identifiable entry component and feature owner.
- No import cycles or shared-to-feature imports remain, and CI prevents their return.
- Reusable components no longer depend on another feature's private tabs or helpers.
- API transport, run identity, browser storage, and event lifecycle have explicit contracts and meaningful tests.
- Critical route, form, list, streaming-display, and navigation behavior is covered with local fixtures.
- Global CSS is limited to shared foundations and intentional application-wide components.
- Maintained modules have checked types, and new work follows the same conventions.
- A clean checkout has documented install, dev, check, build, and browser-test commands in `frontend/README.md`.
- Production serving and cached upgrades pass checks, and built assets come only from the Vite source tree.

Start with Settings. Its circular dependencies are concrete, its screens are bounded, and it can establish the conventions before the more stateful run pages move.
