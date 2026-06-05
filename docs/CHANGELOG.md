# Changelog

All pull requests merged to `main`, in reverse chronological order.

---

## [PR #130] 4th June Release
**Merged:** 2026-06-04 20:47 AEST | Branch: `develop → main`

Bundles scanner improvements, ALICE session fixes, and a new file upload attack specialist across 42 files (12,841 insertions, 103 deletions).

### Browser-Interactive Login Flow

- **Browser-based login** (`services/crawler.py`): Replaced the `seed` curl login method with a fully functional browser-interactive login flow. The crawler now uses a headless browser to complete login forms, resolving issues with JavaScript-heavy authentication pages.
- **Headless host detection**: Displays an informational error when interactive logins are attempted on headless hosts where no display is available, preventing silent failures.

### ALICE Fixes

- **Session token vault** (`services/alice.py`, `#120`): ALICE's tool executor now loads the per-run session vault at the start of each turn. `http_request` and `browser` tool calls carry the primary authenticated session by default, honour `use_session` to switch identities, and accept `"anonymous"` to opt out. `forge_jwt` and `register_account` surface newly created sessions into the in-memory vault so later steps in the same turn can reference them immediately. Previously all ALICE probes were sent anonymously even when stored credentials existed.
- **`finding_list` returns live DB findings + vuln-class filter** (`services/alice.py`, `services/scanner.py`, `#124`): ALICE and specialist context-tool handlers were passing `findings_snapshot=[]` into `_run_thinking_context_tool`, so `finding_list` always returned count 0. A shared `_load_findings_snapshot` helper now reads from the database. A `category` filter is also added so agents can search by vuln-class slug (`sqli`, `xss`, `ssrf`, etc.) matching the `attack_class` vocabulary; unknown slugs degrade to a free-text search token. Documented in the Test Lead and ALICE prompts.

### Scanner Improvements

- **SQLi chaining depth** (`services/prompts/test_lead.py`, `#97`): After confirming a SQL injection, the agent now executes a structured post-confirmation escalation sequence: DB user identity, table enumeration (names only), MSSQL `xp_cmdshell` RCE probe, MySQL `LOAD_FILE` read probe, and PostgreSQL `COPY TO PROGRAM` OS exec probe. Hard constraint remains read-only — no `DROP`/`INSERT`/`UPDATE`/`DELETE` and no bulk PII dump.
- **`auth_robustness` skill scoping** (`services/prompts/specialist.py`, `#98`): The `auth_robustness` WSTG skill is now gated on an actual credential-submission endpoint rather than the broad `has_auth_pages` signal (which was true for any authenticated page, including dashboards). A `_CREDENTIAL_PATH_FRAGMENTS` set and a dedicated `has_credential_endpoint` check now gate this skill; the site's configured `login_url` is fed into the selector so non-standard login paths still trigger correctly. `auth_bypass` and `sessions` remain on the broader authenticated surface.
- **Password compliance finding and SSRF improvements** (`#98`): Improved accuracy of password policy compliance findings and SSRF detection logic.
- **Traffic logging fixes** (`services/traffic.py`, `#128`): Fixed issues with traffic request logging — requests are now fully and correctly captured.

### File Upload Specialist (New)

- **`file_upload` attack class** (`services/prompts/specialist.py`, `services/prompts/test_lead.py`, `services/scanner.py`): New specialist agent dispatched as soon as an upload endpoint is confirmed. Tests extension filtering (`.php`, `.php3`, `.phtml`, `.phar`, `.jsp`, `.aspx`, etc.), extension bypass tricks (mixed case, double extension, trailing dot, null-byte, alternate extensions), content-type spoofing, and path traversal in filename parameters. Uploads a canary webshell (`aespa_rce_` marker) and fetches the stored URL to confirm execution. Severity: CRITICAL if RCE is confirmed, HIGH if a dangerous extension is stored but not executed.
- **Specialist dispatch registered**: `dispatch_file_upload` added to `_SPECIALIST_DISPATCH_CLASSES` in `scanner.py` and `file_upload` appended to `_SKILL_ORDER`.
- **Thinking agent system prompt updated**: Now dispatches a `file_upload` specialist on upload endpoint discovery without waiting for manual extension probing.

### New API & Scan Endpoint

- **`/api/scan.py` additions** (61 lines): New scan-related API endpoints added.
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
- **`write_finding` validation + activity-log events** (`services/alice.py`): The `write_finding` tool handler now captures the returned `saved` object. If a finding was saved, `validate_finding_inline` is scheduled as a background task and a persisted `agent_status` event (role `Reporting`) is emitted with the finding ID. If the write fails an error event is also persisted, making both successes and failures visible in the activity log.
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

| Endpoint | Description |
|---|---|
| `POST /alice/run` | Start a background ALICE task (returns immediately; agent runs server-side) |
| `GET /alice/stream?cursor=N` | SSE stream with replay from position N |
| `DELETE /alice/run` | Cancel the running task; emits a final `done` event with partial content |
| `GET /alice/status` | Check whether a task is running; returns `tab_id`, `think_msg_id`, `reply_msg_id` |
| `GET /alice/sessions` | Load persisted chat sessions (returns `updated_at` for cache-freshness comparison) |
| `PUT /alice/sessions` | Save chat sessions (debounced 800 ms on the client) |

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

- **`write_finding` false deduplication** (`skip_normalize=True`): `normalize_finding_titles` was renaming ALICE findings to match existing titles of unrelated findings that share an OWASP category, causing them to be dropped as duplicates. ALICE findings now bypass normalisation; exact-title dedup still applies.
- **`agent_dispatch` was a no-op**: `dispatch_specialist_agent` was imported but never defined; the import raised `ImportError` which was silently swallowed. Added the public wrapper `dispatch_specialist_agent` in `scanner.py` that bootstraps LLM config, scanner policy, specialist config, session vault and recon summary from the DB before calling `_schedule_specialist_agent`.
- **`browser` tool import error**: Was importing `_execute_browser_steps` (non-existent); replaced with a direct `httpx` page fetch using the same client as `http_request`.
- **`get_run_scanner_policy` wrong call signature**: Was called as `get_run_scanner_policy(run_id)` but requires `(session, run)`; replaced with `_get_alice_timeout(run_id)` helper that opens its own session.
- **`_scope_err` typo**: Variable `scope_err` was referenced as `_scope_err` in the HTTP request scope-check path.
- **`\\n` vs `\n` in SSE deltas**: Thinking chunk deltas contained literal `\n` (backslash-n) rather than actual newlines, causing `parseAliceThinking`'s line-split to produce no separators and rendering all status blocks as raw text.
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
- **`reporting_debug.py` service** (624 lines): Core logic for storing captures, running replays asynchronously, and computing finding-level diff statistics between replay runs.
- **`/api/reporting-debug/` router** (176 lines): REST endpoints for captures, replays, prompt version management, and replay comparison.
- **Prompts refactor**: Reporting prompt strings (`_ANALYSE_PROMPT`, `_WRITEUP_REPLAY_PROMPT`, etc.) extracted into `src/aespa/services/prompts/reporting.py`; `llm.py` imports and re-exports them for downstream consumers.
- **`DebugFindingsTable` component**: New collapsible findings table in the frontend with severity ordering, CVSS inline display, and per-instance independent expand state — used in both the capture detail panel and the side-by-side replay comparison view.
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
