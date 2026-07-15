# Changelog

All pull requests merged to `main`, in reverse chronological order.

---

## [develop → main] July 15 Update — evidence-driven scanning, bounded completion, unified coverage UI

**Branch:** `develop → main`

### Evidence-driven scan engine

- **Recon is now a live attack-surface projection** (`services/recon_summary.py`, scanner/API/models): the synthetic persisted hypothesis/task graph has been removed. The Test Lead now receives compact, evidence-backed canonical routes, methods, parameters, access observations, provenance, signals, and real OWASP coverage gaps derived from crawl and traffic data.
- **Systematic continuation rules** (`services/prompts/test_lead.py`): web and API Test Leads treat findings and specialist dispatches as milestones rather than exit conditions, continue across the route inventory, and only request completion after input-bearing surfaces have been exercised.
- **Published scan comparisons** (`docs/results/BankOfEd/`): adds July 14 multi-model scan outputs, consolidated vulnerability results, and a model comparison for GPT-5.6, MiniMax M3, Claude Opus 4.8, and Claude Sonnet 5.

### Bounded completion and reliable resume

- **Completion cannot loop indefinitely** (`services/scan_completion.py`, `services/scanner.py`): a bounded policy mediates `done`, permits only limited session/coverage challenges, warns after prolonged inactivity, and automatically stops after 50 tool calls without meaningful coverage, finding, lead, specialist, or session progress.
- **Checkpoint repair** (`services/checkpoint.py`, `services/llm.py`): resumed conversations ending on assistant output or interrupted tool use are repaired with a continuation prompt or matching tool results before being sent to providers that reject assistant-message prefill.
- **Provider diagnostics survive reloads** (`services/llm.py`, activity UI): LLM response/protocol events record provider, model, stop reason, usable content blocks, context size, retry state, and safe Bedrock request/usage metadata, making empty and no-tool responses diagnosable from the run log.

### OWASP coverage and run UI

- **Per-vulnerability-class web coverage** (`services/web_workprogram.py`, models/migration/tests): A03 cells independently track SQL injection, reflected XSS, and stored XSS obligations. Probes declare their test class, while constrained browser `dom_check` assertions record explicit canary pass/fail results without arbitrary JavaScript execution.
- **Unified Attack Surface & Coverage tab** (`frontend/src/pages/SiteDetail/`): OWASP progress and matrix, route/input inventory, evidence signals, access observations, technologies, and Target Intelligence now live under aligned **OWASP**, **Attack Surface**, and **Intelligence** subtabs. The full-width panels keep their scrollbars at the viewport edge.
- **Scrollbar regressions fixed**: Intelligence, Sessions, and the retired Task Graph views correctly expose their internal scroll regions.

### Packaging and documentation

- **macOS notarisation stapling fixed** (`make_dmg.sh`, `notarize_only_mac.sh`): the release flow staples the notarisation ticket correctly before distributing the DMG.
- **Repository documentation refreshed** (`README.md`, `docs/architecture.md`, guides): architecture and scan UI documentation match the new scan model, and the DeepWiki badge links directly to this repository's DeepWiki page.

## [develop → main] July 13 Update — routeless crawling, detached SAST leads, API scan isolation

**Branch:** `develop → main`

### Routeless SPA crawling

- **New routeless crawler mode** (`services/crawler.py`, run models/API/UI): test runs can crawl single-page applications whose meaningful states do not change the browser URL. The crawler records distinct UI states, navigation actions, and state-aware page identities so these applications produce a useful sitemap and dynamic-scan context instead of collapsing into one route.
- **Clearer sitemap identity and ownership** (`SiteDetail/*`, crawler/LLM helpers): scraped-page titles no longer inherit possessive user labels, page metadata exposes crawler mode, and sitemap nodes retain the correct credential/user colouring as live events arrive.

### Standalone SAST and fresh per-run leads

- **SAST is detached from API collections** (`api/sast_runs.py`, `services/sast_scanner.py`, API collection UI): API scans no longer auto-create or await a collection-bound SAST pre-phase. SAST runs are standalone, while source ZIP uploads on API collections remain available solely for deriving endpoints and routes.
- **Explicit imports for API test runs** (`api/sast_runs.py`, `services/scan_leads.py`, API run UI): completed SAST results can be imported into an API test run just like a web run. Every import creates run-owned lead copies, so each test run independently reassesses every lead without mutating the source SAST result or inheriting another run's outcome.
- **Run-scoped lead management**: API lead listing, ALICE context, scanner context, deletion, and cleanup now filter by run type and run id. This removes duplicate collection-wide leads and prevents repeated or stale results from appearing in unrelated API runs.
- **Responsive SAST lead UI** (`frontend/src/styles/run.css`, shared lead tab): the API run lead panel now wraps and shrinks within the viewport instead of overflowing horizontally.

### API scanner isolation and session safety

- **API-aware tool surface and scope checks** (`services/api_scanner.py`, `services/prompts/test_lead.py`): API Test Leads receive a restricted API tool set, reject web-only inventory commands, and apply API collection scope checks to requests and redirects. API ALICE also withholds unsafe web-oriented finding and specialist paths.
- **Run-kind-safe sessions** (`services/scanner.py`, `services/alice.py`): credentials, JWTs, registrations, and captured bearer/cookie sessions are persisted under the correct web/API run kind, avoiding collisions between independently numbered run tables.
- **Coverage and regression tests**: expanded API scanner, API ALICE, scan-lead, crawler, LLM, and test-run API coverage; rebuilt the served Vite assets and refreshed architecture/tool-reference documentation.

## [PR #227] July 12 Update — scan lifecycle, reporting concurrency, crawl export/import

**Branch:** `develop → main`

### Scan lifecycle, reporting, and validation

- **Clear Test Lead handoff and true scan completion** (`services/scanner.py`, `useActivity.js`): once testing ends, the Test Lead now logs *"Testing complete - handed traffic to reporting agent for analysis..."*. The UI remains active through Reporting's probe analysis and receives a final *"Scan complete"* event only after reporting and scan finalisation finish.
- **Reliable, visible validator work** (`services/validator.py`, `api/test_runs.py`, `ActiveJobs.jsx`): validator sessions are recovered from the vault and configured credentials when possible; reporting-created findings are queued for managed validation; interrupted work is recovered at startup; and a run now shows one Validation active job while validators are working, including after a refresh.
- **Concurrent end-of-scan validators** (`models.py`, `schemas.py`, `db.py`, `ValidatorSettings.jsx`): final validation is bounded by a configurable concurrency limit (default **4**). Manual/recovery validation remains controlled separately.
- **Skipped is no longer unconfirmed** (`services/findings.py`, `db.py`, findings UI): informational findings beneath the configured validation threshold are explicitly marked skipped/not validated rather than unconfirmed.

### Concurrent reporting

- **Probe-analysis batches run concurrently** (`services/llm.py`, `services/scanner.py`): Reporting processes final probe batches under a bounded semaphore, preserving ordered output while reducing end-of-scan wait time.
- **New Reporting settings tab** (`ReportingSettings.jsx`): exposes the reporting batch concurrency limit (default **4**) in Scan Policy settings.

### Crawl data and frontend structure

- **Crawl export/import** (`services/*`, API/UI): crawl data can be exported and imported, including its OWASP classifications.
- **Run UI modularisation** (`frontend/src/`): further separates the Site Detail/run UI and sitemap components, with related ALICE/validator UI fixes and rebuilt served frontend assets.

## [PR #222] July 8 Update — frontend component extraction, macOS crawl fix

**Branch:** `frontend-refactor`

### Crawls no longer die immediately on the macOS build (`sign_app.sh`)

- **Nested Mach-O binaries now sign with the app entitlements.** Playwright's bundled `node` driver runs V8, which JITs (write+execute memory). Under hardened runtime without `allow-jit` / `allow-unsigned-executable-memory` the OS killed it on startup (`Failed to reserve virtual memory for CodeRange`), Playwright reported *"Connection closed while reading from the driver"*, and every crawl ended instantly. `sign_app.sh` previously passed `--entitlements` only to the outer bundle; it now passes them to every nested Mach-O too. Fixes the GitHub Actions release build as well (CI signs via the same script). Requires a rebuild + re-sign + re-notarize — already-shipped DMGs stay broken.

### Frontend refactor — extract shared components & split god-files

No behavior change intended; this is structural cleanup of the Vite/React SPA.

- **Shared components** (`frontend/src/components/`): `PageHeader` (+ `Crumb`/`Sep`) replaces the topbar/breadcrumb markup copy-pasted across ~9 pages; `EmptyState` standardises the icon+message+action empty card; `StatusBadge` centralises status→colour mapping. `StatusBadge` also **fixes drifted badge colours** — some pages used `success`/`warning` variants that had no CSS rule and rendered colourless.
- **`ApiCollections.jsx` (1315 lines) split** into an `ApiCollections/` module: `ApiCollectionsList`, `ApiCollectionForm`, `ApiCollectionDetail`, `ApiFilesManager`, `ApiTestRunDetail`, `ApiTestRunForm`, with a barrel `index.js` as the router's import surface.
- **`SiteDetail.jsx` slimmed (743 → ~120 lines):** extracted `TestRunForm`, plus `useActivity` and `useFindings` hooks that each own one tab's state (event log/agent roster/token usage; findings list/validation/dedup) instead of threading ~40 loose props through `TestRunDetail`.
- **A.L.I.C.E. session split** (`frontend/src/lib/`): `aliceSession.jsx` → `aliceRender.jsx` (render helpers) + `aliceSession.js` (the module-level singleton stream store that keeps the reader loop alive across component unmounts).

## [PR #220] July 7 Update — upstream proxy fixes, macOS clipboard, packaging

**Branch:** `develop`

### Upstream proxy now actually routes traffic (fix #218)

- **ALICE traffic honours the upstream proxy** (`services/alice.py`): new `_apply_upstream_proxy` sets the scanner/LLM proxy ContextVars at the start of each web/API ALICE turn — previously ALICE ran in a fresh context with the vars unset, so every request bypassed Burp/ZAP.
- **Loopback targets reach the proxy** (`services/scanner.py`, `services/crawler.py`): Chromium bypasses the proxy for `localhost`/`127.0.0.1`/`*.local` by default. New `_playwright_launch_args()` (and matching args in the crawler) pass `--proxy-bypass-list=<-loopback>` when a proxy is configured, so loopback-target traffic is captured. No-op when no proxy is set.

### macOS build: clipboard shortcuts (fix #219)

- **Edit menu wired into the menubar app** (`desktop.py`): `_install_edit_menu` installs a main menu exposing `cut:/copy:/paste:/selectAll:` (plus undo/redo, quit) with nil targets so ⌘X/⌘C/⌘V/⌘A route through the responder chain to the WKWebView. A menubar-only app has no main menu by default, which is why copy/paste were previously dead.

### Packaging & frontend

- **Versioned DMG artifact** (`make_dmg.sh`, `release.yml`): DMG is now named `AESPA-macos-v<version>.dmg` (read from `pyproject.toml`); release upload uses `RELEASE_PAT` instead of the default `GITHUB_TOKEN`.
- **d3 sitemap gravity adjustment** (`app.js`, `SiteDetail.jsx`) and scope/palette color constants exported from `SiteDetail/_helpers.jsx`.

## [PR #216] July 3–5 Update — Vite/React frontend rewrite, TLS scanner

**Branch:** `vite` 

### Frontend rewrite: vanilla JS → Vite + React

- **Monolithic app.js replaced with Vite/React source**  under `frontend/src/` (`4e28723`). Now requires `npm run build` after UI changes (agent instructions updated to match).  UI components were split into their own files — e.g. `pages/SiteDetail/` (`WebRunActivityTab`, `WebRunFindingsTab`, `WebRunTrafficTab`, `WebRunSitemapTab`, `WebRunWorkProgramTab`, `WebRunSastLeadsTab`, `TaskGraphPanel`, `AttackSurfacePanel`, `TargetIntelligencePanel`, `ScannerSessionsPanel`), `pages/ApiCollections/*`, and `pages/Settings/*` (provider/model/profile forms, scanner-policy, validator, specialist-agent settings). `styles.css` moved to `frontend/src/`; vendored `d3.js`/`htm.js`/`react*.js` removed.
- **SPA serving + dev proxy** (`main.py`, `frontend/vite.config.js`): backend serves the built `index.html`/assets; Vite dev config proxies API/WS to the FastAPI server.
- **d3 sitemap fix** (`69dbb19`): sitemap tab renders under React again; assorted tab components de-duplicated.
- **Alice chat wiring fixes** (`487c41b`, `4b560d6`): `lib/aliceSession.jsx` reconnect/replay fixed; SAST-leads tab (`WebRunSastLeadsTab`) and `SastRuns` page reworked.


### TLS/SSL scanner (`services/tls_scan.py`, `d810ee8`, `1dd6482`)

