# Frontend development

AESPA's UI is a React application built with Vite. Use Node 24 for the same environment as CI. The lockfile is committed; use `npm ci` on a fresh checkout.

Run these commands from `frontend/`:

```sh
npm ci
npm run dev          # Vite, with /api forwarded to localhost:8000
npm run check        # formatting, lint, boundaries, types, tests, build, asset checks
npm run test:watch
npm run test:e2e     # browser checks with local fixtures
npm run format
```

Run the backend separately with `uv run aespa` from the repository root. Use the Vite URL during UI development. The backend serves the compiled bundle, so source edits appear there only after a build.

`npm run build` writes directly to `../src/aespa/web/`. Commit those generated files alongside UI changes. Never edit them manually. Startup also checks source, public assets, the HTML entry, package files, and Vite configuration for changes requiring a rebuild.

## Finding code

| Directory | Responsibility |
| --- | --- |
| `src/app` | Application shell, sidebar, route loaders, preferences, page error recovery |
| `src/features` | Screens and their local components, state, and interactions |
| `src/shared/api` | HTTP transport plus endpoint modules grouped by domain |
| `src/shared/navigation` | Hash parsing and shared link builders |
| `src/shared/ui` | Reusable UI such as tabs, headers, badges, and traffic display |
| `src/shared/runs`, `findings`, `leads`, `sessions` | Common run display and file conversion code |
| `src/shared/alice` | Chat rendering, parsing, and existing session transport |
| `src/shared/hooks` | Generic browser behavior, polling, incremental collections, resizing |
| `src/styles` | Global tokens, base styles, layout, and the stylesheet import order |
| `src/test`, `e2e` | Unit/component setup and browser fixtures |

The old `pages`, `components`, and catch-all `lib` directories have been replaced. Web runs, API runs, SAST runs, collections, sites, settings, applications, and campaigns each have an owner under `features`.

Imports flow from app to features to shared code. Shared modules cannot import features or app. Features cannot import another feature's private files. A small `public.js` module may expose a deliberate integration, such as the campaign list embedded in an application. `npm run check:architecture` enforces these rules and rejects cycles and missing imports. Add `-- --inventory` to inspect reachability and cross-feature dependencies.

Keep local state, handlers, and effects with the component that owns the interaction. The settings lists own sorting; forms own drafts; SAST views own table/menu interactions; the API chat panel owns chat state. Avoid replacing a large component with a hook that exposes all of its internal setters.

## Routes and state

`app/routes.jsx` maps parsed route names to direct lazy imports, props, and sidebar sections. `shared/navigation/parseRoute.ts` handles existing hash URLs and query references. Keep hash URLs compatible with copied links, desktop windows, and browser history. Web and SAST tab selection comes from the URL, so back/forward works without resetting the rest of the screen.

Use `runHref` for new run links. Shared run identities include both kind and ID; numeric IDs alone are not unique across web, API, and SAST runs.

Server responses, form drafts, URL state, and browser preferences have separate owners. Use `shared/api/request.ts` for JSON and multipart requests. `importJson` accepts already serialized JSON. All transport errors preserve HTTP status, including plain-text proxy failures. Forward an abort signal when a request should end with its component.

`usePolling` passes an abort signal to its loader and skips overlapping ticks for that loader. Cleanup aborts the signal; loaders must forward or inspect it to discard their own late responses. `useIncrementalCollection` additionally discards responses from an older loader/reset and deduplicates records. `useEventStream` owns reconnect timers and visibility handling. Chat cursor replay uses its separate session transport; preserve that protocol when editing presentation code.

## Styles and types

Shared and feature styles are owned by the corresponding directory. `styles/index.css` explicitly preserves their cascade order. Use CSS Modules for new local component rules, as in `ScanPolicyPage.module.css`, and retain computed dimensions as inline values where appropriate. Moving CSS must preserve the parent layout, scroll containers, and selector order. In particular, Agent Settings has 16px content padding while the generic tab bar assumes 28px.

TypeScript checks the new transport, navigation contracts, run identity, and tab component. Existing JavaScript remains supported with `allowJs`; it has not all been converted or type checked. Use typed contracts for new shared boundaries and convert existing modules as their data contracts are clarified. `tsc --noEmit` is separate from the Vite build.

## Browser checks

The browser suite intercepts API requests with deterministic fixtures. It must not depend on your database, send live LLM requests, or start scans. It checks route rendering, console errors, settings interactions, run-tab history, errors, narrow layouts, and nested tab bounds.

Install Chromium once:

```sh
npx playwright install chromium
npm run test:e2e
```

To use an already installed Chrome, set `AESPA_CHROME_PATH` to its executable. `AESPA_UI_TEST_URL` selects an existing local test server. Set `AESPA_UI_TEST_BUILD=1` to run against the compiled bundle through Vite preview after `npm run build`. CI exercises development and production builds. Screenshots and failure artifacts are written to the system temporary directory.

Unit and component tests are discovered as `src/**/*.test.{js,jsx,ts,tsx}`. Keep tests beside the code they cover. Use Vitest and Testing Library for behavior and Playwright for real layout and navigation; large JSX snapshots are not a substitute for interaction checks.

## Production assets

FastAPI and desktop packaging currently expect `app.js`, `styles.css`, `index.html`, and public assets in `src/aespa/web`. The entry and stylesheet use a server-injected version query; other chunks use content hashes. Vite collects all styles into one file so lazy routes cannot overwrite the fixed CSS filename. `check:build` verifies the HTML references and emitted chunk dependencies.

Service-worker registration runs only in production. If an earlier build registered a worker on your Vite origin, unregister it in browser developer tools and clear that origin's site data once. Normal development then uses Vite's live modules.

The existing production cache strategy and fixed entry filenames remain in place. Changing them requires a separate upgrade test with an old cached shell and checks of FastAPI and packaged desktop builds. The fixture suite blocks service workers and does not verify offline behavior or native installers.
