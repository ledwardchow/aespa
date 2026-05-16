# Changelog

All pull requests merged to `main`, in reverse chronological order.

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