- **New sslscan-like probe** — pure stdlib `ssl` + the existing `cryptography` dep. Given `host:port`, reports accepted TLS versions (1.0→1.3), weak/non-forward-secret cipher suites, negotiated protocol+cipher, and leaf-cert details (validity, key size, sig alg, SANs, self-signed, hostname match), then derives an `issues` list the agent can turn into an OWASP **A02 Cryptographic Failures** finding.
- **Deliberate limitation:** SSLv2/SSLv3 are compiled out of Python's linked OpenSSL, so they're reported `"not-testable"` rather than falsely "not supported" (bundling `nassl`/`sslyze` for this would pull in an AGPL dep — intentionally avoided). Blocking socket work runs in a thread via `scan_tls`.
- **Wired into the scan** (`services/scanner.py`, `api_scanner.py`, `prompts/test_lead.py`): Test Lead gets a TLS tool; TLS findings now land in the normal findings list (`1dd6482`) instead of a separate bucket.
- Tests: `tests/test_tls_scan.py` (235 lines).

### Test Lead prompt: eager lead resolution (uncommitted)

- **`update_lead` now called immediately** - SAST leads were marked with investigation status at the end of a scan, now they are marked during a scan (via prompt, so may not be 100% reliable...)

### Licensing / packaging

- **Third-party licence generation** (`scripts/generate_third_party_licenses.py`, `d810ee8`): produces a bundled licence file for release artifacts; `.spec`, Dockerfile, and mac/win build scripts updated.

## [develop → main] June 28–30 — Sitewide guidance, release packaging, Alice tuning

- **Sitewide Test Lead guidance** (`c7bedbd`): new `Site.scan_guidance` free-text field (`models.py`, `db.py` migration, `schemas.py`, `api/sites.py`, `services/sites.py`, `web/app.js`) is injected into the Test Lead prompt as *"Operator guidance — follow these instructions"* for every run of that site. Tests in `tests/test_sites_api.py`.
- **GitHub Actions release packaging** (`8534934`): `.github/workflows/release.yml` builds/packages release artifacts.
- **Alice max steps 200 → 300** (`272996d`) and an `llm.py` fix (`650c593`).
- README cleanup and Docker instructions (`9440ef5`, `e643b85`).

## [PR #209] June 28 Update — Per-task model routing, adaptive login, editable findings

**Branch:** `develop → main`

### Per-task model routing

- **Per-agent-role model assignment** (`models.py`, `schemas.py`, `db.py`, `services/settings.py`, `api/settings.py`, `web/app.js`): new `LLMProfile` maps each agent role to a "Model" (`LLMConfig`), with a `default_model_id` covering any unmapped role and a `role_models_json` holding only the overrides. Assignable roles: `crawler`, `test_lead`, `specialist`, `validator`, `api_scanner`, `sast`, and `alice`. A scan resolves each agent's model via `get_llm_config_for_role(session, run, role)`; precedence is explicit per-run profile → legacy per-run model → globally active profile → globally active model, and within a profile a per-role override beats the default. Mix a cheap model on the crawler/validator with your best model on the Test Lead to cut cost.
- **Profile + model CRUD** (`api/settings.py`): `/llm/model-configs` and `/llm/profiles` list/create/update/activate/delete endpoints; runs select a profile via a new nullable `llm_profile_id` on `test_run` / `api_test_run` / `sast_run`. Migration adds the `llm_profile` table, the three `llm_profile_id` columns, and seeds a default profile (`db.py::_migrate`).
- **Wired through every run type** (`services/scanner.py`, `services/crawler.py`, `services/api_scanner.py`, `services/sast_scanner.py`, `services/validator.py`, `services/alice.py`): each agent now resolves its own model for its role instead of using one run-wide model.

### Crawler / login

- **LLM-driven adaptive login fallback** (`services/crawler.py::_authenticate_smart`, `services/prompts/login_action.py`, `services/llm.py::decide_login_action`): when the deterministic `_authenticate_auto` heuristic can't clear the login form, the model is shown a structured observation of the page (plus a screenshot when the profile has vision) and returns one action at a time (`fill`/`click`/`press`/`done`/`give_up`), driving a small bounded loop until the form is gone. Handles modal/no-route, non-standard, and multi-step logins. Parse failures return `give_up` so the loop always terminates.
- **Rate-limit waiting events** (`services/llm.py::_emit_rate_limit_waiting`): surfaces back-off waits to the UI instead of stalling silently.

### Validator

- **Access-control validation uses every configured user** (`services/crawler.py`): the cross-user reconcile pass now persists each authenticated credential's session to the vault (`recon_{cred.id}`), not just guided logins and the primary. Previously auto/TOTP credentials were logged in transiently and discarded, so the deterministic access-control check had no alternate-user sessions and reported *"Access-control validation could not run because no alternate user sessions were available"* on every privesc finding. Those sessions now flow through `_active_sessions` to both the inline and post-scan validators.

### Findings

- **Editable findings** (`services/findings.py::apply_finding_update`, `api/scan.py`, `api/api_test_runs.py`, `web/app.js`, `web/styles.css`): `PATCH` endpoints for web (`/api/test-runs/{run_id}/findings/{finding_id}`) and API (`/{run_id}/findings/{finding_id}`) runs let you edit a finding's fields from the UI.

### Docs & tooling

- **Docker instructions** (`4a840d9`) and assorted `README.md` updates.
- **CLAUDE.md**: added the `deno lint src/aespa/web/app.js` JS-sanity step (no build step to catch typos); `docs/architecture.md` updated for the above.
- Added Windows standalone build scripts (untested at time of writing)

### Tests

- New `tests/test_model_mixing.py` (profile resolution / role overrides), plus additions to `tests/test_scanner_service.py`, `tests/test_crawler_logic.py`, `tests/test_settings_api.py`, `tests/test_api_test_runs.py`, and `tests/test_test_runs_api.py`.

## [PR #206] June 25 Update — Public release

**Branch:** `develop → main`

### Crawler

- **Replaced fixed sleeps with content-driven waits** (`services/crawler.py`): page settle after navigation now polls for body text or a link instead of a flat 2s timeout, returning as soon as content is ready; the post-navigation `networkidle` wait was cut from 8s to 3s since it never resolves on pages with polling/analytics/websockets and was previously burning the full timeout.
- **Cross-user access reconciliation progress** (`services/crawler.py`): emits `agent_status` events with a running `(done/total)` count while re-checking each page against each credential, so the Agents panel shows progress instead of sitting idle during this pass.

### Validator

- **PoC outcome messages rewritten for readability** (`services/validator.py`): "PoC suppressed (auth credential not resolvable)" → "Proof skipped (couldn't get the required login)", etc. A PoC outcome now marks the Reporting agent `complete` instead of leaving it `active`, since the outcome is terminal.

### Repo

- Added AGPL licence and switched repo visibility to public.

## [PR #204] June 24 Update — Bedrock Mantle provider, standalone macOS app, OWASP-coverage rename

**Opened:** 2026-06-24 | Branch: `develop → main`

Adds a Bedrock Mantle LLM provider (frontier GPT-5.x via the OpenAI Responses API), packages AESPA as a standalone signed/notarized macOS `.app`, and renames the "Work Program" surface to "OWASP Coverage". Plus newer default models and assorted fixes.

### LLM providers

- **Bedrock Mantle provider** (`services/llm.py`, `models.py`, `schemas.py`, `db.py`, `services/settings.py`, `web/app.js`): new `bedrock_mantle` provider format driving the GPT-5.x and gpt-oss models through the OpenAI **Responses API** (`/v1/responses`, `/openai/v1` for frontier models). Anthropic-shaped messages/tools are translated to Responses input (`_ant_messages_to_responses` / `_ant_tools_to_responses`); reasoning models skip `temperature`; `_create_response` retries once dropping params the model rejects. Auth is either a Bedrock Bearer key or AWS SigV4 (`_BedrockMantleSigV4Auth`) using `AWS_PROFILE` / env / SSO / IAM-role credentials — same fallback as the Bedrock Runtime provider. Region is derived from the base URL. Claude families on Mantle remain Converse/Messages-only — use the Bedrock Runtime provider for those.
- **Mantle project id** (`models.py`, `schemas.py`, `db.py`, `services/settings.py`): new nullable `project_id` on `LLMProviderConfig` (denormalized onto `LLMConfig`), sent as the `OpenAI-Project` header for cost/usage attribution; ignored by other formats. Carried through provider CRUD, profile resolution, and config export/import.
- **Newer default models** (`schemas.py`): added `claude-opus-4-8` (anthropic / bedrock / azure_foundry_anthropic), `gpt-5.5` / `gpt-5.4` (openai / azure_openai), and the Mantle `openai.gpt-5.5` / `openai.gpt-5.4` / `openai.gpt-oss-120b` / `openai.gpt-oss-20b` to the picker defaults.

### Standalone macOS app

- **Menubar desktop launcher** (`desktop.py`, `browser.py`, `config.py`, `main.py`): runs the server in a background thread behind an `NSStatusItem` menubar icon with an optional `WKWebView` window; closing the window keeps the server (and in-flight scans) running — only "Quit" stops it. When bundled, the DB and uploads move to a per-user Application Support dir (the `.app` bundle is read-only), and Playwright's Chromium is resolved/downloaded into that dir on first run.
- **Build & release pipeline** (`AESPA.spec`, `build_mac.sh`, `sign_app.sh`, `notarize_only_mac.sh`, `make_dmg.sh`, `entitlements.plist`, `icon-menubar.png`): PyInstaller bundle (`--collect-all playwright` for the node driver) built against a non-editable install to avoid PyInstaller's macOS BUNDLE crash on uv's editable dist-info; plus code-signing, notarization, and DMG packaging scripts (`./make_dmg.sh` signs + notarizes + builds the dmg).

### Renames & UI

- **"Work Program" → "OWASP Coverage"** (`web/app.js`): the API/web coverage-matrix tab, headings, and export filenames now read "OWASP Coverage" (`*-owasp-coverage-*.md`). Provider form shows a Mantle key/SigV4 hint.

### Bug fixes

- **SAST logging panels** (`aa6a357`) and **macOS file dialogs** (`3385ddd`, `desktop.py` `NSOpenPanel`/`NSSavePanel`).

### Tests

- New Bedrock Mantle coverage (`tests/test_llm_service.py`): Responses translation, SigV4/Bearer auth, base-URL/region derivation, project-id header; updated `tests/test_settings_api.py` (project-id round-trip) and `tests/test_api_coverage.py` / `tests/test_api_scanner.py` for the OWASP-coverage rename.

### Docs

- `docs/architecture.md`, `docs/guide/config/llm.md`, `docs/guide/scans/web-screens.md`, `docs/guide/web-running.md` updated; `README.md` adds a "what to use it for" note, VAmPI results link, and GPT-5.x / Trusted-Access guidance.

## June 22 Update — Security review hardening & cross-cutting fixes

**Opened:** 2026-06-22 | Branch: `develop → main`

A multi-file review pass over the SAST scanner, validator, multi-provider LLM client, crawler, and dynamic scanner, fixing several real correctness/security bugs surfaced along the way, plus a repo-wide lint cleanup that uncovered a latent crash.

### Security

- **Scope enforcement now survives HTTP redirects** (`services/scanner.py`, `services/alice.py`): the scanner/ALICE clients use `follow_redirects=True`, but scope was only validated on the initial URL — a target could redirect to an out-of-scope/internal host (SSRF / scope bypass) with no re-check. New `_request_scope_checked` disables auto-follow and validates every `Location` against the run's scope predicate before following it (also honouring 303/POST→GET body-drop semantics); an out-of-scope redirect is refused and surfaced as `[SCOPE BLOCK]`. Applied to the scanner main-loop + specialist `http_request`, and to ALICE's `http_request` and `register_account` (which captures a session from the final response). The `browser` tool (scanner and ALICE) re-checks the final post-redirect URL and refuses to load an off-scope page into context (auth/SSO flows exempt). The helper takes an optional `scope_check` callable so ALICE's API-run scope is honoured.
- **TLS verification no longer disabled without a proxy** (`services/llm.py`): every non-Bedrock LLM client hardcoded `verify=False`, sending the provider API key and prompt data over unvalidated TLS even with no proxy configured. Now `verify=(proxy is None)` across all providers, mirroring the existing Bedrock pattern — verification is disabled only for an interception proxy.
- **SAST path jail hardened** (`services/sast_scanner.py`): `_jail` / `_safe_unzip` used string-prefix matching, so `…/extract/5` treated `…/extract/55` as inside it; switched to `Path.is_relative_to`, closing a sibling-directory escape for the file tools and archive extraction.
- **PoC verification is shell-free** (`services/validator.py`): PoC re-verification ran the built `curl` string via `subprocess.run(shell=True)` with POSIX `shlex` quoting — meaningless to `cmd.exe` (so nothing verified on Windows) and a command-injection vector for target-derived values. Added `_build_curl_argv` + a shell-free `_run_and_assert_curl(argv)`.
- **Optional Cloudflare Access AUD** (`models.py`, `schemas.py`, `db.py`, `services/settings.py`, `api/settings.py`, `main.py`, `web/app.js`): new `CloudflareAccessConfig` singleton (edited on the Debug page) lets the `/api/version` JWT verifier enforce an Access application audience. When unset, behaviour is unchanged (audience check skipped) — previously any Cloudflare tenant's signed token passed the issuer check.

### Bug fixes

