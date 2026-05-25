# Changelog

All pull requests merged to `main`, in reverse chronological order.

---

## [PR #94] LLM Rate Limiting, Local Timezone Display & UI Polish
**Merged:** Pending (Open PR) | Branch: `develop`

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
