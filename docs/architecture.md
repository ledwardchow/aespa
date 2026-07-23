# AESPA — Architecture & Internal Workings

AESPA (AI-Enabled Security Pentesting Agent) is an LLM-driven automated security scanner. It covers three distinct surfaces:

- **Web application scanning** — discovers endpoints through an intelligent crawl, then probes them via an **agentic dynamic scan**: the LLM acts as an autonomous Test Lead agent, deciding what to attack next in a loop, and can spawn focused **Specialist Agents** to deep-dive on confirmed leads. An **OWASP Coverage** matrix tracks per-page OWASP Top-10 coverage with Track/Enforce modes.
- **API scanning** — parses OpenAPI/Swagger/Postman specs and source ZIP archives into a structured **API collection**, drives the same agentic scan loop against REST endpoints without a browser, and tracks OWASP API Top-10 coverage in a per-endpoint matrix.
- **SAST assistance** — a standalone agentic static-analysis pass over an uploaded source ZIP that identifies high-confidence vulnerability **leads**. Users explicitly import completed SAST results into either a web or API test run. Leads are unproven hypotheses the dynamic loop reproduces against the live target before writing a finding.

---

## Index

1. [Repository Layout](#1-repository-layout)
2. [How to Run](#2-how-to-run)
3. [System Overview](#3-system-overview)
4. [Configuration](#4-configuration)
   - [LLM Configuration (`LLMProviderConfig` & `LLMConfig`)](#llm-configuration-llmproviderconfig--llmconfig-models)
   - [LLM Profiles (`LLMProfile`)](#llm-profiles-llmprofile-model)
   - [Scanner Policy](#scanner-policy-scannerpolicy-model)
   - [Burp Suite REST API Config](#burp-suite-rest-api-config-burprestapiconfig-model)
   - [Upstream Proxy Config](#upstream-proxy-config-upstreamproxyconfig-model)
   - [Specialist Agent Config](#specialist-agent-config-specialistagentconfig-model)
   - [Adversarial Validator Config](#adversarial-validator-config-adversarialvalidatorconfig-model)
   - [Global Extra HTTP Header Config](#global-extra-http-header-config-globalhttpheaderconfig-model)
   - [Reporting Debug Config](#reporting-debug-config-reportingdebugconfig-model)
5. [Data Models](#5-data-models)
   - [Core entities](#core-entities)
   - [`CrawledPage` flags](#crawledpage-flags-set-by-llm-during-crawl)
   - [`ScanFinding` key fields](#scanfinding-key-fields)
6. [Crawling](#6-crawling)
   - [Process](#process) · [LLM involvement](#llm-involvement)
7. [Dynamic Scan](#7-dynamic-scan)
   - [Bootstrap](#bootstrap) · [Scan resume](#scan-resume) · [Agentic loop](#agentic-loop)
   - [Actions available to the LLM](#actions-available-to-the-llm)
   - [Context tools](#context-tools-read-only-reconnaissance) · [Web OWASP Coverage](#web-owasp-coverage-owasp-top-10-matrix)
8. [Multi-Agent System](#8-multi-agent-system)
   - [Agent types](#agent-types) · [Specialist agents](#specialist-agents)
   - [Adversarial validator](#adversarial-validator) · [Post-scan review](#post-scan-review-reporting-agent)
   - [Recon summary](#recon-summary)
9. [LLM Integration](#9-llm-integration)
   - [Agent tool sets](#agent-tool-sets) · [WSTG skills](#wstg-skills) · [Prompt caching](#prompt-caching)
   - [Upstream proxy](#upstream-proxy) · [Rate Limiting & Pacing](#rate-limiting--pacing) · [Token Usage Telemetry](#token-usage-telemetry--telemetry-persistence)
10. [Burp Suite Integration](#10-burp-suite-integration)
    - [Workflow](#workflow) · [Scope pinning](#scope-pinning) · [Per-class routing](#per-class-routing) · [Connection test](#connection-test)
11. [Findings & Validation](#11-findings--validation)
    - [Deduplication](#deduplication) · [Validation](#validation)
12. [API Layer](#12-api-layer)
    - [Key route groups](#key-route-groups)
13. [Frontend & Real-time Events](#13-frontend--real-time-events)
    - [WebSocket event types](#websocket-event-types-emitted-by-serviceseventspy) · [UI tabs](#ui-tabs)
14. [Concurrency & State Management](#14-concurrency--state-management)
15. [A.L.I.C.E. — Interactive Pentesting Chat](#15-alice--interactive-pentesting-chat)
    - [Architecture overview](#architecture-overview) · [Background task registry](#background-task-registry-alice_taskspy)
    - [Reconnect and replay](#reconnect-and-replay) · [Agentic loop](#agentic-loop-alicepy) · [Tools available to ALICE](#tools-available-to-alice)
    - [Chat session persistence](#chat-session-persistence) · [Client-side streaming state](#client-side-streaming-state) · [Stop A.L.I.C.E.](#stop-alice)
16. [API Collections & API Scanning](#16-api-collections--api-scanning)
    - [API Collections](#api-collections) · [Document parsing](#document-parsing-servicesapi_docspy) · [LLM readiness assessment](#llm-readiness-assessment-servicesapi_readinesspy)
    - [OWASP API Top-10 coverage matrix](#owasp-api-top-10-coverage-matrix) · [API scan engine](#api-scan-engine-servicesapi_scannerpy)
    - [Scope enforcement](#scope-enforcement) · [ALICE on API runs](#alice-on-api-runs)
17. [SAST Scanner & Scan Leads](#17-sast-scanner--scan-leads)
    - [Architecture overview](#architecture-overview-1) · [File tools](#file-tools-all-path-jailed-to-the-extraction-root) · [Lead lifecycle](#lead-lifecycle)
    - [ScanLead entity](#scanlead-entity-servicesscan_leadspy) · [Lead consumption (API vs web)](#lead-consumption-api-vs-web) · [Concurrency](#concurrency)

---

## 1. Repository Layout

```
src/aespa/
├── __init__.py            # Package entry point — exports main()
├── main.py                # FastAPI app factory & lifespan handler
├── config.py              # Pydantic settings (host, port, db URL)
├── models.py              # SQLModel ORM table definitions
├── schemas.py             # Pydantic schemas for API I/O
├── db.py                  # Database engine, session factory, migrations
├── api/
│   ├── scan.py            # /api/test-runs/{id}/thinking-scan/* and crawl
│   ├── test_runs.py       # /api/test-runs/* — CRUD, status, site map graph
│   ├── sites.py           # /api/sites/* — target website management
│   ├── settings.py        # /api/settings/* — LLM, policy, Burp, proxy, specialists, headers
│   ├── traffic.py         # /api/traffic/* — HTTP traffic log
│   ├── events.py          # WebSocket event stream
│   ├── alice.py           # /api/test-runs/{id}/alice/* — A.L.I.C.E. chat
│   ├── api_collections.py # /api/api-collections/* — collections, documents, endpoints
│   ├── api_test_runs.py   # /api/api-collections/{id}/test-runs/* — API scan runs
│   ├── sast_runs.py       # /api/sast-runs/* and dynamic-run lead import routes
│   └── reporting_debug.py # /api/reporting-debug/* — reporting-prompt editing & replay
└── services/
    ├── sites.py           # CRUD service layer for Site and Credential
    ├── crawler.py         # LLM-guided parallel web crawl
    ├── scanner.py         # Dynamic agentic scan engine, specialist dispatch, finding dedup
    ├── llm.py             # Multi-provider LLM client, agent tools, rate limiting, token telemetry
    ├── prompts/           # Extracted modular prompt templates
    │   ├── reporting.py   # Reporting / post-scan review prompts
    │   ├── specialist.py  # Specialist agent prompts
    │   ├── test_lead.py   # Test Lead agent prompts
    │   ├── validator.py   # Adversarial validator prompts
    │   ├── alice.py       # A.L.I.C.E. system prompt
    │   └── sast.py        # SAST scanner system prompt and tool schemas
    ├── alice.py           # A.L.I.C.E. agentic loop & tool executor
    ├── alice_tasks.py     # Background task registry — survives client disconnects
    ├── api_collections.py # CRUD service layer for ApiCollection
    ├── api_docs.py        # Document parsing (OpenAPI, Postman, freetext, source ZIP)
    ├── api_documents.py   # Document upload, storage, and doc_type sniffing
    ├── api_readiness.py   # LLM-driven readiness gap analysis for collections
    ├── api_scanner.py     # API scan orchestration — OWASP Top-10 coverage matrix
    ├── burp_rest.py       # Burp Suite Professional REST API client
    ├── checkpoint.py      # Scan resume — persist and restore LLM conversation state
    ├── findings.py        # Finding CRUD operations & validation status management
    ├── recon_summary.py   # Structured attack-surface summary from crawl data
    ├── reporting_debug.py # Reporting-prompt version store & write-up replay harness
    ├── run_cleanup.py     # Scoped database row deletion per run kind
    ├── sast_scanner.py    # SAST agentic loop over uploaded source archives
    ├── scan_completion.py # Completion state policy & bounded stopping logic
    ├── scan_leads.py      # ScanLead CRUD and confidence-threshold filtering
    ├── scanner_sessions.py# Auth session vault (cookies, tokens)
    ├── scope.py           # Scan scope boundaries and out-of-scope filtering
    ├── settings.py        # LLM config / profiles / policy / Burp / proxy / specialist config
    ├── tls_scan.py        # Pure stdlib + cryptography TLS/SSL security posture probe
    ├── traffic.py         # HTTP capture (Playwright intercept + httpx)
    ├── validator.py       # Adversarial validator agent (LLM-assisted finding validation)
    ├── web_route_inventory.py # Web route inventory classification & dynamic enrichment
    ├── web_workprogram.py # Web OWASP Top-10 matrix & per-class obligation tracking
    └── events.py          # WebSocket event emission
```

---

## 2. How to Run

```bash
uv run aespa          # starts the server at http://127.0.0.1:8000
```

Runtime configuration is read from a `.env` file:

```
AESPA_DATABASE_URL = sqlite:///./aespa.db
AESPA_HOST         = 127.0.0.1
AESPA_PORT         = 8000
```

---

## 3. System Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Browser / API client                                       │
│  (Web UI SPA or raw HTTP)                                   │
└─────────────────┬───────────────────────────────────────────┘
                  │  HTTP + WebSocket
┌─────────────────▼───────────────────────────────────────────┐
│  FastAPI application  (src/aespa/main.py)                   │
│  Routers: sites · settings · test_runs · scan · alice       │
│           traffic · events · api_collections                │
│           api_test_runs · sast_runs · reporting_debug       │
└──────┬───────────────────────┬──────────────────────────────┘
       │                       │
       ▼                       ▼
┌─────────────┐       ┌─────────────────────────────────────┐
│  Services   │       │  LLM Provider                       │
│  ─────────  │       │  (Copilot / Anthropic / OpenAI /    │
│  crawler    │◄──────│   Google / Bedrock / Azure / etc.)  │
│  scanner    │       └─────────────────────────────────────┘
│  findings   │
│  validator  │       ┌─────────────────────────────────────┐
│  recon      │       │  Burp Suite Professional            │
│  burp_rest  │──────►│  REST API  (default :1337)          │
│  traffic    │       └─────────────────────────────────────┘
│  events     │
└──────┬──────┘
       │                  (optional upstream proxy)
       ▼
┌─────────────────────────────────────────────────────────────┐
│  SQLite database  (aespa.db — via SQLModel / SQLAlchemy)    │
│  Sites · Credentials · TestRuns · CrawledPages · PageLinks  │
│  TrafficEntries · ScanFindings · ScannerSessions            │
│  TargetIntelItems · PageOwaspTests · ScanCheckpoints        │
│  ScanLogs · AliceChatSessions · AliceChatMessages           │
│  BurpRestApiConfig · UpstreamProxyConfig                    │
│  ApiCollections · ApiDocuments · ApiEndpoints               │
│  ApiCredentials · ApiTestRuns · ApiEndpointTests            │
│  SastRuns · ScanLeads                                       │
└─────────────────────────────────────────────────────────────┘
```

A **test run** is the central unit of work. It ties together a target site, its credentials, the LLM config, the scanner policy, and all results (crawled pages, traffic, findings, hypotheses). A run progresses through phases: `created → crawling → crawled → scanning → scanned` (plus `thinking_scanning`).

---

## 4. Configuration

### LLM Configuration (`LLMProviderConfig`, `LLMConfig`, & `LLMProfile` models)

LLM settings are structured into three entities to separate reusable provider connections, execution profiles, and role-based model routing:

#### 1. Reusable Provider Config (`LLMProviderConfig` model)

Defines API connections, optional project identifiers, and rate limits for LLM backends:

| Field | Default | Description |
|---|---|---|
| `name` | `Default Provider` | Label for the provider |
| `api_format` | `anthropic` | API format: `github_copilot`, `anthropic`, `openai`, `openai_compatible`, `openrouter`, `google`, `bedrock`, `bedrock_mantle`, `azure_openai`, `azure_foundry`, `azure_foundry_openai`, `azure_foundry_anthropic` |
| `api_key` | — | Provider API key (stored in DB; masked and excluded from non-localhost exports) |
| `base_url` | — | Override endpoint URL |
| `username` | — | Optional Copilot CLI account login; blank uses Copilot CLI's selected default account |
| `project_id` | — | Bedrock Mantle project ID (sent as `OpenAI-Project` header for cost/usage attribution) |
| `models_json` | `[]` | JSON list of available model names for this provider |
| `max_tpm` | — | Optional Token-Per-Minute rate limit for this provider |
| `max_rpm` | — | Optional Request-Per-Minute rate limit for this provider |

#### 2. Saved LLM Profile (`LLMConfig` model)

Defines execution parameters linked to a provider:

| Field | Default | Description |
|---|---|---|
| `name` | `Default` | Profile name label |
| `is_active` | `false` | Global active switch (only one profile active globally) |
| `provider_id` | — | Foreign key linking to the `LLMProviderConfig` connection |
| `model` | `claude-opus-4-5` | Specific model identifier to run |
| `max_tokens` | `70000` | Max tokens per LLM call |
| `temperature` | — | Unset by default (falls through to provider/model default) |
| `use_vision` | `false` | Include Playwright screenshots in prompts |
| `force_tool_choice` | `false` | Force tool selection via wire-format `tool_choice: required/any` |

#### 3. Multi-Role Model Profile (`LLMProfile` model)

Maps agent roles (`crawler`, `test_lead`, `mentor`, `specialist`, `validator`, `reporting`, `alice`, `sast`) to specific `LLMConfig` instances. An unassigned `mentor` inherits the `test_lead` model before falling back to the profile default:

| Field | Default | Description |
|---|---|---|
| `name` | `Default` | Profile name label |
| `is_active` | `false` | Global active switch |
| `default_model_id` | — | Foreign key linking to the default fallback `LLMConfig` |
| `role_models_json` | `{}` | JSON dictionary mapping role strings to specific `LLMConfig` IDs |

Runs (`TestRun`, `ApiTestRun`, `SastRun`) can override model routing via an `llm_profile_id` reference. Roles resolve their configuration via `get_llm_config_for_role(role, run_profile_id)`.

### Scanner Policy (`ScannerPolicy` model)

| Field | Default | Description |
|---|---|---|
| `execution_monitor_enabled` | `false` | Enable duplicate-action and stalled-progress supervision by the Mentor |
| `disable_deterministic_checks` | `false` | Skip automatic JavaScript sink, TLS, authentication, IDOR, and probe-result checks |
| `max_consecutive_text_turns` | `0` | Stop after this many text-only Test Lead turns; `0` allows unlimited turns |
| `enforce_full_coverage_obligations` | `false` | Require every coverage obligation to be resolved before the Test Lead can finish |
| `scan_mode` | `safe_active` | `passive` (GET/HEAD only) · `safe_active` (+ POST) · `aggressive` (all methods) · `destructive` |
| `max_probes_per_page` | `50` | Cap on probe attempts per crawled page |
| `thinking_max_steps` | `120` | Legacy compatibility setting; the active Test Lead loop is deliberately uncapped and does not read this value |
| `request_timeout` | `10` | HTTP timeout per probe (seconds) |
| `min_delay` | `0.05` | Minimum delay between probes (rate-limiting) |
| `max_request_body` | `65536` | Probe body size cap (bytes) |
| `follow_redirects` | `true` | |
| `allow_subdomains` | `true` | Allow crawling/probing subdomains of the target |

### Burp Suite REST API Config (`BurpRestApiConfig` model)

Singleton row (id = 1). Configures the optional Burp Suite Professional active-scan integration.

| Field | Default | Description |
|---|---|---|
| `enabled` | `false` | Enable Burp integration |
| `api_url` | `http://127.0.0.1:1337` | Burp REST API base URL |
| `api_key` | — | Bearer token for the Burp REST API (optional) |
| `scan_configuration_name` | `Audit checks - all except time-based detection methods` | Named Burp scan config to apply |
| `scan_sqli` | `true` | Route SQLi findings to Burp active scan |
| `scan_xss` | `true` | Route XSS findings to Burp active scan |
| `scan_command_injection` | `true` | Route command injection findings |
| `scan_path_traversal` | `true` | Route path traversal findings |
| `scan_ssrf` | `true` | Route SSRF findings |
| `scan_xxe` | `true` | Route XXE findings |
| `scan_ssti` | `true` | Route SSTI findings |

### Upstream Proxy Config (`UpstreamProxyConfig` model)

Singleton row (id = 1). Routes scanner and/or LLM traffic through an upstream HTTP proxy.

| Field | Default | Description |
|---|---|---|
| `proxy_url` | — | `http://host:port` proxy URL |
| `proxy_scanner` | `false` | Route scanner HTTP and Playwright traffic through proxy |
| `proxy_llm` | `false` | Route LLM API calls through proxy |

### Specialist Agent Config (`SpecialistAgentConfig` model)

Singleton row (id = 1). Controls when and how Specialist Agents are dispatched during a dynamic scan.

| Field | Default | Description |
|---|---|---|
| `enabled` | `true` | Master switch — disable to suppress all specialist dispatch |
| `max_concurrent` | `5` | Maximum simultaneously-running specialists per scan |
| `max_steps` | `30` | Step budget per specialist agent |
| `min_priority` | `7` | Minimum recon-summary `attack_class` priority to trigger dispatch |
| `dispatch_idor` | `true` | Dispatch specialists for IDOR leads |
| `dispatch_auth_bypass` | `true` | Dispatch specialists for auth bypass leads |
| `dispatch_sqli` | `true` | Dispatch specialists for SQLi leads |
| `dispatch_xss` | `true` | Dispatch specialists for XSS leads |
| `dispatch_business_logic` | `true` | Dispatch specialists for business logic leads |
| `dispatch_ssrf` | `true` | Dispatch specialists for SSRF leads |
| `dispatch_path_traversal` | `true` | Dispatch specialists for path traversal leads |
| `dispatch_cors` | `false` | Dispatch specialists for CORS leads |
| `dispatch_crypto` | `true` | Dispatch specialists for cryptography/secrets leads |
| `dispatch_config` | `false` | Dispatch specialists for misconfiguration leads |
| `dispatch_file_upload` | `true` | Dispatch specialists for file upload leads |
| `trigger_specialist_on_burp` | `false` | Also dispatch a specialist alongside each Burp active scan |

### Adversarial Validator Config (`AdversarialValidatorConfig` model)

Singleton row (id = 1). Controls the adversarial validation agent that attempts to disprove each finding.

| Field | Default | Description |
|---|---|---|
| `enabled` | `true` | Use adversarial agent mode; `false` falls back to legacy static-probe validation |
| `max_steps` | `20` | Step budget per validation pass |
| `min_severity` | `low` | Skip validation for findings below this severity (`critical`\|`high`\|`medium`\|`low`\|`info`) |
| `end_scan_max_concurrent` | `4` | Maximum simultaneous validators for end-of-scan batch review |
| `auto_validate_inline` | `true` | Automatically validate each finding immediately after it is written |
| `require_concrete_disproof` | `true` | Strict mode — only return `false_positive` when concrete innocent explanation is found |

### Global Extra HTTP Header Config (`GlobalHttpHeaderConfig` model)

Singleton row (id = 1). Configures custom HTTP headers appended to all outbound scanner and crawler HTTP requests:

| Field | Default | Description |
|---|---|---|
| `headers` | `[]` | List of header name and value pairs; header names are case-insensitively unique |

### Reporting Debug Config (`ReportingDebugConfig` model)

Singleton row (id = 1). Configures reporting prompt debug capture and replay:

| Field | Default | Description |
|---|---|---|
| `capture_enabled` | `false` | Persist reporting prompt executions for debug inspection |
| `panel_enabled` | `false` | Expose the reporting debug UI panel |
| `batch_max_concurrent` | `4` | Maximum concurrent LLM workers during post-scan reporting review |

### Cloudflare Access Config (`CloudflareAccessConfig` model)

Singleton row (id = 1). Holds the optional Cloudflare Access application **audience (AUD)** tag used when verifying the proxy-injected `Cf-Access-Jwt-Assertion` header.

| Field | Default | Description |
|---|---|---|
| `audience` | `null` | Access application AUD tag. When set, the JWT is verified against it (`jwt.decode(..., audience=...)`). When null, audience checking is skipped. |

---

## 5. Data Models

All models are defined in `src/aespa/models.py` using **SQLModel** (SQLAlchemy + Pydantic).

### Core entities

| Model | Purpose |
|---|---|
| `Site` | Target website (base URL, auth settings, associated credentials) |
| `Credential` | Login credentials tied to a site (username, password, login URL) |
| `LLMProviderConfig` | Reusable LLM provider connection settings (API keys, base URLs, rate limits, project IDs) |
| `LLMConfig` | Saved LLM configuration/execution profile linked to a provider |
| `LLMProfile` | Named per-agent-role model routing profile mapping roles to specific `LLMConfig` IDs |
| `ScannerPolicy` | Scan behaviour policy for a test run |
| `BurpRestApiConfig` | Singleton — Burp Suite REST API connection and routing settings |
| `UpstreamProxyConfig` | Singleton — upstream HTTP proxy settings for scanner and LLM traffic |
| `GlobalHttpHeaderConfig` | Singleton — custom HTTP header added to all scanner and crawler requests |
| `ReportingDebugConfig` | Singleton — reporting prompt execution capture and debug settings |
| `CloudflareAccessConfig` | Singleton — optional Access AUD tag for verifying the proxy-injected JWT |
| `TestRun` | A single web scan session; owns all scan artefacts and stores token telemetry in `token_usage_json` |
| `CrawledPage` | A discovered page/endpoint with LLM-assigned flags |
| `PageLink` | Directed edge between two `CrawledPage` nodes (site map graph) |
| `TrafficEntry` | A captured HTTP request/response pair |
| `ScanFinding` | A discovered vulnerability with evidence and CVSS score (shared by web and API scans) |
| `ScannerSession` | Reusable auth material (cookies, JWT, metadata) |
| `TargetIntelItem` | Normalised reconnaissance atom (endpoint, form, input, ID, script, xss_sink) |
| `PageOwaspTest` | One cell in the web OWASP Coverage matrix (`TestRun` × `CrawledPage` × OWASP category, status, finding IDs, per-vulnerability-class coverage in `test_classes_json`) |
| `ScanLog` | Audit event emitted during crawl/scan phases |
| `AliceChatSession` | One ALICE chat tab per test run (title, ordering, active flag) |
| `AliceChatMessage` | One chat bubble inside an `AliceChatSession` (sender, type, text) |
| `ApiCollection` | A named REST API target (base URL, scope hosts, auth summary, readiness JSON) |
| `ApiDocument` | Uploaded API spec or source file (`doc_type`: openapi, postman, credentials, freetext, source_zip) |
| `ApiEndpoint` | A parsed endpoint row (method, path, parameters, request/response schema, scope flag) |
| `ApiCredential` | A parsed credential row tied to a collection (scheme, label, auth endpoint) |
| `ApiTestRun` | A single API scan session; linked to an `ApiCollection`; carries `coverage_mode` and `sast_run_id` |
| `ApiEndpointTest` | One cell in the OWASP API Top-10 coverage matrix (endpoint × category, status, finding IDs) |
| `SastRun` | A standalone static-analysis scan over a source ZIP; tracks `leads_count` and carries its archive via `source_archive_path` / `source_filename`. Legacy collection linkage fields remain nullable for compatibility. |
| `ScanLead` | A high-confidence SAST lead. Keyed to its producing `SastRun` (`producer_run_id`). An *original* lead leaves `imported_into_run_id` NULL; a *copy* imported into a dynamic run sets `imported_into_run_type`/`imported_into_run_id` to that run. Web and API scans both consume independent run-owned copies. |

### `CrawledPage` flags (set by LLM during crawl)

| Flag | Meaning |
|---|---|
| `req_auth` | Page requires authentication |
| `takes_input` | Has forms or query parameters |
| `has_object_ref` | References object IDs / UUIDs (IDOR candidate) |
| `has_business_logic` | Core application functionality |

### `ScanFinding` key fields

| Field | Notes |
|---|---|
| `owasp_category` | `A01`–`A10` (OWASP Top 10) |
| `severity` | `critical` · `high` · `medium` · `low` · `info` |
| `cvss_score` | 0.0–10.0 |
| `cvss_vector` | CVSS 3.1 string |
| `affected_url` | Specific URL where the issue was found |
| `evidence_json` | Structured request/response pairs |
| `screenshot_b64` | Base64 PNG (form-based probes) |
| `finding_source` | Origin of the finding: `aespa_scanner` · `burp_active_scan` · `deterministic_probe` · `sast_lead` (auto-promoted from a confirmed `ScanLead`) · `manual_import` · `unknown` |
| `validation_status` | `unvalidated` · `validating` · `confirmed` · `unconfirmed` · `false_positive` · `low_confidence` |

---

## 6. Crawling

**File**: `src/aespa/services/crawler.py`  
**Entry point**: `async start_crawl(run_id)`

The crawler performs a **multi-phase, multi-user, LLM-guided BFS** across the target site using Playwright browser instances.

### Process

```
start_crawl(run_id)
  └─ _do_crawl(run_id)
       1. Load site config, credentials, and upstream proxy settings
       2. Build crawl phases:
            • Phase 0 — always unauthenticated (even if credentials exist)
            • Phase 1..N — one phase per stored Credential
       └─ Per phase:
            a. Authenticate via Playwright (or skip for unauthenticated phase)
            b. Export auth cookies → ScannerSession
            c. Spawn N parallel browser workers (_CrawlShared state)
            └─ Per worker, BFS loop:
                 i.   Load page in Playwright, intercept network traffic
                 ii.  Extract page text, links, forms, inputs
                 iii. Send page content to LLM → analyse flags (req_auth, takes_input, etc.)
                 iv.  Ask LLM "where next?" → ranked link suggestions
                 v.   Enqueue new URLs (in-scope, within depth/page limits)
                 vi.  Persist CrawledPage + PageLinks + TrafficEntries
       3. Extract TargetIntelItems (endpoints, forms, inputs, IDs, scripts, JWT hints)
       4. Update TestRun status → crawled
```

The unauthenticated phase is always run first so the crawler maps the public attack surface before logging in. When a dynamic scan discovers valid credentials, they are persisted to the site's credential store and a `credential_discovered` event is emitted, prompting the user to re-crawl with the new account.

**`max_pages` caps the total site-map size.** All phases run concurrently and share `_CrawlShared` (the `crawled_norms` dedup map + a `pages_done` counter, guarded by an `asyncio.Lock`). New nodes — both HTML pages and promoted API endpoints — are only created while `pages_done < max_pages`, so the number of distinct `CrawledPage` nodes in the site map never exceeds `max_pages` regardless of how many credential phases run. Already-discovered URLs still fall through the cap so every phase records its own access view of them (this is the differential broken-access-control signal); they don't create new nodes.

### LLM involvement

The crawler sends each page's content to the LLM twice:
- **Analysis prompt**: Classify the page (flags above) and extract intelligence atoms.
- **Navigation prompt**: Suggest which links are most interesting to follow next (prioritising high-value pages like login forms, API endpoints, admin areas).

Scope enforcement prevents crawling outside the target domain (configurable via `allow_subdomains`).

### Authentication

`_authenticate` dispatches per `Credential.auth_mode`:

- **`auto`** / **`totp`** — `_authenticate_auto` does a fast deterministic form
  fill. Credentials can contain any number of named login fields, such as
  Policy Number and Postcode. AESPA matches them using labels and input
  attributes, or an optional CSS selector. Older credentials with only the
  `username` and `password` columns are automatically presented as Username and
  Password fields. TOTP additionally fills a 2FA code from the stored seed.
- **`entra_id`** — `_authenticate_entra_id` follows Microsoft Entra's multi-page
  browser flow. It handles account pickers, username/password pages, consent,
  stay-signed-in prompts, Authenticator notification approval, and TOTP code
  entry when a seed is configured. Number-matching prompts and terminal status
  are emitted to the run UI; retryable Authenticator failures wait for an
  operator retry request. Successful cookies/storage are persisted as an Entra
  `ScannerSession` with MFA metadata.
- **`guided`** — `_authenticate_guided` opens a headed browser so the user logs
  in by hand; cookies/storage are captured and injected into the headless crawl
  contexts.

Entra and guided modes use the run-scoped interactive-auth coordinator. A
credential's first successful interactive login is cached so concurrent crawl
workers and later scan phases reuse the captured state instead of opening
competing browser/MFA flows. The API exposes an Entra retry action, while
`entra_authenticator_prompt` and `entra_authenticator_status` events keep the run
view synchronized with number matching, success, timeout, and retry-required
states.

**LLM-driven adaptive fallback.** When the deterministic `auto`/`totp` attempt
fails to clear the login form (`_page_requires_login` still true) and the run has
an LLM profile, `_authenticate_smart` takes over: it builds a text observation of
the page (forms/fields via `_extract_dom_intelligence` plus visible clickable
controls; a screenshot too when the profile has `use_vision`) and runs a bounded
agentic loop (≤6 steps) calling `llm.decide_login_action` for one action at a time
(fill/click/press/done/give_up), re-checking for success after each. This handles
modal/no-route logins, non-standard field labels, and multi-step flows that the
selector heuristics miss. Credential values are kept out of this LLM call: the
model returns named placeholders such as `{{credential.policy_number}}` and the
crawler substitutes the real values locally.

---

## 7. Dynamic Scan

**File**: `src/aespa/services/scanner.py`  
**Entry point**: `async start_thinking_scan(run_id)`

The dynamic scan is an **autonomous agentic loop**: the LLM is given a toolkit and decides each action itself, building on prior observations. This allows it to chain multi-step attacks that the structured scan cannot discover.

### Bootstrap

```
start_thinking_scan(run_id)
  └─ _do_thinking_scan(run_id)
       1. Load crawl data, prior findings, TargetIntelItems
       2. Unless deterministic checks are disabled, run JS sink analysis (_analyse_js_sinks) — fetches each
          discovered JS file (TargetIntelItem kind=script), regex-scans
          for unsanitized innerHTML/outerHTML/document.write sinks,
          saves TargetIntelItem(kind=xss_sink) and info-severity findings
       3. Authenticate → ScannerSession
       4. Build attack-surface projection (_build_thinking_context_from_recon_summary)
          — canonical routes, real parameters, access observations, evidence
          signals, and current PageOwaspTest coverage; stored on TestRun.recon_summary
       5. Build a compact LLM brief from actionable routes and coverage gaps
       6. Detect auth cookies for boundary checks
       7. Restore checkpoint if this is a resumed scan
       8. Unless deterministic checks are disabled, _run_deterministic_site_modules(...) — LLM-free probes
          (TLS/SSL posture, auth matrix, IDOR matrix)
       └─ _do_agentic_thinking_loop(...)   ← main loop
```

**TLS/SSL posture (deterministic).** Unless deterministic checks are disabled, any
`https://` target runs `_run_tls_posture_module` first through
`_run_deterministic_site_modules` — an
sslscan-like probe (`services/tls_scan.py`, pure stdlib `ssl` + `cryptography`)
that enumerates accepted protocol versions (TLS 1.0–1.3; SSLv2/SSLv3 report as
`not-testable`), weak / non-forward-secret cipher acceptance, and leaf-certificate
weaknesses (expiry, key size, signature algorithm, SANs, self-signed, hostname
match). When enabled, it runs on every HTTPS scan (including `passive` mode, since the
handshake is non-intrusive) and records **at most one** consolidated
`A02 · TLS/SSL configuration weaknesses` finding summarising every issue; overall
severity is the worst per-issue tier (`_tls_worst_cvss`). Dedup by title +
`affected_url` keeps it to a single finding across resumes. This is deliberately
**not** a Test Lead tool — the same `tls_scan` schema (`TLS_SCAN_TOOL`) is exposed
only to A.L.I.C.E. for interactive inspection, so the automated scan cannot raise
a second, competing TLS finding. The **API scanner** runs the same module before
its agentic loop for any `https://` collection base URL (`is_api_run=True`, keyed
on `api_test_run_id`, categorised `API8 · Security Misconfiguration`).

**Deterministic authorization identity rules.** Role and IDOR matrices only use
sessions bound to current configured credential IDs. Tokens recovered from an
arbitrary HTTP response have unknown role provenance and are excluded until they
are bound to an identity. Role probes also require a positive authorized crawl
baseline for the target. Per-page access combines current `PageCredentialView`
rows with `CrawledPage.accessible_by`; imported credential IDs are remapped, and
stale IDs from older imports are ignored. An anonymous result is eligible only
when the request actually sent neither cookies nor an Authorization header.

### Scan resume

The checkpoint service (`services/checkpoint.py`) serialises the LLM conversation history to the database at regular intervals. If a scan is interrupted (server restart, user stop) it can be resumed with `start_thinking_scan_resume(run_id)`, which restores the conversation at the last saved checkpoint rather than starting over.

### Agentic loop

Two execution modes depending on the configured LLM provider:

| Mode | Providers | Description |
|---|---|---|
| **Native tool-use** | Any provider in `llm.AGENTIC_LOOP_PROVIDERS` (currently every supported provider) | The provider returns native tool calls and AESPA preserves the conversation between turns. |
| **Step-by-step** | DEPRECATED — dormant fallback for providers outside `AGENTIC_LOOP_PROVIDERS` | Each iteration sends the full conversation history; the LLM emits a JSON action; the harness executes it and appends the result. |

The loop terminates when:
- The LLM calls the `done` action (with a summary)
- A stop is requested via the API
- An unrecoverable network error occurs
- The bounded completion policy observes 50 consecutive tool calls without a new
  route/category coverage transition, finding, lead resolution, specialist handoff,
  or session use. It warns after 40 and records the automatic stop in the Test Lead log.
- The Execution Monitor reaches a bounded rejection limit after the Test Lead keeps
  retrying a hard-blocked duplicate or refuses an active Mentor Strategy Shift Contract.

The Execution Monitor is disabled by default and can be enabled in the Scanner settings.
When enabled, `execution_monitor.py` fingerprints meaningful tool inputs while removing
known transport noise. A second consecutive normalized duplicate invokes the run-scoped
Mentor; a third is blocked. Intentional bounded repetition tests are treated differently:
rate-limit, lockout, credential-stuffing, password-spraying, and OTP-guessing probes can
declare a `repeat_sequence` and `repeat_limit` of up to 20 requests. The standard login
rate-limit check permits six identical requests before either duplicate guard intervenes.
Eight completed steps without a persisted progress signal invoke the Mentor and establish
a structured Strategy Shift Contract containing two or three route/category/class vectors.
Calls that match none of those constraints are rejected unless they carry an explicit
`strategy_pivot_justification`. Executed and rejected steps share the same completion
accounting, so supervision cannot itself form an unbounded rejection loop. Monitor and
contract state are stored in scan checkpoints.
Persisted activity entries use explicit emitter tags: `Execution Monitor` records every
Mentor trigger, hard block, and contract rejection; `Mentor Guidance` records the full
diagnosis, structured alternate vectors, and tactical next step; invalid-session
checks and evictions are tagged `Session Validator`; completion challenges are tagged
`Test Lead Completion Gate` rather than the generic `Completion_Policy`.

`done` is mediated by a bounded policy rather than an open-ended completeness gate.
An active session that has never been attempted may trigger one challenge, and Track
mode may trigger at most two compact live coverage rounds. A 401/403 counts as a
session attempt and evicts that session. The same completion condition can therefore
never reject `done` indefinitely.

### Actions available to the LLM

| Action | Description |
|---|---|
| `http` | Issue an arbitrary HTTP request (method, URL, headers, body) |
| `browser` | Playwright commands: `goto`, `fill`, `click`, `wait`, `snapshot` |
| `jwt` | Forge a signed HS256 JWT from a discovered secret |
| `decode_jwt` | Decode a JWT's header and payload; optionally verify the HS256 signature against a known secret |
| `credential_check` | Test a login URL with candidate credentials |
| `finding_write` | Record a confirmed vulnerability |
| `update_lead` | Record the outcome (`confirmed`/`dismissed`/`inconclusive`) of investigating a SAST lead; a confirmed lead with no linked finding is auto-promoted to one. Present only when SAST leads are in context (see §17) |
| `agent_dispatch` | Dispatch a Specialist Agent to deep-dive on a high-confidence lead (see §8) |
| `tool` | Call a read-only context tool (see below) |
| `done` | Finish the scan with a summary |

### Context tools (read-only reconnaissance)

These use an adaptive checkpoint. After 3 consecutive context calls, the LLM should
take a real action. If more context is genuinely needed, it can continue by including
`context_budget_reason` with a short summary, current hypothesis, and why another
targeted scan round will change the next action.

| Tool | Returns |
|---|---|
| `site_map` | Filtered list of crawled pages |
| `page_detail` | Full metadata, flags, text for a page |
| `history_search` | Query prior HTTP requests/responses by keyword |
| `finding_list` | Already-confirmed findings |
| `target_inventory` | Extracted endpoints, forms, inputs, IDs, scripts, and pre-identified `xss_sink` items (unsanitized innerHTML sinks found by static JS analysis) |
| `traffic_search` | Search the HTTP traffic log |
| `endpoint_detail` | Combined page + intel + traffic for a URL |
| `compare_responses` | Diff two prior responses |
| `mutate_request` | Generate probe variants (input_validation, idor, business_logic) |
| `auth_matrix` | Test a set of endpoints across auth boundaries |
| `extract_entities` | Parse URLs, IDs, JWTs, error strings from text |
| `coverage_gaps` | Compact live list of high-value uncovered web route/category cells |

### Web OWASP Coverage (OWASP Top-10 matrix)

**File**: `src/aespa/services/web_workprogram.py`

The web scan tracks OWASP Top-10 coverage in a per-page matrix — the web analogue of the API coverage matrix (§16). Each cell is a `PageOwaspTest` row: a `(TestRun, CrawledPage, OWASP category A01–A10)` triple with status `not_started → in_progress → covered / finding / skipped`.

Input-bearing A03 cells additionally persist class-level states in `test_classes_json`. SQLi, reflected XSS, and stored XSS are separate obligations: an HTTP probe must declare `test_class`, and exercising one class does not satisfy the others. The browser tool's constrained `dom_check` operation can compare an element's text or attribute to an exact expected canary and records an explicit PASS/FAIL without allowing arbitrary JavaScript execution.

- `seed_web_workprogram(run_id)` creates the cells; it runs synchronously when a dynamic scan starts (and on resume) via `api/scan.py`, and can be re-triggered through `POST /api/test-runs/{id}/coverage/seed`.
- `_make_web_post_probe_fn` / `_make_web_post_finding_fn` update cells as the agentic loop probes pages and writes findings (findings flip the cell to `finding` and record the `ScanFinding.id`).
- `web_route_inventory.enrich_dynamic_route` classifies routes first observed during the dynamic scan from their request/response evidence. It OR-merges deterministic and LLM-derived applicability into the canonical `CrawledPage`, reseeds newly applicable cells, and leaves the current probe hook to mark the exercised category `in_progress`. Browser-observed routes are enriched too; passive JavaScript route literals remain target intelligence until actively reached.
- `TestRun.coverage_mode` selects **Track** (observe only) or **Enforce**; in Enforce mode `_enforce_web_coverage_loop` drives every still-uncovered cell to a terminal state after the main loop, classifying each `(page, category)` as probe-worthy or skippable up to a budget.
- `get_web_coverage_matrix(run_id)` powers the **OWASP Coverage** UI tab (`GET /api/test-runs/{id}/coverage`).

---

## 8. Multi-Agent System

**File**: `src/aespa/services/scanner.py`, `src/aespa/services/validator.py`

Every agent type — Test Lead, Specialist, Burp, Validator, Reporting — emits `agent_status` SSE events and appears as a row in the **Agents** panel in the UI.

### Agent types

```
Dynamic scan
  └── Test Lead agent  (scanner.py — single continuous session, full context)
        │
        ├── On high-confidence lead ──→  Specialist Agent
        │                                (narrow scope, focused mission,
        │                                 runs concurrently via asyncio.Task,
        │                                 cannot dispatch further specialists)
        │
        └── On finding written ────────→  Adversarial Validator Agent
                                           (mandate to disprove the finding;
                                            different system prompt;
                                            cannot create new findings)

A.L.I.C.E. (Interactive chat — user-directed, runs as persistent background task)
  └── Can dispatch Specialist Agents via agent_dispatch tool
  └── Can write findings directly via write_finding tool

Burp active scans  (dispatched from scanner, surfaced in Agents panel)
Reporting agent    (post-scan LLM pre-screen pass over new findings)
```

### Specialist agents

The Test Lead calls `agent_dispatch` when it has a strong, specific lead it wants to pursue concurrently (e.g. a suspected IDOR on a particular endpoint). The scanner dispatches `_run_specialist_agent` as a background `asyncio.Task`.

**Dispatch flow:**

```
Test Lead calls agent_dispatch
  └─ _should_dispatch_specialist(attack_class, priority, config)
       • checks SpecialistAgentConfig (enabled, min_priority, per-class toggles)
       • checks _specialist_at_capacity(run_id)  ← max_concurrent gate
  └─ _run_specialist_agent(
         agent_id, attack_class, target_url, rationale,
         session_vault, llm_cfg, max_steps
     )
       1. Build opening brief from the explicit dispatch payload
       2. Run focused agentic loop using SPECIALIST_AGENT_TOOLS
          (no agent_dispatch — no recursive dispatch; no JWT/register tools)
       3. Write findings directly to DB under the same run_id
       4. Emit specialist_step + agent_status events throughout
```

Specialists can also be triggered alongside Burp active scans via the `trigger_specialist_on_burp` config flag.

**`SpecialistAgentConfig` fields:**

See [§4 Configuration](#4-configuration) for the full `SpecialistAgentConfig` field reference.

### Adversarial validator

After any finding is written, the validator service (`validator.py`) can run an independent **adversarial validation** pass. The validator agent is given a different system prompt with an explicit mandate to disprove the finding — it re-runs the probe and looks for counter-evidence. This reduces false positives more effectively than self-review by the same agent.

Validation outcomes:
- **confirmed** — vulnerability is reproducible and real
- **unconfirmed** — could not be reproduced
- **false_positive** — validator determines finding was incorrect
- **low_confidence** — post-scan pre-screen flagged the finding as likely noise

### Post-scan review (Reporting agent)

After the dynamic scan loop ends, a final **Reporting agent** pass (`_run_post_scan_llm_review`) reviews all `unvalidated` findings created in the current run in batches of 10. Findings where the evidence is too vague, the payload is reflected as plain text without execution, or the response status contradicts the claim are moved to `low_confidence`. This is a lightweight pre-screen; per-finding adversarial validation runs separately.

### Recon summary

`recon_summary.build_recon_summary(run_id)` generates a structured attack-surface projection from canonical crawl, intelligence, access-view, traffic-header, and workprogram rows. It is stored on `TestRun.recon_summary` at scan startup and rebuilt without persistence whenever the UI polls, so live coverage and dynamically discovered routes are reflected.

1. **LLM opening context** — the Test Lead receives a small sample of concrete routes plus the largest real workprogram gaps. The summary is explicitly not a second scan plan or risk ranking.
2. **Attack Surface & Coverage UI panel** — renders the full route/input inventory, access evidence, live coverage, provenance, and evidence-backed signals.

Specialists use their explicit dispatch target and rationale. They do not consume the UI projection or inherit synthetic attack-class priorities.

The `ReconSummary` schema:

```json
{
  "schema_version": 2,
  "routes": [
    {
      "canonical_url": "https://target/api/accounts/{id}",
      "example_urls": ["https://target/api/accounts/42"],
      "methods": ["GET", "POST"],
      "parameters": ["account_id"],
      "sources": ["api_observation", "public_asset"],
      "source_urls": ["https://target/assets/api.js"],
      "access": {"classification": "authenticated", "labels": ["Customer"]},
      "coverage": {"statuses": {"not_started": 2}, "remaining_categories": ["A01", "A03"]}
    }
  ],
  "input_surface": {"routes": 12, "parameters": 38, "forms": 4},
  "access": {"counts": {"anonymous": 8, "authenticated": 14, "mixed": 2, "unknown": 3}},
  "coverage": {"total": 120, "resolved": 48, "statuses": {}, "by_category": []},
  "signals": {"total": 9, "shown": 9, "items": []},
  "technologies": [{"name": "Apache", "source": "response headers"}]
}
```

---

## 9. LLM Integration

**File**: `src/aespa/services/llm.py`

The LLM service provides a **provider-agnostic client** that maps onto:

| Provider | SDK used |
|---|---|
| `github_copilot` | Official GitHub Copilot SDK, using Copilot CLI authentication or a GitHub user token |
| `anthropic` | `anthropic` Python SDK (native tool-use supported) |
| `openai` | `openai` Python SDK |
| `google` | `google-generativeai` |
| `bedrock` | `boto3` / `anthropic` Bedrock adapter |
| `bedrock_mantle` | `openai` SDK with Bedrock Mantle endpoint (`project_id` sent as `OpenAI-Project` header) |
| `azure_openai` | `openai` SDK with Azure base URL |
| `openai_compatible` | `openai` SDK with custom base URL |
| `openrouter` | `openai` SDK with OpenRouter base URL |

When both the provider token and username are blank, the GitHub Copilot SDK reads Copilot CLI's real home directory and uses the account selected there. A configured username resolves that account's stored Copilot CLI credential, while an explicit provider token takes precedence over both choices. Named-account and explicit-token sessions get a temporary Copilot home. Every path keeps scans isolated: they use a temporary working directory, remove Copilot's repository environment from the prompt, disable instructions, skills, memory, hooks, embeddings, telemetry, host Git operations, and session storage, and expose only the custom tools AESPA explicitly registers. One Copilot session stays alive for the full AESPA agent conversation, allowing the provider to reuse conversation state and prompt caches. When Copilot requests a tool, its SDK handler pauses while AESPA applies the existing scope checks, execution monitoring, checkpointing, and tool-result limits. AESPA returns the real result to that handler and the same Copilot session continues.

Copilot usage events arrive through the SDK's background JSON-RPC callback, so each callback is bound explicitly to the AESPA run that created the session. AESPA records AI credits, model-call counts, token/cache details, and legacy premium requests when GitHub supplies them. The latest available Copilot allowance percentage and reset date are also included in the run telemetry. AESPA waits briefly for the ephemeral usage event before returning or closing a model turn so final-call usage is not lost.

Structured outputs such as probe lists, finding objects, and page analysis are requested as JSON or produced through tool calls. AESPA does not parse free-form model text with regular expressions.

### Agent tool sets

Different agent roles receive different tool sets:

- **Test Lead** — full tool set including `agent_dispatch`, `jwt`, `credential_check`, `browser`, `http`, all context tools
- **Specialist** — `SPECIALIST_AGENT_TOOLS`: `http`, `browser`, context tools; no `agent_dispatch` (prevents recursive dispatch), no JWT/credential/register tools (specialist is narrowly focused)
- **Adversarial validator** — purpose-built prompt and tool set focused on re-running and disproving a specific finding

### WSTG skills

The LLM service dynamically selects a subset of OWASP Web Security Testing Guide (WSTG) technique descriptions relevant to the target's attack surface and injects them into the Test Lead's system prompt. This gives the scanner domain-specific testing guidance without overloading the context with irrelevant techniques.

Vision support (when `enable_vision=true`) attaches base64-encoded Playwright screenshots to prompts, giving the LLM visual context about what a page looks like.

### Prompt caching

The LLM service uses Anthropic prompt caching for large, repeated context blocks (crawl summaries, system prompts). This significantly reduces token usage on multi-step dynamic scans where the same context is sent across many loop iterations.

### Upstream proxy

All LLM SDK clients (GitHub Copilot, Anthropic, OpenAI, Azure, OpenRouter, Bedrock) honour an optional upstream proxy URL injected via a `ContextVar` (`_llm_proxy_var`). Copilot receives this through its child-process `HTTP_PROXY` and `HTTPS_PROXY` environment. The direct HTTP clients use the proxy configuration described in `llm.py`.

### Rate Limiting & Pacing

To prevent exceeding upstream LLM API limits (which can cause active scans to fail or encounter transient errors), `llm.py` implements a provider-level **Rate Limiting & Pacing** layer:

- **Token Bucket Algorithm:** Uses an asynchronous token-bucket rate limiter (`AsyncTokenBucketLimiter`) linked to each unique `(provider, model)` pair.
- **Coverage:** Pacing wraps **both** the non-agentic path (`_call` — page analysis, probe planning, reporting) **and** the agentic tool-using path (`_call_with_tools`, used by every dynamic / API / SAST / ALICE scan loop), so a configured `max_tpm` / `max_rpm` applies to the whole run, not just page analysis.
- **Estimated Pre-allocation:**
  - Before making an API request, the limiter estimates token usage (`estimate_tokens`) for prompt text (1.1x scaling of character count divided by 4) and vision payloads (765–1600 tokens depending on the provider). The agentic path flattens the running message history to estimate input size.
  - It also includes the configured `max_tokens` (or a 4096 default) for the model's response.
  - A single request's estimate is **clamped to the per-minute budget** (`max_tokens`): a call estimated larger than the whole TPM budget paces once and then proceeds, rather than waiting forever for capacity that can never exist.
  - If the bucket does not have enough capacity, the limiter sleeps until the required TPM (Tokens Per Minute) and RPM (Requests Per Minute) quotas are met.
- **Real-Time Notification:** When pacing first begins to wait, an `on_wait` callback fires a `rate_limit` scanner-phase event (e.g. *"LLM rate limit reached — pacing requests… (waiting ~Ns, reserved X tokens)"*) routed to the active run's log via the context emit function (the scanner log, the API scan log, or the ALICE stream), so a rate-limited scan never looks frozen. A matching *"rate limit cleared"* event is emitted once the call proceeds.
- **Post-Call Reconciliation:** Once the API call returns, the exact actual token counts consumed are retrieved, and the bucket's pre-allocation is reconciled (refunding the reserved-but-unused tokens). If the request fails, the reserved tokens are fully refunded.

---

## 10. Burp Suite Integration

**File**: `src/aespa/services/burp_rest.py`

When enabled, aespa can hand off targeted active scans to **Burp Suite Professional** via its REST API (default `http://127.0.0.1:1337`). This augments aespa's own probing with Burp's full active-scan engine for injection-class vulnerabilities.

### Workflow

```
Finding written by aespa scanner
  └─ _finding_burp_vuln_class(finding)
       • Maps finding to a Burp vulnerability class (sqli, xss, cmdi, etc.)
       • Checks BurpRestApiConfig to see if that class is enabled
  └─ _run_burp_active_scan_for_target(run_id, url, vuln_class)
       1. burp_rest.launch_active_scan(config, url, cookies=..., extra_headers=...)
            POST /v0.1/scan  →  returns integer task_id
       2. burp_rest.wait_for_scan(config, task_id)
            Polls GET /v0.1/scan/{task_id} with adaptive back-off:
              • 0–60 s  →  every 5 s
              • 60–180 s →  every 15 s
              • 180–600 s → every 30 s
            Returns when status ∈ {succeeded, failed, cancelled}
       3. Normalised Burp issues → ScanFinding rows (finding_source = "burp_active_scan")
```

### Scope pinning

Each Burp scan is scoped to the exact URL path prefix being tested so Burp does not re-crawl the whole site. Cookies and bearer tokens from the active `ScannerSession` are forwarded to Burp as custom headers so authenticated endpoints are tested with valid sessions.

### Per-class routing

Each vulnerability class can be toggled independently in `BurpRestApiConfig` (e.g. enable only SQLi and SSRF, skip XSS). The scanner also deduplicates Burp targets: if a `(run_id, url, vuln_class)` triple has already been dispatched in the current run, a second Burp scan is not launched.

### Connection test

`POST /api/settings/burp-rest-api/test-connection` probes `GET /v0.1/scan/0` and returns `{ok, message}`. A 404 from Burp counts as success (server is reachable; the scan ID just doesn't exist).

---

## 11. Findings & Validation

**Files**: `src/aespa/services/scanner.py` (finding-write & dedup path), `src/aespa/services/llm.py` (`normalize_finding_titles`), `src/aespa/services/validator.py`

### Deduplication

Findings are deduplicated as they are written, on the dynamic finding-write path in `scanner.py`:

1. **Title normalisation** — before a finding is persisted, `llm.normalize_finding_titles` asks the LLM to rewrite its title to a canonical form so near-identical findings (same vulnerability class, different parameter name) collapse to the same heading. ALICE findings skip this pass (`skip_normalize=True`) because they already carry specific, human-readable titles — see §15.
2. **Exact-title deduplication** — `_dynamic_finding_exists` then rejects any finding whose (normalised) title already exists at the same URL for the run, so genuinely identical findings are not written twice.

### Validation

Each finding starts with `validation_status = unvalidated`. The adversarial validator agent (`validator.py`) re-runs the probe with a mandate to disprove the finding. See §8 for full detail.

All findings carry a `finding_source` field that records their origin:

| Value | Source |
|---|---|
| `aespa_scanner` | Discovered by aespa's own structured or dynamic scan |
| `burp_active_scan` | Imported from a Burp Suite active scan triggered by aespa |
| `manual_import` | Imported via the findings import API |
| `unknown` | Legacy / untagged |

External findings can be imported via `POST /api/test-runs/{run_id}/findings/import`.

### Verified proof-of-concept (PoC) commands

When the validator confirms a finding, `validator.py` tries to attach a **reproducible `curl` command** (`ScanFinding.poc_command` / `poc_setup`). The pipeline is strict — "it works, or there is no PoC":

- The validator must supply a `poc_request` (method, url, headers, body) and a positive `poc_expect` assertion (a status code and/or a distinctive `body_contains` substring). Without a positive assertion nothing is attached.
- The URL is scope-locked to the finding's host; methods are restricted to an allow-list (`GET`, `HEAD`, `POST` — `POST` is permitted so a confirmed state-changing finding can be reproduced against the already-authorised target); sensitive headers (`authorization`, `cookie`, `host`, `content-length`) are stripped.
- Auth-required PoCs resolve the live session credential and emit a shippable command that reads it from a token file (`-H "Authorization: Bearer $(cat aespa-poc-auth.txt)"`), plus `poc_setup` markdown telling the user how to capture that file. The live credential never appears in the stored command.
- **Verification runs the request locally and shell-free**: the shipped command string is for the human, but the verification step builds a separate argv (`_build_curl_argv`) and runs it via `subprocess.run(argv)` with **no shell**, materialising the credential directly into the header. This avoids treating target-derived header/body/url values as shell syntax (a command-injection vector) and behaves identically on POSIX and Windows (POSIX `shlex` quoting is meaningless to `cmd.exe`). Only PoCs whose assertion holds on this re-run are persisted.
- Every suppressed/failed branch emits an INFO log + scan-log + Reporting-agent event so the reason a PoC is missing is visible (`_emit_poc_outcome`).

---

## 12. API Layer

**Files**: `src/aespa/api/`

The API is a **FastAPI** application. All routes are async and use SQLModel sessions injected via `Depends`.

### Key route groups

| Prefix | Router | Responsibility |
|---|---|---|
| `/api/sites/` | `sites.py` | CRUD for target sites and credentials |
| `/api/settings/llm-config` | `settings.py` | Get/set LLM provider config |
| `/api/settings/llm-profiles` | `settings.py` | CRUD for multi-role model routing profiles |
| `/api/settings/scanner-policy` | `settings.py` | Get/set scanner policy |
| `/api/settings/specialist-agent` | `settings.py` | Get/set specialist agent config |
| `/api/settings/burp-rest-api` | `settings.py` | Get/set Burp Suite REST API config |
| `/api/settings/burp-rest-api/test-connection` | `settings.py` | Test connectivity to Burp REST API |
| `/api/settings/upstream-proxy` | `settings.py` | Get/set upstream proxy config |
| `/api/settings/global-http-header` | `settings.py` | Get/set global custom HTTP header appended to scanner requests |
| `/api/settings/reporting-debug` | `reporting_debug.py` | Get/set reporting prompt debug capture settings |
| `/api/settings/cloudflare-access` | `settings.py` | Get/set the Cloudflare Access AUD verified on the proxy-injected JWT |
| `/api/test-runs/` | `test_runs.py` | Create runs, check status, retrieve site map graph |
| `/api/test-runs/{id}/thinking-scan/` | `scan.py` | Start/stop/status/resume for dynamic scan |
| `/api/test-runs/{id}/recon-summary` | `scan.py` | Get the structured attack surface summary for a run |
| `/api/test-runs/{id}/findings/` | `test_runs.py` | List, import, validate findings |
| `/api/test-runs/{id}/coverage` | `test_runs.py` | Web OWASP Coverage matrix (OWASP Top-10) (`GET`); `coverage/seed` re-seeds cells |
| `/api/test-runs/{id}/sast-runs/available` | `test_runs.py` | Completed SAST runs (with leads) available to import into this web run |
| `/api/test-runs/{id}/import-leads` | `test_runs.py` | Copy a SAST run's leads into this web run |
| `/api/test-runs/{id}/leads` | `test_runs.py` | List (`GET`) / clear-all (`DELETE`) leads imported into this web run; `leads/{lead_id}` deletes one |
| `/api/test-runs/{id}/thinking-log/export` | `scan.py` | Export the full scan activity log |
| `/api/test-runs/{id}/alice/run` | `alice.py` | `POST` start · `DELETE` stop background ALICE task |
| `/api/test-runs/{id}/alice/stream` | `alice.py` | SSE event stream with cursor-based replay |
| `/api/test-runs/{id}/alice/status` | `alice.py` | Check whether an ALICE task is running |
| `/api/test-runs/{id}/alice/sessions` | `alice.py` | `GET`/`PUT` chat session persistence |
| `/api/traffic/` | `traffic.py` | Paginated HTTP traffic log |
| `/ws/events/{run_id}` | `events.py` | WebSocket event stream |
| `/api/api-collections/` | `api_collections.py` | CRUD for API collections; document upload and parse; endpoint and credential management |
| `/api/api-collections/{id}/export` · `/api/api-collections/import` | `api_collections.py` | Export a collection (endpoints, credentials, metadata) as a JSON bundle and re-import it elsewhere |
| `/api/api-collections/{id}/readiness` | `api_collections.py` | `POST` run · `GET` retrieve LLM gap analysis |
| `/api/api-collections/{id}/test-runs/` | `api_collections.py` | Create API test runs under a collection |
| `/api/api-test-runs/{id}/scan/` | `api_test_runs.py` | Start/stop/status for API scans |
| `/api/api-test-runs/{id}/coverage` | `api_test_runs.py` | OWASP API Top-10 coverage matrix |
| `/api/api-test-runs/{id}/findings/` | `api_test_runs.py` | List, import, export API scan findings |
| `/api/api-test-runs/{id}/traffic` | `api_test_runs.py` | API scan HTTP traffic log |
| `/api/api-test-runs/{id}/alice/*` | `api_test_runs.py` | ALICE chat for API runs (same surface as web ALICE) |
| `/api/sast-runs` | `sast_runs.py` | `POST` (multipart) create a **standalone** SAST run from an uploaded source ZIP; `GET` lists all SAST runs |
| `/api/api-test-runs/{id}/import-leads` | `sast_runs.py` | Import independent copies from a completed SAST run into an API test run |
| `/api/sast-runs/{id}/scan/` | `sast_runs.py` | Start/stop/status for SAST scans |
| `/api/sast-runs/{id}/leads` | `sast_runs.py` | List the *original* `ScanLead` rows for a SAST run (imported copies excluded) |
| `/api/sast-runs/{id}/agent-log` | `sast_runs.py` | SAST agent activity log |

---

## 13. Frontend & Real-time Events

The web UI is a **single-page application** served from `src/aespa/web/`. It communicates with the backend over:
- **REST** for CRUD and control operations
- **WebSocket** (`/ws/events/{run_id}`) for real-time progress updates

### Telemetry rendering (`TokenUsageBar`)

Detail views for Web runs, API runs, and SAST runs embed the `TokenUsageBar` component. For API-key providers it renders per-model input, output, and prompt-cache tokens. For GitHub Copilot it leads with AI credits or legacy premium requests, model-call counts, and available allowance information, with token/cache details in the expanded view. The data is persisted in `token_usage_json`.

### WebSocket event types (emitted by `services/events.py`)

Events are emitted at key points during crawling and scanning:

- Crawl progress (pages discovered, depth reached)
- Thinking-scan step (action taken, tool called, finding written)
- Finding created / updated
- Task graph changes (hypothesis seeded, task status update)
- `agent_status` — emitted by every agent type (Test Lead, Specialist, Burp, Validator, Reporting) with `agent_id`, `role`, `status`, `current_task`, `outcome`; persisted to `ScanLog` so the Agents panel survives page reload
- `specialist_step` — per-step event from a running specialist (action type, method, URL, hypothesis)
- `scanner_phase` — scanner lifecycle events (scan started, JS sink analysis, stored XSS sweep, post-scan review, etc.)
- `llm_response` / `llm_protocol` scanner phases persist provider/model, native stop reason, usable block counts, context size, retry state, and safe Bedrock request/usage metadata
- Resumed agentic checkpoints are repaired when they end on an assistant turn: AESPA appends either an explicit continuation request or matching interrupted `tool_result` blocks before calling providers that prohibit assistant-message prefill
- `credential_discovered` — emitted when the dynamic scan finds and persists a valid credential; prompts the user to re-crawl with the new account
- `entra_authenticator_prompt` / `entra_authenticator_status` — number-matching and lifecycle updates for interactive Microsoft Entra authentication, including retry-required, success, and timeout states
- Error events

### UI tabs

#### Web scan run view

| Tab | Content |
|---|---|
| **Status** | Scan controls, run metadata, `TokenUsageBar` telemetry; sub-tabs: **Agents** (all agent rows with status), **Specialists** (specialist-only thread view), **Log** (raw timestamped event feed) |
| **Site Map** | Interactive graph of `CrawledPage` nodes and `PageLink` edges |
| **Intelligence** | `TargetIntelItems` — endpoints, forms, inputs, IDs, scripts, `xss_sink` items |
| **Attack Surface & Coverage** | Live evidence projection — canonical routes/methods/parameters, access observations, workprogram gaps, provenance, signals, and observed technologies |
| **Sessions** | `ScannerSession` records — auth cookies and tokens captured during crawl/scan |
| **Findings** | `ScanFinding` list sorted by severity, with CVSS scores, evidence, validation controls, and export/import (markdown) |
| **Traffic Log** | All `TrafficEntry` records (request + response) |
| **OWASP Coverage** | Web OWASP Top-10 coverage matrix (`PageOwaspTest` cells), updated live; Track/Enforce mode |
| **SAST Leads** | Import a completed SAST run's leads into this run (dropdown), then list the imported copies; per-row delete, clear-all, and export (markdown). Originals on the SAST run are untouched |
| **A.L.I.C.E.** | Interactive chat panel; supports multiple named sessions (tabs); see §15 |

#### API collection view

| Panel | Content |
|---|---|
| **Documents** | Uploaded spec/source files with parse status and re-parse trigger |
| **Endpoints** | Parsed `ApiEndpoint` rows with scope toggles and readiness indicators |
| **Credentials** | `ApiCredential` rows discovered from documents or entered manually |
| **Readiness** | LLM gap-analysis output (auth coverage, missing data, per-endpoint prereq status) |
| **Test Runs** | List of `ApiTestRun` records with scan controls |
| **SAST Runs** | List of `SastRun` records with scan controls and lead summary |

#### API scan run view

| Tab | Content |
|---|---|
| **Status / Log** | Agent activity log, scan controls, `TokenUsageBar` telemetry, real-time phase events |
| **OWASP Coverage** | OWASP API Top-10 coverage matrix — per-endpoint × per-category status badges, updated live |
| **Findings** | `ScanFinding` list for this API run |
| **Traffic** | HTTP traffic captured during the API scan |
| **A.L.I.C.E.** | Interactive ALICE chat tab (same surface as web scans) |

#### SAST run view

A top-level **SAST** screen lists all `SastRun` records and has a **New SAST Scan** button that uploads a source ZIP and starts a standalone scan.

| Panel | Content |
|---|---|
| **Status / Log** | Agent activity log, scan controls, `TokenUsageBar` telemetry |
| **Leads** | Original `ScanLead` rows with severity, confidence score, location, and evidence; exportable to markdown |

---

## 14. Concurrency & State Management

- **FastAPI async handlers** — all I/O is non-blocking via `asyncio`
- **Parallel crawl workers** — multiple Playwright browser instances share a `_CrawlShared` state object (asyncio locks around the URL frontier and seen-set)
- **Background tasks** — crawl and scan jobs run as `asyncio.Task`s; handles are stored in-memory so the API can stop them
- **Specialist agents** — each specialist runs as its own `asyncio.Task`; tracked in `_specialist_tasks[run_id]` so they are cancelled when the parent scan is stopped; concurrency is capped by `_specialist_running[run_id]` vs `SpecialistAgentConfig.max_concurrent`
- **ALICE background tasks** — `alice_tasks.py` holds a module-level `_registry: dict[int, AliceTask]` (one entry per run). Each task runs `run_alice_turn_stream` as an `asyncio.create_task`, decoupled from the HTTP connection; all emitted events are buffered in `AliceTask.events` so clients can replay from any cursor on reconnect
- **Scan checkpointing** — the LLM conversation history is serialised to the DB at regular intervals by `checkpoint.py`; `start_thinking_scan_resume` restores it on restart
- **Bounded scan completion** — `scan_completion.py` tracks structural progress across agentic turns to enforce termination policy and prevent non-terminating tool loops
- **Database** — SQLite via SQLAlchemy sync sessions wrapped in `run_in_executor` where needed; all schema changes are applied at startup via `db.py`
- **Auth session vault** — `ScannerSession` rows in the DB store serialised cookies/tokens; `scanner_sessions.py` manages load/save/invalidation

### Run-id collisions & `run_kind`

`TestRun` (web), `ApiTestRun`, and `SastRun` draw ids from **independent autoincrement sequences that collide in the same integer space** — run #5 can exist as all three at once. Tables shared across run kinds must therefore be disambiguated, or rows leak between unrelated runs:

- **Shared tables carry a `run_kind` column** (`'web'` / `'api'` / `'sast'`): `agent_log`, `scan_log`, `scanner_session`, `alice_chat_session`. Every query filters on it.
- **Findings use separate FK columns**: `ScanFinding.test_run_id` (web) vs `api_test_run_id` (API), both nullable. `ScanLead` copies key on `imported_into_run_id` for the same reason.
- **Event emission is scoped, not id-guessed**: `events.run_kind_scope("web"|"api"|"sast")` is the *sole* authoritative source of an event's kind. It is a context variable that `asyncio.create_task` snapshots, so every event a scan emits — directly or from any child task — inherits the right kind even when ids collide. Every background-task entry point that can emit `agent_status`/`scanner_phase` (the web/api/sast scanners, the crawler, the validator, ALICE) MUST open a scope; an emit that escapes every scope deterministically defaults to `'web'`. There is deliberately no per-id fallback registry — keying on a colliding run id is exactly what leaked events into the wrong run's Agents tab (issue #169 / the SAST Agents leak).
- **Deletion is scoped per kind** (`services/run_cleanup.py` + the inline web cascade in `api/test_runs.py`) so deleting a run removes exactly its own rows and nothing leaks into a later run that reuses the freed id. SQLite reuses the max id after the highest row is deleted, which is what makes this collision practical, not theoretical.

---

## 15. A.L.I.C.E. — Interactive Pentesting Chat

**Files**: `src/aespa/services/alice.py`, `src/aespa/services/alice_tasks.py`, `src/aespa/api/alice.py`

A.L.I.C.E. (AI LLM-Integrated Chat Engine) is an **interactive, user-directed pentesting agent** embedded in the run detail view. Unlike the autonomous dynamic scan, ALICE responds to natural-language instructions typed by the user and conducts targeted investigations in real time — probing specific endpoints, testing hypotheses, and writing confirmed findings directly to the scan report.

### Architecture overview

```
User types instruction in chat UI
  │
  ▼
POST /api/test-runs/{id}/alice/run
  └─ alice_tasks.start(run_id, tab_id, think_msg_id, reply_msg_id, message, history)
       └─ asyncio.create_task(_run(...))   ← background task, survives client disconnects
            └─ alice.run_alice_turn_stream(run_id, message, history)
                 └─ Agentic loop: LLM → tool → result → repeat until done/steps exhausted

Browser subscribes to event stream
  │
  ▼
GET /api/test-runs/{id}/alice/stream?cursor=N
  └─ alice_tasks.stream_events(run_id, cursor)
       ├─ Replay buffered events[cursor:]  ← catches up missed events (page refresh)
       └─ Live events from asyncio.Queue   ← pushed by _append() as they arrive
```

### Background task registry (`alice_tasks.py`)

The key design decision: **the agentic loop runs independently of the HTTP connection**. When a user refreshes the page, navigates away, or loses network for a moment, the agent keeps thinking and executing tools on the server.

```python
@dataclass
class AliceTask:
    run_id: int
    tab_id: str           # which chat session tab started this turn
    think_msg_id: str     # client-assigned ID for the thinking bubble
    reply_msg_id: str     # client-assigned ID for the reply bubble
    events: list[dict]    # all SSE events since task start (capped at BUFFER_LIMIT=2000)
    waiters: set[asyncio.Queue]  # one queue per connected SSE client
    asyncio_task: asyncio.Task
    done: bool
    accumulated_thought: str     # running total for a valid done event on cancel
    accumulated_message: str
```

`_append(task, event)` is synchronous and called from within the async task loop:
- Updates `accumulated_thought` / `accumulated_message` running totals
- Appends to `task.events` (trims oldest if over `BUFFER_LIMIT`)
- Pushes to every connected client queue via `q.put_nowait(event)` (non-blocking)

On `asyncio.CancelledError` (user hits Stop A.L.I.C.E.), a final `done` event is appended with the thought/message accumulated so far, so the UI always receives a clean terminal state.

### Reconnect and replay

When a client reconnects (page refresh, SPA navigation back to the run), it calls `GET /alice/stream?cursor=0`. The server replays `task.events[0:]` as SSE lines immediately, then switches to live delivery. The client re-accumulates `accumulatedThought` and `accumulatedMessage` from these replayed events, so the chat UI rebuilds the correct state even if the page was refreshed mid-stream.

`GET /alice/status` is polled on page load. If `running: true`, the client automatically calls `aliceSessionConnect` to start receiving events.

### Agentic loop (`alice.py`)

`run_alice_turn_stream` implements the multi-turn agentic loop as an async generator that yields SSE lines:

```
1. Load run/site config; verify scope of the user's instruction
2. Emit [A.L.I.C.E. Initializing] + scope-check status chunks
3. Convert chat history → Anthropic messages format
4. Loop (max ALICE_MAX_STEPS = 40):
     a. Emit [Step N] Calling LLM... thinking chunk
     b. Call LLM with tools (ALICE tool set — see below)
     c. Stream thinking blocks → thinking_chunk SSE events
     d. Stream text blocks → message_chunk SSE events
        (prepend \n\n separator if prior message content exists)
     e. Execute tool calls → emit step status + tool result chunks
     f. If model calls done tool → break
     g. If 3 consecutive text-only turns → break (nudge model back to tools)
5. Emit done SSE event with final accumulated thought + message
```

### Tools available to ALICE

| Tool | Description |
|---|---|
| `http_request` | Issue arbitrary HTTP requests; scope-checked; traffic logged |
| `browser` | Simple page fetch via httpx with browser-like headers |
| `context_tool` | Read-only access to crawl data (site map, page details, traffic) |
| `write_finding` | Persist a confirmed vulnerability directly to `ScanFinding`; **skips `normalize_finding_titles`** to prevent false deduplication |
| `forge_jwt` | Sign an HS256 JWT from a discovered secret; stores result in session vault |
| `decode_jwt` | Decode a JWT's header and payload |
| `credential_check` | Test a login URL with a list of candidate credential pairs |
| `register_account` | Create a test account and store the resulting session |
| `agent_dispatch` | Dispatch a Specialist Agent (see below) |
| `done` | End the turn with a summary |

#### `write_finding` deduplication

ALICE findings bypass the `normalize_finding_titles` LLM call (`skip_normalize=True`). The automated scanner uses title normalisation to group near-identical probe results under a canonical title; ALICE already generates specific, human-readable titles. Running normalisation against ALICE findings can rename a distinct finding to match an existing title at the same URL, causing it to be silently dropped as a duplicate.

Exact-title deduplication (`_dynamic_finding_exists`) still runs — genuinely identical findings are still rejected.

#### `agent_dispatch` — dispatching Specialist Agents from ALICE

The `dispatch_specialist_agent` function (public wrapper in `scanner.py`) bootstraps all required scanner context from the database (LLM config, scanner policy, specialist config, session vault, recon summary) and calls `_schedule_specialist_agent`. This allows ALICE to dispatch focused specialist agents on high-confidence leads just as the autonomous Test Lead does.

The specialist runs as an independent `asyncio.Task` under the same `run_id` and writes findings directly to the database.

### Chat session persistence

Chat history is stored server-side in a **normalised two-table schema** so any browser opening the same scan sees the full conversation history.

| Table | Purpose |
|---|---|
| `AliceChatSession` | One row per chat tab (`session_key`, `title`, `position`, `is_active`) |
| `AliceChatMessage` | One row per message bubble (`message_key`, `sender`, `type`, `text`, `ts`, `position`) |

The frontend saves state via `PUT /alice/sessions` with a debounce of 800 ms. Message text is updated in place (`message_key` is the client-assigned stable ID), so a long streaming response produces only a single row update rather than rewriting a full JSON blob.

`GET /alice/sessions` returns `{ chats, active_tab_id, updated_at }`. The `updated_at` timestamp (max across all sessions for the run) lets the client compare server state against local `savedAt` to decide which source is fresher — critical for the page-refresh case where local state is current but the server's debounced save is a few seconds behind.

### Client-side streaming state

The frontend maintains a module-level `aliceSessionStore` (keyed by `runId:tabId`) for within-page-session state:

```js
AliceSession {
  active: bool
  thinkMsgId, replyMsgId       // IDs of the in-progress bubbles
  accumulatedThought, accumulatedMessage  // growing totals (re-built from cursor=0 on reconnect)
  waiters: Set<handlers>       // subscriber pattern for multi-component updates
}
```

Subscribers update React state using `session.accumulatedThought` (the running total) rather than appending individual deltas — this ensures that even mid-stream, `parseAliceThinking` always receives a complete, parseable string and renders status blocks and tool-call cards rather than raw text.

A localStorage key `alice_recover_{runId}:{tabId}` is written on every chunk (bypassing React state). On page remount this key is used as a fallback if the module-level session was cleared (e.g. hard refresh, HMR).

### Stop A.L.I.C.E.

A **Stop A.L.I.C.E.** button appears in the run topbar whenever `aliceGlobalRunning` is true. Clicking it:
1. Aborts the local SSE connection (`AbortController.abort()`)
2. Calls `DELETE /alice/run` → `alice_tasks.stop(run_id)` → `asyncio.Task.cancel()`
3. The cancelled task appends a `done` event with partial content before exiting
4. All connected SSE clients receive the `done` event and close their streams

---

## 16. API Collections & API Scanning

**Files**: `src/aespa/services/api_collections.py`, `src/aespa/services/api_docs.py`, `src/aespa/services/api_documents.py`, `src/aespa/services/api_readiness.py`, `src/aespa/services/api_scanner.py`, `src/aespa/api/api_collections.py`, `src/aespa/api/api_test_runs.py`

The API scanning pipeline brings the same Test-Lead + Specialist + Validator agentic loop to REST APIs, replacing the Playwright-based browser with direct `httpx` calls.

### API Collections

An **`ApiCollection`** is the top-level resource for API scanning. It groups:
- A `base_url` and `scope_hosts` list (used for out-of-scope request blocking)
- Uploaded documents (specs, credentials, source code)
- Parsed `ApiEndpoint` and `ApiCredential` rows
- A `readiness_json` blob with the LLM gap analysis
- All `ApiTestRun` and `SastRun` records

### Document parsing (`services/api_docs.py`)

`parse_document(session, collection_id, document_id)` dispatches by `ApiDocument.doc_type`:

| `doc_type` | Parser |
|---|---|
| `openapi` / `swagger` | `prance` dereferences `$ref` chains; walker extracts paths, methods, parameters, request/response schemas |
| `postman` | Postman Collection v2/v2.1 item-tree walker |
| `credentials` | Line-by-line parser: bearer tokens, `key: value` pairs, curl `-H`/`-b` flag lines |
| `freetext` | LLM extraction of endpoint list + auth notes (capped at 40,000 chars) |
| `source_zip` | Safe ZIP extraction + framework-heuristic route scanner (Django urls.py, Flask `@app.route`, Express router, etc.). This derives API inventory only; it does not start or attach a SAST scan. |

Re-parse is idempotent — existing endpoints from the same document are deleted and replaced.

### LLM readiness assessment (`services/api_readiness.py`)

`assess_readiness(session, collection_id)` sends a structured gap-analysis prompt to the active LLM with up to 60 endpoints and all available credentials. It persists results to `ApiCollection.readiness_json` and per-endpoint `prereq_*` fields (missing auth, missing request body schema, etc.).

### OWASP API Top-10 coverage matrix

The coverage matrix maps every `(ApiEndpoint, OWASP_category)` pair to an `ApiEndpointTest` row. Categories are assigned by heuristic on scan start:

| Heuristic | Categories assigned |
|---|---|
| Path contains `{param}` | API1 (BOLA) |
| Method is PUT or PATCH | API3 (BOPLA) |
| Method is DELETE | API5 (BFLA) |
| All endpoints | API2 (Auth), API4 (Resource Consumption), API8 (Misconfiguration), API9 (Inventory) |
| Method is POST | API6 (Business Flows) |
| All endpoints | API10 (Unsafe Consumption) |

Cell statuses: `uncovered` → `in_progress` → `covered` (finding attached) / `skipped` (with reason).

**Track mode** — the agentic loop steers itself; cells are updated as probes are made.  
**Enforce mode** — after the main loop, `_enforce_coverage_loop` drives every still-uncovered cell to a terminal state. An LLM classifier decides per `(endpoint, category)` whether to probe or record a skip reason, up to a configurable budget.

### API scan engine (`services/api_scanner.py`)

The entry point `start_api_scan(api_run_id)` launches `_api_scan_task` as a background `asyncio.Task`.

```
_api_scan_task(api_run_id)
  └─ _do_api_thinking_scan(api_run_id)
       1. Load ApiTestRun, LLM config, scanner policy, collection
       2. seed_sessions_from_credentials — load ApiCredentials into scanner session vault
       3. seed_coverage_matrix — create ApiEndpointTest cells for all (endpoint, category) pairs
       4. _build_api_crawl_context — build LLM opening context from collection metadata + explicitly imported SAST leads
       5. _do_agentic_thinking_loop (shared with web scanner)
            • get_api_test_lead_tools supplies only API-aware top-level tools; browser,
              remove_finding, and agent_dispatch are withheld
            • _api_context_tool_fn routes endpoint_list / endpoint_detail / collection_info / finding_list
              to API-specific handlers and a strict safe subset to the shared handler; all other
              commands are rejected, including web-crawl target_inventory / search_assets
            • _api_check_scope is applied to every target request and redirect hop
            • _make_post_probe_fn updates the coverage matrix cell for each probe (endpoint, category)
            • _make_post_finding_fn stamps api_test_run_id and OWASP category on each finding
       7. (enforce mode only) _enforce_coverage_loop — drive uncovered cells to terminal state
```

### Scope enforcement

`_api_check_scope(url, api_run_id)` blocks requests outside the collection's `scope_hosts`. Out-of-scope attempts return an error string to the agent without making the request. The web dynamic scanner enforces the equivalent boundary through `scope.py::check_scope(url, site_id, run_id)` (host must be in `Site.scope_hosts` when set, and the page must not be marked `in_scope=False`).

**Redirects are re-checked per hop.** The scanner HTTP client uses `follow_redirects=True`, so a pre-send `check_scope` on the requested URL alone would let a target bounce the scanner to an out-of-scope/internal host (SSRF / scope bypass). `_request_scope_checked` therefore disables auto-follow and validates every `Location` against `check_scope` before following it; an out-of-scope redirect is refused (the unfollowed 3xx is surfaced to the agent with a `[SCOPE BLOCK]` note) so the off-scope host is never contacted. The browser (`browser` tool) path re-checks the **final** post-redirect URL after navigation and refuses to load an off-scope page into the agent's context; the auth flow is exempt so legitimate external-IdP/SSO redirects still work.

### ALICE on API runs

API test runs expose the same `/alice/*` endpoints as web test runs. API ALICE routes
`collection_info`, `endpoint_list`, and `endpoint_detail` to API-specific handlers and
persists captured sessions under `run_kind="api"`. Specialist dispatch is withheld in API
mode until the Specialist executor is fully API-aware. The API system prompt includes
OWASP API Top-10 category descriptions and API context tool documentation.

---

## 17. SAST Scanner & Scan Leads

**Files**: `src/aespa/services/sast_scanner.py`, `src/aespa/services/scan_leads.py`, `src/aespa/services/prompts/sast.py`, `src/aespa/api/sast_runs.py`, `src/aespa/api/test_runs.py` (web import)

The SAST scanner is a standalone agentic static-analysis pass over an uploaded source archive that produces high-confidence vulnerability **leads**. It is created from the SAST screen with `POST /api/sast-runs` (multipart); `collection_id` is NULL and the archive is stored on the run (`source_archive_path` / `source_filename`). A completed run's leads can then be explicitly copied into either a web or API test run. Source ZIPs uploaded to an API collection remain a separate API-inventory input and are not reused automatically by SAST.

### Architecture overview

```
start_sast_scan(sast_run_id)
  └─ _sast_scan_task(sast_run_id)
       1. Load SastRun and resolve its standalone `source_archive_path`.
       2. _safe_unzip - extract archive into a deterministic per-run
          directory at `<data_dir>/sast_extract/<id>/` (path-jailed:
          entries that would escape the root are rejected). A startup
          sweep (db._cleanup_orphaned_sast_extractions) reconciles any
          dirs leaked by a previous hard crash.
       3. _build_initial_message — construct LLM opening context; the agent
          discovers entry points itself with the file tools
       4. _make_tool_executor — build the tool executor with path-jailed file tools
       5. llm.thinking_agentic_loop with read-only file tools + write_lead / filter_lead / done
       6. _flush_unfiltered_candidates — persist any remaining candidates
          at scan end regardless of filter score
       7. Cleanup temp directory
```

### File tools (all path-jailed to the extraction root)

| Tool | Description |
|---|---|
| `list_files` | Directory listing up to configurable depth |
| `glob` | Pattern match across the file tree |
| `read_file` | Read a file by path; optional `start_line`/`end_line`; capped at 20,000 chars |
| `grep` | Regex or literal search across files; capped at 200 results |

### Lead lifecycle

```
Agent calls write_lead(title, description, category, severity, confidence, location, evidence)
  └─ Appended to _candidates[sast_run_id] in memory

Agent calls filter_lead(candidate_id, confidence_override?)
  └─ If confidence ≥ CONFIDENCE_THRESHOLD (0.7):
       create_lead() → ScanLead row persisted, status="open"
  └─ If below threshold: candidate discarded

At scan end:
  _flush_unfiltered_candidates() — any unfiltered candidate above threshold is persisted
```

### ScanLead entity (`services/scan_leads.py`)

| Field | Notes |
|---|---|
| `producer_run_id` | ID of the `SastRun` that created this lead (kept on copies for provenance) |
| `producer_run_type` | `"sast"` |
| `collection_id` | Owning `ApiCollection`, or NULL for standalone runs |
| `imported_into_run_type` / `imported_into_run_id` | Set on a *copy* imported into a dynamic run (e.g. `"web"` + `TestRun.id`); NULL on originals |
| `title` / `description` | Human-readable vulnerability description |
| `category` | OWASP category slug (e.g. `"API1"` or `"A03"`) |
| `severity` | `critical` · `high` · `medium` · `low` |
| `confidence` | 0.0–1.0; only leads ≥ 0.7 (`CONFIDENCE_THRESHOLD`) are persisted |
| `location` | Source file path and line reference |
| `evidence` | Code snippet or supporting text |
| `status` | `open` · `investigating` · `confirmed` · `dismissed` · `inconclusive` |
| `investigated_by_run_type` / `investigated_by_run_id` | The dynamic run that recorded the outcome via `update_lead` |
| `linked_finding_id` | Set when a confirmed lead is promoted to a `ScanFinding` |

### Lead consumption (API vs web)

The dynamic loop investigates leads via the shared `update_lead` action, which sets the outcome and — for a confirmed lead with no finding attached — auto-promotes it to a `ScanFinding` (keyed on `test_run_id` for web runs, `api_test_run_id` for API runs). How leads reach the loop's opening context differs by surface:

- **API scans** consume *explicitly imported copies*: the user picks a completed SAST run on the API run's **Scan Leads** tab and `copy_leads_to_run(sast_run_id, "api", run_id)` creates fresh rows owned only by that API run. API scan startup never creates a SAST run or imports collection leads automatically. `_build_api_crawl_context` and API A.L.I.C.E. inject only `format_leads_for_run("api", run_id)`.
- **Web scans** consume *copies*: the user picks a completed SAST run on the **SAST Leads** tab and `copy_leads_to_run(sast_run_id, "web", run_id)` duplicates its originals into new rows tagged `imported_into_*` (idempotent per source run; originals stay `open`). At scan start `scanner._do_thinking_scan` injects them via `format_leads_for_run("web", run_id)`. Because copies are independent, investigating them never mutates the source SAST run's leads, and deleting a SAST run leaves the copies intact (only `imported_into_run_id IS NULL` originals are cascade-deleted).

Leads are exportable to markdown from the UI (originals on the SAST run view, copies on web and API run lead tabs); the export embeds a hidden JSON block for future re-import.

### Concurrency

SAST scans use the same task-registry pattern as web and API scans: `_sast_tasks: dict[int, asyncio.Task]` and `_sast_stop_requested: set[int]`. A stop request causes the agentic loop to exit cleanly at the next step boundary.