- **API-scan SAST pre-phase was silently broken** (`services/api_scanner.py`): `_do_api_thinking_scan` referenced an undefined `collection_id` (should be `run.collection_id`), so the pre-phase always raised `NameError` — swallowed by a broad `except`, logging "failed or skipped". Surfaced by the lint pass (`F821`).
- **Rate-limiter could hang forever** (`services/llm.py`): `AsyncTokenBucketLimiter.acquire` looped indefinitely when a single request's estimate exceeded the per-minute budget (refill caps at `max_tokens`); now clamps the estimate, and `reconcile` clamps symmetrically.
- **Rate limiting now covers the agentic path** (`services/llm.py`): pacing previously wrapped only `_call` (page analysis/reporting), not `_call_with_tools` — so dynamic/API/SAST/ALICE scan loops were unpaced. Wrapped the tool-using path too, with an `on_wait` callback that emits a `rate_limit` notice into the active run's log the moment pacing starts, so a throttled scan never looks frozen.
- `**max_pages` now caps total site-map nodes** (`services/crawler.py`): the per-phase budget let the map grow to ~N×`max_pages` across N credential phases; new node creation is now gated on the shared `pages_done` counter (matching the API-promotion path), so distinct nodes never exceed `max_pages`.
- **Crawler same-host detection ignores default ports** (`services/crawler.py`): `_same_domain` compared raw netlocs, so `example.com` vs `example.com:443` were treated as different hosts and same-site links dropped; added `_norm_netloc` to normalise the scheme's default port (and strip userinfo).
- **Crawler API-call attribution** (`services/crawler.py`): a slow response body could be appended after the crawl moved on and be attributed to the next page; captured calls are now stamped with their page and only promoted to the matching page.
- **SAST stop event mis-routed** (`services/sast_scanner.py`): `stop_sast_scan` emitted outside a `run_kind_scope`, so its persisted `agent_status` defaulted to `run_kind='web'` and leaked into a colliding web run; now wrapped in `run_kind_scope("sast")`.
- **Startup orphan-sweep ordering** (`db.py`): `_cleanup_orphaned_sast_extractions` ran before the `SastRun` columns it queries were migrated (silently skipped on first post-upgrade boot); moved to the end of `_migrate`.
- **Lead attribution falsy-`or` guard** (`services/scan_leads.py`): `update_lead` used `or` fallbacks that misread a `0` run id; switched to explicit `is not None`.
- **ALICE reconnect replay dropped events** (`services/alice_tasks.py`): the per-task event buffer trims from the front at `BUFFER_LIMIT`, but `stream_events` replayed `events[cursor:]` treating the reconnect cursor as an absolute index — so a long ALICE turn (which emits many token-delta events) corrupted the rendered message for a reconnecting client. Added a `dropped` offset so replay slices at `cursor - dropped`.
- **Playwright traffic-capture memory leak** (`services/traffic.py`): `on_request` stored per-request timing/body for *every* request, but `on_response` / `on_request_failed` `return` early for noisy `SKIP_RESOURCE_TYPES` (images/fonts/media) *before* popping that state — so each skipped static asset leaked a `_pending`/`_req_data` entry that grew unboundedly over a long browser-driven scan. `on_request` now skips the same resource types at the source.
- **OpenAPI nested `$ref` / `allOf` resolution** (`services/api_docs.py`): when prance's dereferencer couldn't resolve a spec, the manual backstop only dereferenced the top-level schema ref — `allOf` members that were `$ref`s (losing their properties) and nested property `$ref`s were left unresolved, so request-body schemas surfaced raw `$ref` objects. Replaced `_flatten_all_of` with a recursive, cycle-safe `_resolve_schema_deep` that resolves refs inside `allOf`, `properties`, `items`, and `oneOf`/`anyOf` (internal refs only — external refs still left verbatim as an SSRF guard). Fixes the previously-failing `test_parse_openapi_resolves_nested_refs`; the full suite is now green.

### Chores

- **Repo-wide lint cleanup**: cleared all ruff `F`/`I` findings (unused imports, import ordering, dead locals, empty f-strings) across `src/` and `tests/`; intentional re-exports (e.g. `_ADVERSARIAL_VALIDATOR_SYSTEM` via `services/llm.py`) marked `# noqa: F401`.

### Tests

- New: scope-checked redirect following (`tests/test_scanner_service.py`), rate-limiter clamp/`on_wait` (`tests/test_llm_service.py`), `_same_domain`/`_norm_netloc` port handling (`tests/test_crawler_logic.py`), SAST path-jail escape (`tests/test_web_sast_leads.py`), Cloudflare AUD round-trip (`tests/test_settings_api.py`), ALICE buffer-trim/cursor replay (`tests/test_alice_tasks.py`), Playwright skip-resource no-leak (`tests/test_traffic_service.py`); updated PoC tests for the shell-free argv.

### Docs

- `docs/architecture.md` updated: redirect-aware scope enforcement (§16), conditional TLS + agentic-path rate limiting/pacing (§9), `max_pages` = site-map size (§6), `CloudflareAccessConfig` (§4/§5/§12), and the verified-PoC pipeline (§11).

## June 19 Update — SAST on web scans

**Opened:** 2026-06-19 | Branch: `web-sast → main`

Extends SAST beyond the API-scan pre-phase: SAST runs can now be created standalone (upload a ZIP, no collection), and a web scan can import a *copy* of any completed SAST run's leads to investigate dynamically. Leads are copied — never linked — so the source SAST run's originals stay untouched. Also lands the leads export and a validator fix.

### SAST on web scans

- **Standalone SAST runs** (`models.py`, `db.py`, `services/sast_scanner.py`, `api/sast_runs.py`): `SastRun.collection_id` is now nullable and runs can carry their own archive via new `source_archive_path` / `source_filename` columns. `_sast_scan_task` resolves the archive from the source-zip `ApiDocument` (API pre-phase, unchanged) **or** the standalone archive, and tolerates no collection / no parsed endpoints. New `POST /api/sast-runs` (multipart) uploads a ZIP and creates a standalone run. Migration: `_ensure_sast_run_collection_id_nullable` rebuilds the table to drop the `NOT NULL`, plus idempotent `_ensure_column`s (verified on an old-schema DB).
- **Copy-into-web-run lead model** (`services/scan_leads.py`, `models.py`): `ScanLead` gains indexed `imported_into_run_type` / `imported_into_run_id`. `copy_leads_to_run(sast_run_id, "web", run_id)` duplicates a run's *original* leads into new rows owned by the web run (idempotent per source run, reset to `open`); `get_leads_for_run` / `format_leads_for_run` consume them. SAST-run lead listings now exclude copies (`imported_into_run_id IS NULL`).
- **Web dynamic scan wiring** (`services/scanner.py`): `_do_thinking_scan` injects imported leads into the opening context via `format_leads_for_run("web", run_id)`; the shared `update_lead` tool now records `investigated_by_run_type="web"` for web runs (was hardcoded `"api"`), so confirmed web leads auto-promote to a finding keyed on `test_run_id`.
- **API** (`api/test_runs.py`): `GET /sast-runs/available` (completed runs with leads), `POST /import-leads`, `GET /leads`, `DELETE /leads` (clear all), `DELETE /leads/{lead_id}` (single, scoped to this run). Web-run delete and SAST-run delete each clean up only their own rows (`services/run_cleanup.py` also removes a standalone run's stored archive file).
- **Frontend** (`web/app.js`): SAST screen gets a **New SAST Scan** upload button. Web run gains a **SAST Leads** tab styled like the Findings screen (full-width table, sticky header) with an import dropdown, per-row delete, clear-all, and markdown export.
- **Leads export**: `leadsToMarkdown` exports leads (no source ZIP) from the SAST run view, API run leads, and web SAST Leads tab; embeds a hidden JSON block for future re-import.
- **Tests**: new `tests/test_web_sast_leads.py` (standalone upload, import flow, clear/delete, API-shape regression) and extended `tests/test_scan_leads.py` (copy semantics, idempotency, web→`test_run_id` promotion).

### Bug fixes

- **Validator runs on POST requests too** (`services/validator.py`, `services/prompts/validator.py`): the adversarial validator no longer skips POST-based findings; PoC validation coverage added in `tests/test_poc_validation.py`.

### Docs

- `docs/architecture.md` updated for web SAST (§17 rewrite + standalone/import lead model), the web OWASP work program (#179), run-id collision / `run_kind` handling (#169/#173), and assorted entity/field corrections.

## [PR #197] June 18 Update — Export/Import, ALICE modal logins, OWASP 2025 fix

**Opened:** 2026-06-18 | Branch: `develop → main`

Adds export/import for API collections, sites/web runs, and the web workprogram; teaches ALICE (and the scanner) to handle JS modal logins via a live Playwright browser; fixes the web workprogram progress regression and the OWASP version mismatch; and ships a full user guide under `docs/guide/`. 19 commits across ~30 files.

### Docs

- Full user guide added under `docs/guide/` (LLM config, settings, web scan screens, API scans, running scans) with screenshots, plus VAMPi result writeups under `docs/results/vampi/` and a `docs/results/` reorganisation. README refreshed. Claude GitHub Actions workflows added (`.github/workflows/`).

### Export / Import

- **API collections** (`services/api_collections.py`, `api/api_collections.py`): New `export_collection` serialises a collection (endpoints, documents, settings) to a JSON bundle; `import_collection` rebuilds it. New `GET /api/api-collections/{id}/export` and `POST /api/api-collections/import` endpoints, with Export/Import buttons in the collections UI (`web/app.js`). Round-trip tests in `tests/test_api_collections_export_import.py`.
- **Sites / web runs + workprogram** (`services/sites.py`): A site/run can be exported and re-imported as a JSON bundle including findings and `PageOwaspTest` workprogram cells. `finding_ids_json` on each cell is remapped to the newly-inserted finding ids on import, dropping stale ids that have no exported finding. Tests in `tests/test_sites_export_import.py`.

### ALICE + Scanner: modal / JS logins (#178)

- **Live Playwright browser for ALICE** (`services/alice.py`): ALICE's `browser` tool now drives a real per-run Playwright browser (keyed by run_id), so it can complete JS-based login modals that have no URL route. Session state established by a login (cookies/headers) propagates to later `http_request` and `browser` tool calls. Crawler/scanner auto-login paths adjusted to match (`services/crawler.py`).
- **Reasoning display fix** (`services/alice.py`): Inline `<think>` / `<thinking>` blocks emitted by some models are now parsed out of ALICE's chat output.

### Bug fixes

- **Web workprogram progress regression (#190)**: Workprogram coverage cells weren't filling during web scans — fixed so progress updates live again.
- **OWASP 2025 vs 2021 (#189)**: `write_finding` and prompts (`services/prompts/test_lead.py`, `reporting.py`) now consistently target OWASP Top-10 2025 instead of mixing in a 2021 reference.
- **API findings not logged in workprogram**: API scan findings now auto-fire the workprogram coverage hook (`services/api_scanner.py`).
- **Import/export + findings rendering** (`web/app.js`, `services/traffic.py`): affected-URL cleanup (`_clean_affected_url`) and rendering fixes.

## [PR #186] 16th June Update — OWASP Web Workprogram, even more bug fixes

**Opened:**  2026-06-16 | Branch: `develop → main`

Implements the OWASP Top-10 (2021) web workprogram coverage matrix for web app scans (#179), mirroring the existing API scan workprogram. Adds Track and Enforce modes, live in-scan progress, and auto-seeding. 5 commits across 9 files.

### OWASP Top-10 Web Workprogram (#179, PR #185)

- `**PageOwaspTest` model promoted to a real coverage cell** (`models.py`, `db.py`): Added `status` (`not_started` / `in_progress` / `covered` / `skipped` / `finding`), `skip_reason`, `finding_ids_json`, and `last_updated` fields. `TestRun.coverage_mode` (`track` | `enforce`) added with a SQL `server_default` so old rows keep the `track` default without a migration failure. All 5 new columns are `_ensure_column`-migrated idempotently on startup.
- `**services/web_workprogram.py` — full implementation**: `seed_web_workprogram` creates one `PageOwaspTest` cell per in-scope page × applicable OWASP category (static assets filtered out). `update_web_coverage_cell` upserts with no-downgrade semantics and normalises OWASP codes (`"A02 - Cryptographic Failures"` → `"A02"`) so LLM full-name variants always hit the right row. `mark_in_progress_to_covered` promotes at scan completion (track mode). Enforce mode adds `_build_web_enforce_directive`, `_enforce_web_coverage_loop`, and an LLM-assisted `_make_web_enforce_prober` that drives every uncovered cell to a terminal state.
- **Auto-seeding** (`services/crawler.py`, `api/scan.py`): Workprogram is seeded automatically (1) at crawl completion after `_merge_all_categories`, (2) synchronously in the `start_thinking_scan` and `resume_thinking_scan` API endpoints before returning — so the workprogram tab is populated the moment the user clicks Start/Resume.
- **Scan wiring** (`services/scanner.py`): `_do_thinking_scan` reads `coverage_mode`, seeds the workprogram, prepends an enforce directive to the crawl context when in enforce mode, and passes `post_probe_fn` / `post_finding_fn` hooks into `_do_agentic_thinking_loop`. Post-scan finalisation either promotes in-progress cells (track) or runs the enforce loop (enforce). A `_finding_hooks` module-level registry (same pattern as `_specialist_tasks`) ensures every finding write path — including **specialist agents** — fires the workprogram hook, not just the main agentic loop.
- **ALICE wiring** (`services/alice.py`): `_web_post_probe_fn` constructed per turn and passed into `_execute_alice_tool` so ALICE probes also update the web workprogram.
- **On-the-fly page creation**: If the scan probes or finds an issue at a URL not in the original crawl, a placeholder `CrawledPage` (in-scope) is created automatically and a cell is written — no probe or finding is silently lost.
- **Finding attribution via `affected_url**` (`services/web_workprogram.py`): `_post_finding` resolves the workprogram cell from `finding.affected_url` (the actual endpoint) rather than `finding.page_id` (the scan entry page), fixing incorrect attribution to root-level page rows. `_match_page_for_url` uses exact + normalised match only — prefix overlap removed — so `/` never absorbs `/api/health`.
- **URL normalisation** (`services/web_workprogram.py`): `_normalize_url` now strips IDs (`\d+` / UUID) from both path segments and query-string values (`/items?id=42` → `/items?id={id}`), grouping equivalent parameterised URLs on the same workprogram row.
- **Deterministic findings excluded**: `_post_finding` and `get_web_coverage_matrix` both ignore `finding_source="deterministic_probe"` findings — they don't count toward cell status or totals.
- **Full writeup display fix**: Matrix builder now maintains a `finding_by_id` lookup so cells whose `page_id` diverged from the finding record can still resolve full finding details (title, severity, description) for the UI panel.
- **API** (`api/scan.py`): `start_thinking_scan` accepts an optional `{ coverage_mode }` JSON body.
- **Frontend** (`web/app.js`): Coverage mode selector (Track / Enforce) in the scan topbar. `WebRunWorkProgramTab` replaced with an SSE-driven live view showing per-cell status badges, enforce-loop progress, mode badge, and `skipped` in the legend. Workprogram tab immediately reloads on scan start/resume via a `reloadKey` signal.
- **Tests** (`tests/test_web_coverage.py`): 22 new in-memory tests covering seeding, upsert semantics, probe/finding hooks, enforce loop, placeholder page creation, wrong-page attribution, root-page non-match, and the `start_thinking_scan` coverage_mode endpoint. 497/497 tests pass.

## ALICE improvements and bug fixes:

Closes out the run-id collision class of bugs (#173), gives ALICE the ability to drive the API work-program coverage matrix (#180), adds CVSS calibration to the AI Review Issues tab (#99), ensures confirmed SAST leads always raise a finding, and polishes ALICE chat rendering and reliability. 9 commits across 28 files (~1,800 insertions, ~170 deletions).

### Run-ID Collision Hardening (#173)

- `**ScannerSession.run_kind` discriminator** (`models.py`, `services/scanner_sessions.py`, `db.py`): `ScannerSession` and `AliceChatSession` were keyed on `test_run_id` alone, so a web `TestRun` and an `ApiTestRun` that happened to share an integer id would read, update, and delete each other's rows. Added a `run_kind` column (`"web" | "api"`) on both tables — mirroring the existing `AgentLog` / `ScanLog` pattern — and threaded it through `upsert_session`, `ensure_anonymous_session`, `list_run_sessions`, `load_session_vault`, and every scanner-session endpoint. Includes a one-time backfill migration that tags pre-existing rows by inspecting their parent run.
- **Cascade-delete helpers** (`services/run_cleanup.py`, `api/api_test_runs.py`, `api/sast_runs.py`, `api/test_runs.py`, `services/api_collections.py`): SQLite recycles freed autoincrement ids, so a deleted run (or collection) that left orphaned `ScanFinding` / `TrafficEntry` / `ApiEndpointTest` / `ScanLog` / `ScannerSession` rows would later see them re-attached to a brand-new run reusing the same id. New `cascade_delete_api_run` and `cascade_delete_sast_run` delete every keyed child row in a single transaction; the API-run, SAST-run and collection delete paths now call them, and collection delete also unlinks uploaded documents from disk. Reported symptom — a fresh run showing findings/logs from the previous occupant of the same id — is gone. Regression tests added in `tests/test_api_scanner.py` and `tests/test_api_test_runs.py` for reused run-id and reused collection-id scenarios.

### ALICE Drives the API Work-Program Coverage Matrix (#180)

- **New ALICE context tools for coverage** (`services/alice.py`, `services/prompts/alice.py`): `coverage_matrix` lets ALICE read the current endpoint × OWASP category matrix (filterable by status / endpoint_id) so it can find `not_started` cells to work on; `set_coverage` explicitly marks a cell `covered` / `skipped` / `in_progress` / `finding`, validated against the collection, scope, and applicable categories. Both are wired into `_run_api_context_tool`.
- **Automatic coverage hooks** (`services/alice.py`): `http_request` now forwards the declared `owasp_category` to a new `post_probe_fn` parameter, flipping the matching endpoint × category cell to `in_progress` when ALICE starts a probe (URL-matched, API runs only). `report_finding` mirrors the scanner's hook: matches the finding's `affected_url` to an in-scope endpoint and flips the cell to `finding` with `finding_id` set. Prompts updated to instruct ALICE to set `owasp_category` on category-specific probes and to use `set_coverage` for covered/skipped conclusions.
- **Tests** (`tests/test_alice_service.py`, `tests/test_api_alice_context.py`): Coverage added for `coverage_matrix` / `set_coverage` routing, the `post_probe_fn` integration on `http_request`, and the auto-link from `report_finding` to a coverage cell.

### Improve Issue Deduplicator + Issue Ratings (#99)

- **CVSS 3.1 parser / calculator** (`services/scanner.py`): New `parse_cvss_vector`, `format_cvss_vector`, and `calculate_cvss_score` (full base-score formula, scope-aware, with the official round-up rule) so the app can recompute scores from the metric vector without depending on a string-typed column.
- `**_calibrate_finding_rating` rule set** (`services/scanner.py`): Heuristic calibrator that downgrades the CVSS vector for known overstated categories — CORS, security-header / server-header / CSP / HSTS / X-Frame-Options / X-Content-Type-Options disclosures — bringing their impact metrics in line with realistic exploitation difficulty. Runs per-finding on the AI Review Issues tab.
- **Auto-calibration on ALICE turn end** (`services/alice_tasks.py`, `services/scanner.py`): When an ALICE turn completes, `calibrate_all_findings_for_run(run_id, is_api_run=...)` is invoked against the run's findings, so newly-written issues land in the AI Review tab with calibrated vectors. Failure is logged, never raised.
- **UI** (`web/app.js`): The AI Review Issues panel surfaces calibrated scores and the underlying vector.

### ALICE Chat Rendering & Reliability

- **Claude-code style trace boxes** (`web/app.js`, `web/styles.css`): Thinking/process panels now split an ALICE turn into ordered segments — each piece of intermediate commentary the model emits mid-run is wrapped in `[[ALICE_SAY]]…[[/ALICE_SAY]]` markers and rendered as a prominent chat bubble, with the surrounding tool-call steps collapsed into a low-prominence "Step N · tool_name" expandable box. The final tool-less turn's text and the done summary become the prominent reply bubble. New helpers: `parseAliceTurnSegments`, `aliceTraceSummary`, `renderAliceTraceBox`. New CSS classes: `.alice-trace-box`, `.alice-trace-summary`, `.alice-thinking-inline`.
- **Done summary now surfaces as a message** (`services/alice.py`): The `done` tool's `summary` field is emitted as a `message_chunk` so the user sees the closing paragraph of an ALICE turn as a real reply bubble instead of only inside the collapsed trace.
- **Larger context-tool payloads** (`services/alice.py`, `services/llm.py`, `services/scanner.py`): `context_tool` result cap raised from 8,192 → 30,000 chars (the standard 16,000-char cap is retained for regular tool results), and the `findings_list` tool now returns the full set of findings rather than truncating mid-list. Prevents mid-prompt truncation in long-running API scans.
- **Validator no longer deadlocks when ALICE writes a finding** (`services/validator.py`): The validator was entering a busy loop while ALICE's `report_finding` was still persisting; fix gives the validator a stable view of the in-flight run state and exits cleanly when there's nothing to validate.
- **ALICE task registry keyed by `(run_type, run_id)**` (`services/alice_tasks.py`, `api/alice.py`, `api/api_test_runs.py`, `api/test_runs.py`, `models.py`, `db.py`, `tests/test_api_test_runs.py`): The in-memory task map was previously keyed on `run_id` only, so a web run and an API run sharing an id could stomp on each other's ALICE sessions. Registry now uses `(run_type, run_id)` tuples; new `run_type` parameter threaded through `get`, `start`, `stop`, `stream_events`, and `status`. The `AliceChatSession.run_kind` column added in the run-id collision fix above is what makes the persisted chat history show up under the correct scan type on reload.

### Fixed: Confirmed SAST leads don't always result in a finding

- `**update_lead` auto-promotes confirmed leads** (`services/scan_leads.py`): When an API or web scan confirmed a SAST lead via `update_lead(status="confirmed")`, the lead's status was set but no `ScanFinding` row was ever created — the leads panel showed "confirmed" while the findings panel stayed empty for that issue. The service now synthesises a `ScanFinding` from the lead's own fields (title, description, location, evidence, severity, OWASP category) whenever `linked_finding_id` is not supplied, and sets `linked_finding_id` to the new id. If the agent already recorded a finding for the same run with the same title (i.e. called `write_finding`/`report_finding` but forgot to pass `finding_id` to `update_lead`), the existing finding is linked instead — no duplicate. For API runs, the matching work-program cell is also flipped to `finding` via the existing `update_coverage_cell` hook; the cell flip is best-effort and only triggers when a path token in the lead text strictly matches an in-scope endpoint (never fabricated). Synthesised rows carry `finding_source="sast_lead"` so the UI can distinguish them from agent-written findings. Only fires on `status="confirmed"`; `dismissed` and `inconclusive` leads remain finding-free.
- **SAST lead confidence threshold realigned to 0.7** (`services/prompts/sast.py`): The SAST prompt instructed the LLM *"Only leads ≥ 0.8 are kept"* in four places, but the `CONFIDENCE_THRESHOLD` constant in `services/scan_leads.py` was `0.7`. The SAST agent was discarding hypotheses the service would have otherwise kept, shrinking the lead funnel feeding the dynamic API scanner. Prompts updated to `≥ 0.7` everywhere; no code change.
- **Tests** (`tests/test_scan_leads.py`): New in-memory SQLite suite (7 cases) covering the auto-promotion path, dedup against an existing same-run/same-title finding, the explicit-`linked_finding_id` short-circuit, the dismissed-doesn't-promote invariant, the work-program cell flip, the no-cell-when-no-endpoint-match case, and the no-`run_id` orphan guard.

### Version

- `pyproject.toml`: bumped to `0.5.20260615.4`.

---

## [PR #174] 15th June Update - Lots of bug fixes!

**Opened:** 2026-06-15 | Branch: `develop → main`

ALICE improvements for API scans, two `ScanFinding` ID-space correctness fixes, removal of the server-side deduplication pipeline, vendored frontend dependencies, and supporting bug fixes (17 commits across ~15 files).

### Bug Fixes for ALICE on API Scans

- `**update_lead` tool** (`services/alice.py`): ALICE now has access to `update_lead`, which marks a `ScanLead` row as `confirmed`, `dismissed`, or `inconclusive` after a dynamic investigation, and optionally links it to a written finding. Available to both web and API ALICE sessions.
- `**remove_finding` tool** (`services/alice.py`): New tool that deletes a specific finding by ID from the current run. Accepts findings keyed on either `test_run_id` (web) or `api_test_run_id` (API) so it works correctly in both contexts. Requires a `reason` argument for auditability.
- `**lead_list` context tool for API ALICE** (`services/alice.py`): ALICE in API run context can now call `context_tool(tool='lead_list')` to retrieve open `ScanLead` rows for the collection (capped at 50), giving it visibility into SAST-generated leads during an interactive session.
- `**write_finding` withheld from API ALICE** (`services/alice.py`): API runs record findings via the API-aware `context_tool(tool='report_finding')` path. `write_finding` is now excluded from the API ALICE tool set to prevent it persisting findings against the wrong (web) table and triggering validation with a colliding run ID. The nudge-back prompt and the API ALICE system prompt updated accordingly.
- **Finding ID added to `list_findings**` (`services/prompts/test_lead.py`, `services/scanner.py`): The `list_findings` context tool response now includes the `id` field on each finding, so ALICE and the Test Lead can reference specific findings when calling `remove_finding` or `update_lead`.
- `**remove_finding` prompts updated** (`services/prompts/alice.py`, `services/prompts/test_lead.py`): System prompts for both web and API ALICE updated to document the `remove_finding` tool and when to use it.
- **Thought-process display fixes for API ALICE** (`services/alice_tasks.py`, `web/app.js`): Thinking-block accumulation and SSE event handling fixed for API ALICE sessions — thought deltas were being dropped or rendered in the wrong bubble, causing blank thought-process panels.
- **ALICE fixes for API scans** (`services/alice.py`, `services/prompts/alice.py`): Extended `run_api_alice_turn_stream` with correct API context-tool routing for `lead_list`, `endpoint_list`, `endpoint_detail`, and `collection_info`; fixed scope-check logic that was blocking all API-run ALICE requests; fixed the accumulated thought/message state used for cursor-based replay.

### Bug Fixes for logs and findings attaching to the wrong test runs

- **API and web scan finding IDs clash** (`db.py`, `models.py`, `schemas.py`, `services/api_scanner.py`, `services/scanner.py`): `ApiTestRun` and `TestRun` use independent autoincrement sequences, so their integer IDs can coincide. Previously, API scan findings were stamped with both `api_test_run_id` and `test_run_id` (set to the same integer), causing API findings to bleed into whichever web scan run happened to share that ID. Fix: `test_run_id` is now nullable on `ScanFinding`; API findings set it to `NULL`. A `_ensure_scan_finding_test_run_id_nullable` migration (SQLite table-rebuild pattern) clears `test_run_id` on all existing API findings. `DELETE /api-test-runs/{id}/findings/{finding_id}` endpoint added so individual API findings can be removed. Regression tests added in `tests/test_api_test_runs.py` and `tests/test_db_migration.py`.
- **API scan agent logs blank when run IDs collide** (`services/events.py`, `services/api_scanner.py`, `services/sast_scanner.py`, `services/scanner.py`, `services/alice_tasks.py`, `#169`): `AgentLog`/`ScanLog` rows are tagged with a `run_kind` discriminator (`web`, `api`, `sast`) so the API Status page can query only its own rows. The discriminator was previously resolved from in-memory id-keyed sets; because web/API/SAST run IDs come from independent sequences they can collide, and the SAST set was checked first — so an API run whose ID matched a SAST run had its agent rows mis-tagged `sast`, returning nothing to the API log endpoint. Fix: replaced id-based resolution with `events.run_kind_scope()`, a `contextvars.ContextVar`-based scope that each scan orchestrator opens at start (`api`, `sast`, `web`). `asyncio.create_task` snapshots the context, so the scan task and all its child specialist/ALICE tasks inherit the correct tag regardless of ID collisions. Regression tests added in `tests/test_api_test_runs.py`.
- **Validator hidden from API scan UI** (`web/app.js`): The adversarial validator agent row was being rendered in the API scan Agents panel even though the validator does not run for API scans. One-line fix to suppress it.
- **Stuck findings reset on startup** (`db.py`): Findings left in `validating` status by a previous server crash are reset to `unvalidated` on startup, preventing them from being permanently stuck and never re-validated.
- **ALICE API reporting tool** (`services/alice.py`, `services/prompts/alice.py`, `services/validator.py`): The `report_finding` context-tool path used by API ALICE was calling the web validator with wrong arguments; fixed to use the API-aware validation flow. The validator service updated to handle `ApiTestRun`-scoped findings correctly.

### Deduplication Pipeline Removed

- **LLM-based finding deduplication removed** (`services/findings.py`, `services/llm.py`, `services/prompts/reporting.py`, `api/scan.py`, `schemas.py`): The `POST /api/test-runs/{id}/findings/deduplicate` endpoint and the `findings_svc.deduplicate_findings` pipeline (~878 lines) have been removed. Deduplication is now handled exclusively by ALICE on user instruction, which produces more accurate results with less hallucination than the batch LLM pass. The `DebugFindingsTable` UI component updated to remove the Deduplicate button.

### Vendored Frontend Dependencies

- **External JS libraries vendored** (`web/vendor/`, `web/index.html`, `main.py`): React, ReactDOM, HTM, and D3 are now served from `src/aespa/web/vendor/` as static files rather than loaded from CDNs. This eliminates network dependency at runtime and avoids CSP issues when running in air-gapped environments. FastAPI serves the vendor directory as a static mount.

### Documentation

- `CHANGELOG.md` relocated from `docs/` to the repository root.
- `README.md` created at repository root.
- `docs/` documentation updates.

### Version

- `pyproject.toml`: bumped to `0.5.20260615.2`.

---

## [PR #162] 12th June Update

**Opened:** 2026-06-12 | Branch: `develop → main`

Bundles two feature branches: a full API security scanning engine (PR #149) and a SAST-assisted pre-phase for API scans (PR #160), totalling 53 files and ~13,300 insertions.

### Included: PR #149 — API Scanning Feature

*Merged to develop: 2026-06-09*

Introduces REST API security testing: collections, document parsing, OWASP API Top-10 coverage matrix, an agentic scan loop, ALICE integration for API runs, and a comprehensive test suite (36 files, ~10,600 insertions).

#### API Collections & Documents

- `**ApiCollection` entity** (`models.py`, `db.py`, `schemas.py`): New top-level resource grouping a base URL, server list, scope hosts, auth summary, and readiness assessment. CRUD endpoints under `/api/api-collections/`.
- **Document ingestion** (`services/api_documents.py`, `services/api_docs.py`): Upload and parse API specification documents. Supports OpenAPI 3.x / Swagger 2.x (via `prance` for `$ref` resolution), Postman Collection v2/v2.1, credential files (bearer tokens, key-value pairs, curl `-H`/`-b` lines), free-text documents (LLM extraction), and source ZIP archives (framework-heuristic route scanning). Idempotent re-parse replaces existing endpoints from the same document.
- `**ApiEndpoint` & `ApiCredential**` (`models.py`): Normalised rows for discovered endpoints (method, path, parameters, request/response schema) and credentials (scheme, label, auth endpoint). Endpoint scope toggle (`in_scope` flag) controllable via `PATCH /{collection_id}/endpoints/{endpoint_id}/scope`.
- **Testing readiness assessment** (`services/api_readiness.py`): Tells you whether the scanner has enough information about the APIs to conduct a test. `assess_readiness()` loads endpoints and credentials, sends a gap-analysis prompt to the active LLM (capped at 60 endpoints), and persists structured results to `ApiCollection.readiness_json` and per-endpoint `prereq_*` fields.

#### OWASP API Top-10 Coverage Matrix

- **Coverage seeding** (`services/api_scanner.py`, `seed_coverage_matrix`): On scan start, creates `ApiEndpointTest` rows for each (endpoint, OWASP category) pair applicable by heuristic (BOLA for path parameters, BOPLA for PUT/PATCH, BFLA for DELETE, etc.). All endpoints receive API2, API4, API8, and API9.
- **Track & Enforce modes** (`coverage_mode` field on `ApiTestRun`): In `track` mode the matrix is updated as the agent makes probes. In `enforce` mode (`_enforce_coverage_loop`) every still-uncovered cell is driven to a terminal state by an LLM classifier that decides per (endpoint, category) whether to probe or skip with a reason, up to a configurable budget.
- **Coverage matrix API** (`GET /{run_id}/coverage`): Returns the full matrix as a structured dict grouped by endpoint.

#### API Scan Engine

- `**ApiTestRun` lifecycle** (`api/api_test_runs.py`): Create, start, stop, and query API scan runs. Mirrors the web scanner's task registry pattern (`_scan_tasks`, `_stop_requested`). SSE event stream at `GET /{run_id}/events` for real-time progress.
- `**_do_api_thinking_scan**` (`services/api_scanner.py`): Full Test-Lead + Specialist + Validator agentic loop wired for REST APIs — no Playwright required. Uses `_api_context_tool_fn` to route `endpoint_list`, `endpoint_detail`, `collection_info`, and `finding_list` to API-specific handlers, with shared web-scanner context tool for `history_search`, `traffic_search`, etc. Findings are stamped with `api_test_run_id` and mapped to OWASP API Top-10 category.
- **Session seeding from credentials** (`seed_sessions_from_credentials`): Loads all `ApiCredential` rows for the collection and registers them into the scanner session vault before the agentic loop begins.
- **Scope enforcement** (`_api_check_scope`): Out-of-scope requests are blocked against the collection's `scope_hosts` list.
- **Credential persistence** (`_make_persist_credential_fn`): Newly discovered credentials are saved back to the collection during a scan.
- **Traffic logging**: API scan HTTP traffic captured via the shared `traffic.py` service; accessible at `GET /{run_id}/traffic`.
- **Findings export / import** (`GET /{run_id}/findings`, `POST /{run_id}/findings/import`): Findings round-trip in the same markdown format as web scans.

#### ALICE Integration for API Runs

- **ALICE endpoints on `ApiTestRun**` (`api/api_test_runs.py`): Full ALICE agentic chat available under `/{run_id}/alice/*` — start, stream, stop, status, and session persistence — mirroring the web scan ALICE surface.
- **API-specific ALICE context** (`services/alice.py`): `_run_thinking_context_tool` extended to handle `collection_info`, `endpoint_list`, and `endpoint_detail` commands when invoked from an API run context.
- **API-focused ALICE system prompt** (`services/prompts/alice.py`): Updated to instruct ALICE on OWASP API Top-10 categories and available API context tools.

#### UI

- **API Collections screen** (`web/app.js`): List, create, and manage API collections. Document upload panel (drag-and-drop or file picker) with parse status. Endpoint table with scope toggles and readiness indicators.
- **Endpoints / work-program screen**: Coverage matrix table showing per-endpoint × per-category status (`uncovered`, `in_progress`, `covered`, `skipped`). Status badges update in real time via the event stream.
- **API test run detail**: Activity log panel, findings panel, traffic panel, and ALICE chat tab — all equivalent to the web scan run detail view.
- **Log panel & findings export**: Agent log viewer with per-entry expand, bulk export to JSON.
- **Credential display**: Credentials discovered or provided during document parsing surfaced in the collection detail panel.

#### Test Coverage

- `tests/test_api_alice_context.py` (391 lines)
- `tests/test_api_collections_api.py` (322 lines)
- `tests/test_api_coverage.py` (505 lines)
- `tests/test_api_docs.py` (501 lines)
- `tests/test_api_readiness.py` (355 lines)
- `tests/test_api_scanner.py` (421 lines)
- `tests/test_api_test_runs.py` (203 lines)

#### Documentation

- `docs/api-collection-testing-plan.md` (465 lines): design document for the API collection and testing pipeline.
- `docs/api-test-files/`: sample auth credential file and Markdown API specification used for development testing.

#### Database & Schema

- New tables: `api_collection`, `api_document`, `api_endpoint`, `api_credential`, `api_test_run`, `api_endpoint_test`.
- `api_test_run` carries `coverage_mode`, `sast_run_id` (back-reference populated in PR #160), and ALICE session state.

---

### Included: PR #160 — SAST Assistance for API Scans

*Merged to develop: 2026-06-12*

Introduces an agentic SAST scanner that analyses uploaded source archives and feeds high-confidence vulnerability leads into the dynamic API scan pipeline (17 files, ~2,700 insertions).

#### SAST Scanner (`services/sast_scanner.py`, 761 lines)

- **Safe archive extraction** (`_safe_unzip`): Extracts source ZIP uploads into a sandboxed temp directory, rejecting any entries that would escape via path traversal.
- **Read-only file tools**: The agentic loop is equipped with `list_files`, `glob`, `read_file` (capped at 20,000 chars per response), and `grep` (capped at 200 results) — all path-jailed to the extraction root.
- `**write_lead` / `filter_lead` / `done` tools**: The agent calls `write_lead` to propose a candidate finding (title, description, OWASP category, severity, confidence, location, evidence). `filter_lead` scores candidates against a confidence threshold (0.7) before persisting as `ScanLead` rows. Unfiltered candidates at scan end are flushed with their raw confidence.
- `**SastRun` lifecycle** (`create_sast_run`, `start_sast_scan`, `stop_sast_scan`, `get_sast_status`): Task registry mirrors the web and API scanner patterns.
- **SAST system prompt** (`services/prompts/sast.py`, 279 lines): OWASP API Top-10 focused static analysis instructions, with tool schemas for `list_files`, `glob`, `read_file`, `grep`, `write_lead`, `filter_lead`, and `done`.

#### ScanLead Entity & Service (`models.py`, `services/scan_leads.py`, 167 lines)

- `**ScanLead` model**: Stores producer run ID and type, collection ID, title, description, category, severity, confidence score, source file location, and evidence snippet. Status field (`open` / `used`) allows the dynamic scan to consume leads without re-scanning.
- `**get_open_leads_for_collection**`: Returns open leads sorted by severity then confidence, consumed by the API scanner's agentic loop context to prioritise dynamic probes.
- `**needs_fresh_sast**`: Returns `True` when no completed SAST run exists within the last 24 hours for the collection, used to gate automatic pre-phase creation.

#### Automatic SAST Pre-Phase in API Scans

- **Auto-trigger** (`services/api_scanner.py`, `_do_api_thinking_scan`): When an API scan starts and the collection has a `source_zip` document with no fresh completed SAST run, a `SastRun` is automatically created, awaited to completion, and its leads are made available to the dynamic scan context before the agentic loop begins.
- **Back-reference**: `ApiTestRun.sast_run_id` is written once the auto-created SAST run is known, linking the two runs in the DB.
- **Phase events**: `scanner_phase` SSE events with `phase: sast_prephase` emitted at start and complete so the UI can display SAST progress inline with the API scan activity log.
- **Best-effort**: SAST pre-phase failures (e.g., no source ZIP, LLM error) are logged and the dynamic scan continues unaffected.

#### SAST API (`api/sast_runs.py`, 322 lines)

| Endpoint                                   | Description                                             |
| ------------------------------------------ | ------------------------------------------------------- |
| `POST /api/api-collections/{id}/sast-runs` | Create a SAST run (auto-selects most recent source ZIP) |
| `GET /api/sast-runs/{id}`                  | Run summary                                             |
| `POST /api/sast-runs/{id}/scan/start`      | Start the SAST scan                                     |
| `POST /api/sast-runs/{id}/scan/stop`       | Stop the SAST scan                                      |
| `GET /api/sast-runs/{id}/scan/status`      | Scan status                                             |
| `GET /api/sast-runs/{id}/events`           | SSE event stream                                        |
| `GET /api/sast-runs/{id}/leads`            | List all `ScanLead` rows for the run                    |
| `GET /api/sast-runs/{id}/agent-log`        | Agent activity log                                      |

#### UI

- **SAST run panel** (`web/app.js`, +390 lines): Launch and monitor SAST scans from the collection detail view. Lead list with severity, confidence score, location, and evidence columns.
- **Agent log integration**: `AgentLog` and `ScanLog` entries persisted and surfaced in the SAST run detail panel.
- **Finding description fix** (`fix display of finding description in api scans`): API scan finding descriptions were rendered as `[object Object]` in the frontend due to an incorrect field access path; fixed to read the string value correctly.
- **Agent log collision fix** (`fix: agent logs were colliding between web and api runs`): `AgentLog` entries from concurrent web and API scan runs were being written to the wrong run's log due to a shared context variable; scoped correctly per run.

#### Database & Schema

- New tables: `sast_run`, `scan_lead`.
- `api_test_run` table: `sast_run_id` column added.

#### Documentation

- `docs/sast-scan-leads-plan.md` (417 lines): design document for the SAST pre-phase and scan leads pipeline.

### Version

- `pyproject.toml`: bumped to `0.5.20260612.6`.

---

## [PR #141] 7th June Update

**Opened:** 2026-06-07 | Branch: `develop → main`

Verified proof-of-concept generation for confirmed findings, optional temperature parameter for LLM profiles, and an ALICE session identity fix (27 files, ~780 insertions).

### Verified Proof-of-Concept Commands (New)

- **PoC generation in validator** (`services/validator.py`): When the adversarial validator confirms a finding, it now attempts to build and execute a `curl` command that re-produces the issue server-side. The command is only persisted to the finding if the re-run passes all assertions, so `poc_command` is always a proven reproducer rather than a speculative template.
- **Safety constraints**: Only idempotent `GET`/`HEAD` requests are accepted as PoC candidates — state-changing methods (`POST`, `PUT`, `PATCH`, `DELETE`) are rejected. The PoC URL must match the host of the affected finding to prevent SSRF / out-of-scope requests. A `_POC_BLOCKED_HEADERS` allowlist filters dangerous request headers, and a header count cap prevents oversized payloads.
- **Auth credential handling** (`_resolve_poc_auth`, `_build_curl_command`): Live session credentials (cookies or bearer tokens) are never embedded in the command string. Instead, the command reads from a local token file at runtime via `$(cat <token-file>)`, with a `_build_poc_setup` helper generating human-readable instructions for capturing the session credential (JS console snippets for readable cookies/JWT, DevTools Network tab steps for HttpOnly session cookies).
- **Deterministic validator updated**: `_deterministic_validate_finding` now returns a third element carrying the PoC spec so access-control findings confirmed by HTTP replay also receive a `poc_command`.
- `**done()` tool schema extended** (`services/prompts/validator.py`): The validator agent's `done()` tool now accepts `poc_request`, `poc_expect`, and `poc_auth` fields. The system prompt instructs the agent to supply a single decisive GET/HEAD request and a distinctive assertion (HTTP status and/or `body_contains` substring). The server re-runs the request and discards the PoC if the assertion fails.

### Optional Temperature Parameter

- `**temperature` made nullable** (`models.py`, `schemas.py`, `db.py`): The `temperature` field on `LLMConfig` is now `Optional[float]` (defaults to `None`). A SQLite table-rebuild migration (`_ensure_llm_config_temperature_nullable`) makes the column nullable for existing databases. When `temperature` is `None`, the parameter is omitted entirely from all LLM API call sites (Anthropic, OpenAI, Bedrock Runtime, Azure Foundry Anthropic, Google Gemini, and the `_chat_completion_kwargs` shared path).
- **UI checkbox toggle** (`web/app.js`): The LLM profile form now shows a checkbox next to the temperature input. When unchecked, the field is disabled and `null` is sent in the save payload. The default profile form raises `max_tokens` from 4,096 to 70,000 and sets a default temperature of 0.2.
- **Export/import schema updated**: `LLMExportProfileItem` defaults updated to `max_tokens=70000` and `temperature=None`.

### ALICE Session Identity Fix

- `**run_created_at` token** (`api/alice.py`): `GET /alice/sessions` now returns a `run_created_at` timestamp derived from `TestRun.created_at`. The client can use this token to detect when a new run has been assigned a previously-deleted run's integer ID (SQLite reuses primary keys) and discard stale `localStorage` chat history that belongs to the deleted run.

### UI

- **PoC command panel in findings** (`web/app.js`): Confirmed findings with a `poc_command` now display a "Validation Command (verified)" block with a one-click copy button and a collapsible "Setup" section showing credential-capture instructions.
- **Markdown export**: `findingsToMarkdown` and `parseFindingsMarkdownSections` round-trip `poc_command` and `poc_setup` as `### Validation Command` and `### Validation Setup` sections.
- **Finding import API** (`api/scan.py`): `poc_command` and `poc_setup` are now preserved when importing findings.

### Database & Schema

- `scan_finding` table: `poc_command TEXT NOT NULL DEFAULT ''` and `poc_setup TEXT NOT NULL DEFAULT ''` columns added via migration.
- `llm_config` table: `temperature` column made nullable via SQLite table rebuild migration.

### Test Coverage

- `tests/test_poc_validation.py` (new, 173 lines): Unit tests for `_poc_url_in_scope`, `_resolve_poc_auth`, `_build_curl_command`, `_run_and_assert_curl`, `_poc_assertion_holds`, `_build_and_verify_poc`, and rejection of unsafe methods / out-of-scope URLs / missing sessions.
- `tests/test_alice_service.py`, `tests/test_settings_api.py`, `tests/test_db_migration.py`, `tests/test_validation_logic.py`: Updated for the new fields and schema changes.

### Version

- `pyproject.toml`: bumped to `0.4.20260607.6`.

---

## [PR #130] 4th June Release

**Merged:** 2026-06-04 20:47 AEST | Branch: `develop → main`

Bundles scanner improvements, ALICE session fixes, and a new file upload attack specialist across 42 files (12,841 insertions, 103 deletions).

### Browser-Interactive Login Flow

- **Browser-based login** (`services/crawler.py`): Replaced the `seed` curl login method with a fully functional browser-interactive login flow. The crawler now uses a headless browser to complete login forms, resolving issues with JavaScript-heavy authentication pages.
- **Headless host detection**: Displays an informational error when interactive logins are attempted on headless hosts where no display is available, preventing silent failures.

### ALICE Fixes

- **Session token vault** (`services/alice.py`, `#120`): ALICE's tool executor now loads the per-run session vault at the start of each turn. `http_request` and `browser` tool calls carry the primary authenticated session by default, honour `use_session` to switch identities, and accept `"anonymous"` to opt out. `forge_jwt` and `register_account` surface newly created sessions into the in-memory vault so later steps in the same turn can reference them immediately. Previously all ALICE probes were sent anonymously even when stored credentials existed.
- `**finding_list` returns live DB findings + vuln-class filter** (`services/alice.py`, `services/scanner.py`, `#124`): ALICE and specialist context-tool handlers were passing `findings_snapshot=[]` into `_run_thinking_context_tool`, so `finding_list` always returned count 0. A shared `_load_findings_snapshot` helper now reads from the database. A `category` filter is also added so agents can search by vuln-class slug (`sqli`, `xss`, `ssrf`, etc.) matching the `attack_class` vocabulary; unknown slugs degrade to a free-text search token. Documented in the Test Lead and ALICE prompts.

### Scanner Improvements

- **SQLi chaining depth** (`services/prompts/test_lead.py`, `#97`): After confirming a SQL injection, the agent now executes a structured post-confirmation escalation sequence: DB user identity, table enumeration (names only), MSSQL `xp_cmdshell` RCE probe, MySQL `LOAD_FILE` read probe, and PostgreSQL `COPY TO PROGRAM` OS exec probe. Hard constraint remains read-only — no `DROP`/`INSERT`/`UPDATE`/`DELETE` and no bulk PII dump.
- `**auth_robustness` skill scoping** (`services/prompts/specialist.py`, `#98`): The `auth_robustness` WSTG skill is now gated on an actual credential-submission endpoint rather than the broad `has_auth_pages` signal (which was true for any authenticated page, including dashboards). A `_CREDENTIAL_PATH_FRAGMENTS` set and a dedicated `has_credential_endpoint` check now gate this skill; the site's configured `login_url` is fed into the selector so non-standard login paths still trigger correctly. `auth_bypass` and `sessions` remain on the broader authenticated surface.
- **Password compliance finding and SSRF improvements** (`#98`): Improved accuracy of password policy compliance findings and SSRF detection logic.
- **Traffic logging fixes** (`services/traffic.py`, `#128`): Fixed issues with traffic request logging — requests are now fully and correctly captured.

### File Upload Specialist (New)

- `**file_upload` attack class** (`services/prompts/specialist.py`, `services/prompts/test_lead.py`, `services/scanner.py`): New specialist agent dispatched as soon as an upload endpoint is confirmed. Tests extension filtering (`.php`, `.php3`, `.phtml`, `.phar`, `.jsp`, `.aspx`, etc.), extension bypass tricks (mixed case, double extension, trailing dot, null-byte, alternate extensions), content-type spoofing, and path traversal in filename parameters. Uploads a canary webshell (`aespa_rce_` marker) and fetches the stored URL to confirm execution. Severity: CRITICAL if RCE is confirmed, HIGH if a dangerous extension is stored but not executed.
- **Specialist dispatch registered**: `dispatch_file_upload` added to `_SPECIALIST_DISPATCH_CLASSES` in `scanner.py` and `file_upload` appended to `_SKILL_ORDER`.
- **Thinking agent system prompt updated**: Now dispatches a `file_upload` specialist on upload endpoint discovery without waiting for manual extension probing.

### New API & Scan Endpoint

- `**/api/scan.py` additions** (61 lines): New scan-related API endpoints added.
- **Database and schema extensions** (`db.py`, `models.py`, `schemas.py`): Model and schema additions to support new features.

### Documentation & Test Coverage

- `docs/advanced-auth-implementation.md` added (109 lines) — documents the browser-interactive authentication flow.
- `docs/aespa-boe-2026-06-01.md` added (10,769 lines) — scan results document.
- `docs/results-comparison.md` updated with new comparison data.
- `README.md` refreshed; all UI screenshots updated.
- New test suites: `test_alice_service.py` (122 lines), `test_scanner_service.py` (98 lines), `test_traffic_service.py` (131 lines), `test_wstg_skill_selector.py` (112 lines).

---

## [PR #119] ALICE Bug Fixes

**Opened:** 2026-05-31 | Branch: `develop → main`

Four targeted fixes addressing ALICE session persistence, job visibility, token attribution, and adds expandable step-detail blocks to the thought-process panel (8 files changed).

- **Cross-machine session race condition** (`app.js`): On a new machine, all chat messages were being overwritten with the default welcome message. Root cause — on mount, the save `useEffect` ran synchronously and wrote `Date.now()` (T1) to `localStorage.alice_chats_${runId}_savedAt` before the async `getAliceSessions` call resolved. The server's `updated_at` (T0, an older timestamp) was always less than T1, so the server data was silently discarded and the 800 ms debounce then overwrote the server's history. Fix: added an `_aliceServerLoaded` ref (initially `false`); the save effect returns early until the ref is set; the load effect sets it to `true` in all exit paths (server-wins, local-wins, empty response, and `.catch()`), so comparisons always run against a `localSavedAt` written by a *previous* session rather than the current mount.
- **ALICE jobs now appear in active jobs panel** (`api/test_runs.py`): `list_active_jobs` checks `alice_tasks.get(run.id)` and appends an `ActiveJobSummary` with `job_type="A.L.I.C.E."` when a background task is running, so in-progress ALICE conversations are surfaced alongside scanner jobs.
- **Token counters now attributed to the correct run** (`services/alice.py`): `llm_svc.set_run_context(run_id, ...)` is called at the start of `run_alice_turn_stream` so all LLM calls inside the agentic loop increment the per-run token usage counters; `llm_svc.clear_run_context()` is called in the `done` event path to release the context.
- `**write_finding` validation + activity-log events** (`services/alice.py`): The `write_finding` tool handler now captures the returned `saved` object. If a finding was saved, `validate_finding_inline` is scheduled as a background task and a persisted `agent_status` event (role `Reporting`) is emitted with the finding ID. If the write fails an error event is also persisted, making both successes and failures visible in the activity log.
- **Expandable step-detail blocks** (`services/alice.py`, `app.js`, `styles.css`): Three new SSE event types are emitted during the agentic loop — `step_llm_call` (serialised last-N input messages via `_build_step_messages`/`_summarize_content` helpers), `step_tool_call` (tool name + JSON-safe input), and `step_tool_result` (truncated result preview). The frontend accumulates these into `session.stepData` keyed by step number and renders expandable `<details>` blocks in the thought-process panel so developers can inspect the exact LLM context, tool inputs, and raw results for each step.

---

## [PR #114] A.L.I.C.E. — Interactive Pentesting Chat Agent

**Merged:** 2026-05-30 22:49 AEST | Branch: `tester-chat → main`

Introduces A.L.I.C.E. (AI LLM-Integrated Chat Engine), an interactive user-directed pentesting agent embedded directly in the scan UI. Covers the full feature from initial chat interface through background task persistence, stream resume after page refresh, server-side session storage, and a suite of correctness fixes (~40 files changed).

### Architecture

- **Background task registry** (`services/alice_tasks.py`): ALICE agentic loops now run as `asyncio.create_task` entries in a module-level registry keyed by `run_id`, fully decoupled from the HTTP connection. The agent keeps executing tools on the server even when the browser refreshes or navigates away.
- **SSE event buffer with cursor-based replay**: Every event emitted by the task is appended to `AliceTask.events` (capped at 2,000 entries). On reconnect `GET /alice/stream?cursor=N` replays buffered events from position N, then switches to live delivery — no missed events after a page refresh.
- **Stream resume on page load**: `GET /alice/status` is polled on component mount; if a task is running the client automatically reconnects to the event stream and rebuilds the chat UI from the buffer.

### New API endpoints (`api/alice.py`)

| Endpoint                     | Description                                                                        |
| ---------------------------- | ---------------------------------------------------------------------------------- |
| `POST /alice/run`            | Start a background ALICE task (returns immediately; agent runs server-side)        |
| `GET /alice/stream?cursor=N` | SSE stream with replay from position N                                             |
| `DELETE /alice/run`          | Cancel the running task; emits a final `done` event with partial content           |
| `GET /alice/status`          | Check whether a task is running; returns `tab_id`, `think_msg_id`, `reply_msg_id`  |
| `GET /alice/sessions`        | Load persisted chat sessions (returns `updated_at` for cache-freshness comparison) |
| `PUT /alice/sessions`        | Save chat sessions (debounced 800 ms on the client)                                |

### Server-side chat persistence

- **Normalised schema**: `AliceChatSession` (one row per tab) + `AliceChatMessage` (one row per bubble) replace a blob-per-run design. Message text is updated in-place; large streaming responses produce a single row update rather than a full JSON rewrite.
- **Multi-user support**: Any browser opening the same scan URL sees the full conversation history immediately.
- **Freshness comparison**: `GET /alice/sessions` returns `updated_at`; the client compares it against a local `savedAt` timestamp so a same-user page refresh keeps the fresher local state while a different-user load correctly takes the server version.

### UI

- **ALICE chat panel** in the run detail Activity tab: multi-session tabs, collapsible thought-process bubbles, tool-call cards, markdown reply rendering.
- **Stop A.L.I.C.E. button**: appears in the run topbar whenever a background task is running; aborts the local SSE connection and sends `DELETE /alice/run` to cancel the server task.
- **Thought process renders graphically during streaming**: subscriber writes `session.accumulatedThought` (the complete running total) to React state on each chunk, so `parseAliceThinking` always receives a parseable string rather than partial text.
- **ALICE panel open by default** (removed from the initially-collapsed agent set).
- **Newline separation**: each new LLM text block is preceded by `\n\n` when prior message content exists, preventing consecutive paragraphs from running together.

### Bug fixes

- `**write_finding` false deduplication** (`skip_normalize=True`): `normalize_finding_titles` was renaming ALICE findings to match existing titles of unrelated findings that share an OWASP category, causing them to be dropped as duplicates. ALICE findings now bypass normalisation; exact-title dedup still applies.
- `**agent_dispatch` was a no-op**: `dispatch_specialist_agent` was imported but never defined; the import raised `ImportError` which was silently swallowed. Added the public wrapper `dispatch_specialist_agent` in `scanner.py` that bootstraps LLM config, scanner policy, specialist config, session vault and recon summary from the DB before calling `_schedule_specialist_agent`.
- `**browser` tool import error**: Was importing `_execute_browser_steps` (non-existent); replaced with a direct `httpx` page fetch using the same client as `http_request`.
- `**get_run_scanner_policy` wrong call signature**: Was called as `get_run_scanner_policy(run_id)` but requires `(session, run)`; replaced with `_get_alice_timeout(run_id)` helper that opens its own session.
- `**_scope_err` typo**: Variable `scope_err` was referenced as `_scope_err` in the HTTP request scope-check path.
- `**\\n` vs `\n` in SSE deltas**: Thinking chunk deltas contained literal `\n` (backslash-n) rather than actual newlines, causing `parseAliceThinking`'s line-split to produce no separators and rendering all status blocks as raw text.
- **304 Not Modified caching bug** (`main.py`): `app.js` and `styles.css` are now served as explicit FastAPI routes that read and return the file directly, bypassing `StaticFiles`' ETag/conditional-GET handling. A normal browser refresh (Cmd-R) no longer serves a stale cached version of the JavaScript bundle.

### Documentation

- `docs/architecture.md`: new §15 A.L.I.C.E. documenting the background task registry, reconnect/replay mechanics, agentic loop, all 10 tools, finding persistence design, client-side streaming state model, and Stop A.L.I.C.E. flow. Other sections updated: repository layout, system overview, data models, multi-agent diagram, API layer, frontend tabs, concurrency.

---

## [PR #102] DeepSeek Support, Anthropic Caching & Reporting Lab

**Merged:** 2026-05-30 22:33 AEST | Branch: `develop → main`

Bundles three develop releases into main: DeepSeek model compatibility, improved Anthropic prompt caching, and the new Reporting Lab capture-replay debugging feature (24 files, 2,699 insertions, 556 deletions).

### Included: PR #95 — DeepSeek Model Support & Provider Fixes

*Merged to develop: 2026-05-27 14:56 AEST*

- **DeepSeek / reasoning model support**: Added a `force_tool_choice` boolean toggle on LLM profiles. DeepSeek R1-series and other reasoning models (`r1`, `reasoner`, `thinking` in model name) cannot force tool execution, so the agentic loop now skips the `tool_choice: required` constraint for those models.
- **Gemini over-commentary fix**: Removed extraneous preamble text that Gemini models were prepending to responses.
- **Removed obsolete Bedrock API scripts**: Deleted `bedrock-api-scripts/` directory (PowerShell and shell credential helpers that are no longer used).
- Test coverage added for `force_tool_choice` behaviour and new settings API paths.

### Included: PR #96 — Improved Anthropic API Token Caching Strategy

*Merged to develop: 2026-05-27 19:56 AEST*

- **Sliding cache-point strategy**: Replaced the previous approach (only caching the static system prompt) with a `_with_anthropic_cache` helper that attaches an ephemeral `cache_control` block to the last message and the last tool definition on every turn. This enables Anthropic's prefix extension caching to carry forward the growing conversation context, not just the system prompt.
- Cache points are applied non-destructively (copies, not in-place mutation) to avoid corrupting the caller's message lists.
- Expanded `test_llm_service.py` with 121 lines of caching unit tests.

### Included: PR #101 — Reporting Lab: Capture Replay & Prompt Debugging

*Merged to develop: 2026-05-28 21:53 AEST*

- **New Reporting Lab UI tab**: Full capture-replay debugging interface for the LLM reporting pipeline. Allows selecting a stored capture, replaying it against any saved prompt version, and comparing findings side-by-side across replays.
- `**reporting_debug.py` service** (624 lines): Core logic for storing captures, running replays asynchronously, and computing finding-level diff statistics between replay runs.
- `**/api/reporting-debug/` router** (176 lines): REST endpoints for captures, replays, prompt version management, and replay comparison.
- **Prompts refactor**: Reporting prompt strings (`_ANALYSE_PROMPT`, `_WRITEUP_REPLAY_PROMPT`, etc.) extracted into `src/aespa/services/prompts/reporting.py`; `llm.py` imports and re-exports them for downstream consumers.
- `**DebugFindingsTable` component**: New collapsible findings table in the frontend with severity ordering, CVSS inline display, and per-instance independent expand state — used in both the capture detail panel and the side-by-side replay comparison view.
- `test_reporting_debug.py` (89 lines) and 155 lines added to `test_llm_service.py`.

---

## [PR #94] LLM Rate Limiting, Local Timezone Display & UI Polish

**Merged:** 2026-05-25 20:39 AEST | Branch: `develop`

Introduces provider-level LLM API rate limiting, local timezone date formatting in the UI, and key frontend bug fixes and polish (9 files, 286 lines changed).

- **LLM API Rate Limiting per Provider**:
  - Implemented an `AsyncTokenBucketLimiter` for pacing calls based on TPM (Tokens Per Minute) and RPM (Requests Per Minute) configured in `LLMProviderConfig`.
  - Added smart token count estimation for prompt text and image payloads (with vision-token scaling per provider).
  - Emits real-time SSE pacing notifications ("LLM rate limit reached. Pacing and temporarily slowing down requests...") when limits are hit.
  - Automatically reconciles pacing buckets against actual usage recorded post-call and on failures.
- **Local Timezone Display**:
  - Introduced `parseDate` utility on the frontend to parse UTC strings containing custom formats.
  - Formats all event logs, active scanner sessions, and traffic timelines in the user's local timezone.
- **UI & Configuration Polish**:
  - **Findings Display Fix:** Fixed a reference error where `deterministicCount` was undefined, correcting deterministic findings rendering.
  - **Cloudflare Username Toggle:** Defaulted the `showUsername` header toggle in localStorage to `true`.
  - Version bump in `pyproject.toml` and updated lockfiles.

---

## [PR #89] LLM Refactor, Cloudflare Access Integration & Pure Agentic Scan

**Merged:** 2026-05-24 21:55 AEST | Branch: `develop`

Major re-architecture removing structured scans, introducing separate LLM providers/profiles with import/export, cryptographic Cloudflare Access JWT verification, prompt package modularisation, and reporting improvements (34 files, 4,300 lines changed).

- **Structured Scan Mode fully removed** — 2,552 lines of code removed from scanner service, APIs, and UI; the agentic scan is better.
- **LLM Configuration & Credentials Refactor**:
  - Separated API credentials and endpoints from configuration profiles via new `LLMProviderConfig` entity.
  - Added export/import capability for providers and profiles via portable JSON bundle endpoints (`/llm/export` and `/llm/import`).
  - Redesigned LLM Settings UI allowing management of multiple providers and configuration profiles.
  - Added database migrations and robust setting/profile APIs with test suites.
- **Prompts Package Re-architecture** — Extracted all hardcoded prompt templates from core services into a new package (`src/aespa/services/prompts/`), cleaning up `llm.py` and `scanner.py`.
- **Cloudflare Access JWT verification** — Implemented cryptographic verification of Cloudflare Access JWT assertion headers (`cf-access-jwt-assertion`) using dynamic JWKS retrieval to display the authenticated email in the UI breadcrumb.
- **Reporting & UI Activity Log Improvements**:
  - Ensured final agent activity logs persist when scans complete (`_persist=True`), fixing a bug where they vanished.
  - Fine-tuned prompt instructions to rate low-risk/low-confidence issues as low severity.
  - Set Google API default base URL to `https://generativelanguage.googleapis.com` and resolved UI placeholders.
  - Fixed `validator` trigger where finding message used `finding.url` instead of `finding.affected_url`.
- **New Scan Results & Documentation updates**:
  - Added `scan-results-2026-05-24.md` detailing ground-truth coverage comparisons and new findings (e.g., default admin credentials `admin`/`admin123`).
  - Refreshed comparison tables and other project documentation.

---

## [PR #79] Documentation Update

**Merged:** 2026-05-21 22:34 AEST | Branch: `develop`

- Created `docs/vuln-scanner-comparison.md` containing ground-truth analysis against 23 intentional OWASP Top 10 vulnerabilities in `BankOfEd` across multiple LLM configurations.
- Substantially expanded `docs/architecture.md` (+291 lines) to document scan phases and LLM integration.
- Minor updates to `README.md`.

---

## [PR #78] Fix Duplicate Issue Findings

**Merged:** 2026-05-21 22:03 AEST | Branch: `develop`

- Fixed duplicate issue findings being generated in the scanner service
- Minor LLM service fix for deduplication logic
- Version bump

---

## [PR #76] Hunter Agents — Specialist Agent & Attack Surface

**Merged:** 2026-05-21 14:49 AEST | Branch: `hunter-agents`

Major architectural release introducing specialist recon/hunter agents and attack surface mapping (33 files, 6,203 lines changed).

- **Specialist agent** — dedicated recon agent implemented (`llm.py` +736 lines); runs targeted reconnaissance passes separate from the main scan loop
- **Attack surface mapping** — new attack surface analysis phase implemented; surfaces endpoints, parameters, and inputs as structured intel before active testing begins
- **Scope service** — new `scope.py` (126 lines) for managing scan scope boundaries and filtering out-of-scope targets
- **Adversarial validator** significantly expanded (`validator.py` +307 lines) — improved adversarial payload validation logic
- **Task graph** expanded (+296 lines) to coordinate specialist agent work alongside main scan tasks
- **LLM service** major expansion (+736 lines) — new agent orchestration, recon prompts, and specialist invocation logic
- **Scanner service** major expansion (+1,020 lines) — integrates specialist agents and attack surface phases into the scan lifecycle
- **Web UI** major overhaul (`app.js` +1,149 lines, `styles.css` +169 lines) — agent status view, attack surface panel, improved activity log
- **New API endpoints** — settings, sites, test runs, and traffic APIs extended
- **New test suites** — adversarial validator (235 lines), recon summary (219 lines), specialist agent (269 lines)
- **Architecture documentation** — `phase0-baseline.md` (362 lines) and `recon-hunter-plan.md` (807 lines) added under `docs/agent-architecture-revamp/`
- Database models and schemas extended for new agent and attack surface data
- Issue merge/deduplication methodology updated

---

## [PR #69] Scan Resume + XSS Improvements

**Merged:** 2026-05-19 12:16 AEST | Branch: `develop`

Adds a scan resume capability and a deterministic JS source analysis phase that identifies unsanitized `innerHTML` sinks before dynamic testing begins. Extends the stored XSS canary sweep to confirm cross-user exploitation when multiple credentials are configured.

- **Scan resume** — new `checkpoint.py` service (145 lines) allows interrupted scans to resume from the last checkpoint rather than restarting
- **JS sink analysis phase** (`_analyse_js_sinks`) — fetches every discovered JS file and regex-scans for `innerHTML`/`outerHTML`/`document.write`/`insertAdjacentHTML` assignments lacking a sanitizer call (`escapeHtml`, `DOMPurify`, etc.); saves `TargetIntelItem(kind=xss_sink)` per unique unsanitized sink
- **Info-severity findings** — one `ScanFinding(severity=info)` per identified sink written immediately to the findings panel, before dynamic confirmation
- **Cross-user canary sweep** — second pass in `_stored_xss_sweep` that POSTs the canary to each sink's write endpoint (resolved via `kind=input` intel items), then re-fetches render pages as a victim session; any unescaped canary in the victim view produces a confirmed high-severity finding with cross-user evidence
- **Thinking-scan bootstrap** — `_analyse_js_sinks` runs at the start of `_do_thinking_scan` so `xss_sink` items are available in `target_inventory` before the LLM loop begins
- **WSTG XSS skill updated** — new Step 0 in the XSS skill block instructs the agent to consult `target_inventory` for `xss_sink` items, resolve their write endpoints via `kind=input` intel, and confirm with a victim-session browser check
- **Architecture docs updated** — `architecture.md` updated to document the new scan phases, `xss_sink` intel kind, and cross-user sweep; `xss-fix.md` writeup added (162 lines)
- Fix for long delay at end of scan before findings are written to the database
- Fix for site import bug
- LLM service expanded (+58 lines) for better XSS-related prompting
- Database models and schemas extended to support checkpoint state
- Web app improvements
- Strix/Sonnet 4.6 comparison added to `results-comparison.md`

---

## [PR #67] Documentation Update

**Merged:** 2026-05-16 22:09 AEST | Branch: `develop`

- `architecture.md` significantly expanded (+162 lines) — updated to reflect current scan phases and LLM integration
- `results-comparison.md` reorganised (+138 lines) — improved structure and added Strix/Sonnet 4.6 comparison
- README updated
- Screenshots refreshed (`activitylog.png`, `crawler.png`, `finding.png`)
- LLM service minor update (+31 lines)

---

## [PR #65] Burp Integration + Credential Persistence

**Merged:** 2026-05-16 21:03 AEST | Branch: `develop`

This release bundles the Burp Suite integration alongside credential persistence and prompt caching improvements introduced in PR #63 and PR #64.

- Burp Suite REST API integration — active scan triggering from within aespa
- Credential persistence across scan sessions
- Prompt caching added to LLM service to reduce token usage
- Fix for OpenAI-compatible models terminating scans early when no action is returned
- Unauthenticated crawl now runs automatically when credentials are added
- Settings and profiles system expanded
- Web UI improvements including form validation
- New test suites: settings, test runs, validation logic, web assets
- Python version and dependency updates

---

## [PR #64] Burp Suite REST Integration

**Merged:** 2026-05-16 21:01 AEST | Branch: `burp-integration`

- New `burp_rest.py` service module for communicating with the Burp Suite REST API
- Active scan triggering from aespa into Burp Suite — end-to-end working
- Scanner service refactored to support Burp integration flow
- Moved deterministic analysis out of structured scan mode
- Database models and schemas extended to support Burp scan metadata
- New test suites for validation logic and test runs API

---

## [PR #63] Credential Persistence & Prompt Caching

**Merged:** 2026-05-15 23:23 AEST | Branch: `develop`

- Discovered credentials now persisted across scan sessions
- Prompt caching added to LLM service
- Fix: OpenAI-compatible models no longer terminate scans early when a response contains no action
- Unauthenticated crawl now triggered automatically when authentication credentials are added
- LLM service expanded significantly (376 lines)
- Comprehensive LLM service test suite added
- Documentation updates

---

## [PR #61] Documentation Update

**Merged:** 2026-05-14 21:32 AEST | Branch: `develop`

- Comprehensive `architecture.md` added (441 lines) — full system architecture documentation
- `README.md` cleaned up and trimmed
- `results-comparison.md` reorganised
- Minor `juice-shop-results.md` update

---

## [PR #60] Re-architecture — Full Implementation Merge

**Merged:** 2026-05-14 16:17 AEST | Branch: `develop`

Bundles the complete re-architecture from PR #59 into `main` (36 files, 11,087 lines changed).

- Agentic scan loop fully implemented
- Task graph system (`task_graph.py`) for coordinating multi-page scan work
- Scanner sessions service (`scanner_sessions.py`) for managing active scans
- Sites service (`sites.py`) — 238 lines of new site management logic
- Scanner service completely revamped (3,735 lines)
- LLM service major expansion (1,004 lines)
- Crawler service enhanced (958 lines)
- Database and model extensions
- Extensive new test suites: crawler logic, scanner sessions, validation, test runs API
- Architecture diagrams added (`intelligence.png`, `taskgraph.png`)
- Pentest architecture improvement plan documented

---

## [PR #59] Re-architecture Exploration

**Merged:** 2026-05-14 16:16 AEST | Branch: `rearchitecture-exploration`

Ground-up redesign of the scanner and crawler for agentic scanning behaviour.

- Agentic scan loop — scanner no longer terminates prematurely on ambiguous states
- Task graph introduced to coordinate scanning work across pages
- Intelligence collection function added
- Additional dynamic scan tools implemented
- Deterministic vulnerability detection for structured scan mode
- Fixed traffic logging so requests are fully captured
- Fixed agent loop getting stuck on a page for excessive turns
- Caching bug fixes
- Column width adjustments in result tables
- `max_steps` limit removed
- Added Foundry Anthropic API support
- `dynamic-scan-tool-calls.md` documentation added

---

## [PR #48] Issue Deduplication & UI Improvements

**Merged:** 2026-05-10 23:43 AEST | Branch: `develop`

- New `findings.py` deduplication service — issues are grouped and deduplicated before reporting (392 lines)
- Findings now persisted even when they cannot be associated to a specific page
- Fixed incorrect tool calls causing dynamic scans to terminate early
- Active job display added to UI
- Sidebar UI improvements
- Fix for scan status indicator
- LLM service enhancements
- New test suites for scanner, LLM service, and test runs API

---

## [PR #43] Documentation Update

**Merged:** 2026-05-08 23:19 AEST | Branch: `develop`

- `README.md` expanded with additional project details (71 lines)
- `results-comparison.md` added with scan result comparisons (63 lines)
- Updated UI screenshots: activity log, findings, test runs, traffic log
- Version bump

---

## [PR #40] Extended Reasoning & Multi-LLM Support

**Merged:** 2026-05-08 22:07 AEST | Branch: `extended-reasoning`

Major feature release adding reasoning model support and a complete UI redesign (32 files, 5,529 lines changed).

- Extended thinking / reasoning model support in LLM service
- OpenRouter support added
- Per-run LLM profile selection — switch models between scan runs
- LLM profile switcher UI component
- Progressive reporting — findings stream into UI as scanning runs
- Revamped thinking loop for extended reasoning passes
- Chunk probe analysis calls so large thinking scans don't error at token limits
- Findings marked unconfirmed when auth credentials are unavailable
- Multiple login page support
- Stop button fixed; progress UI added
- Progress bar fixes
- UI responsiveness and activity status tracking improvements
- Import issues feature
- API display added to crawler
- Writeup engine updated
- Thinking block stripping
- Enhanced logging for thinking processes
- Site name added to breadcrumb bar
- Edit button added to test runs
- AWS Bedrock credential management scripts
- Scan delay adjustment
- Fix for first crawl page LLM context write
- Max tokens released from hard-coded 1024 to UI setting

---

## [PR #11] CI/CD Deployment Workflow

**Merged:** 2026-05-04 22:26 AEST | Branch: `main`

- GitHub Actions workflow added for SSH-based deployment
- Configuration module introduced

---

## [PR #9] Deployment Config & App Improvements

**Merged:** 2026-05-04 20:15 AEST | Branch: `develop`

- SSH deployment workflow via GitHub Actions
- Config module created
- Web app JS updated
- Version counter added

---

## [PR #8] Increased Probes & Improved Input Validation

**Merged:** 2026-05-04 12:52 AEST | Branch: `develop`

- Increased the number of probes permitted per page
- Improved input validation prompts sent to LLM
- Comprehensive crawler service implementation (445 lines)
- LLM service improvements
- Scanner service enhancements
- New test suites: crawler logic, traffic service, validation (421 lines total)
- Web UI and style improvements

---

## [PR #7] Crawler URL Validation

**Merged:** 2026-05-04 11:14 AEST | Branch: `develop`

Bundles the URL hallucination reduction work from PR #6.

- Validator added to remove hallucinated object references in URLs
- Old frontend React/TypeScript scaffolding removed; consolidated into web module
- Removed stale `.DS_Store` files
- `.gitignore` cleanup

---

## [PR #6] LLM Plumbing & URL Hallucination Reduction

**Merged:** 2026-05-04 11:04 AEST | Branch: `llm-plumbing-changes`

- Crawler improvements to reduce hallucinated URLs — validator strips invalid object references
- Scanner mode settings added to restrict HTTP method usage
- Crawler service major implementation (399 lines)
- Validator service comprehensive expansion (274 lines)
- LLM service enhancements
- Scanner service additions
- Schemas and settings extended for scan mode configuration
- Web UI significant updates (343 lines)
- New test suites: crawler, settings, test runs, validation (390 lines total)
- Cleanup of old/redundant files

---

## [PR #5] README Update

**Merged:** 2026-05-03 13:16 AEST | Branch: `develop`

- `README.md` expanded with project details
- `.gitignore` enhancements

---

## [PR #4] Sitemap Multi-User Crawl & Traffic Logging

**Merged:** 2026-05-03 12:24 AEST | Branch: `develop`

Substantial feature release (25 files, 2,998 lines changed).

- Multi-user crawl improvements — per-user scan progress tracked separately
- Traffic log introduced — all HTTP requests captured and surfaced in UI
- New `traffic.py` service (208 lines)
- New `events.py` service for scan event streaming (41 lines)
- Improved reporting — multiple instances of the same issue now grouped together
- Crawler service major refactor (803 lines)
- Scanner service extensive updates (604 lines)
- LLM service enhancements (268 lines)
- Validator service comprehensive implementation (332 lines)
- Web UI major updates (643 lines)
- CSS and styles improvements (252 lines)
- Scan progress bar fixed
- UI padding fixes

---

## [PR #3] Scanner Functionality (Initial)

**Merged:** 2026-05-02 12:33 AEST | Branch: `develop`

- Scanner service initial implementation (644 lines) — first working scan pipeline
- LLM service integrated into scanner
- Database models and schemas for scan tracking
- Web UI updated to surface scan results
- Style definitions added
- Documentation images: crawler, scan progress, site views
- New dependencies added

---

## [PR #2] Google API Support

**Merged:** 2026-05-02 11:55 AEST | Branch: `develop`

- Google Gemini API support added to LLM service
- Models and schemas updated for Google provider
- README expanded with Google API setup instructions
- Dependency updates (`uv.lock`)

---

## [PR #1] Initial Crawler Implementation

**Merged:** 2026-05-02 11:46 AEST | Branch: `develop`

Initial working release of the project.

- LLM-driven page classification
- Crawler with sitemap tool support
- New scan status tab
- Backend API: settings, sites, test runs endpoints
- Database schema and ORM models
- Web UI with Settings page, Site form, Sites list
- Full CSS styling (662 lines)
- Project configuration: `pyproject.toml`, `.env.example`, `.gitignore`
