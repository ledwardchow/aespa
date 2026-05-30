# AESPA — Architecture & Internal Workings

AESPA (AI-Enabled Security Pentesting Agent) is an LLM-driven automated web application security scanner. It discovers endpoints through an intelligent crawl, then probes them for vulnerabilities through an **agentic dynamic scan**: the LLM acts as an autonomous Test Lead agent, deciding what to attack next in a loop, and can spawn focused **Specialist Agents** to deep-dive on confirmed leads.

---

## Table of Contents

1. [Repository Layout](#1-repository-layout)
2. [How to Run](#2-how-to-run)
3. [System Overview](#3-system-overview)
4. [Configuration](#4-configuration)
5. [Data Models](#5-data-models)
6. [Crawling](#6-crawling)
7. [Dynamic Scan (Thinking Mode)](#7-dynamic-scan-thinking-mode)
8. [Multi-Agent System](#8-multi-agent-system)
9. [LLM Integration](#9-llm-integration)
10. [Burp Suite Integration](#10-burp-suite-integration)
11. [Findings & Validation](#11-findings--validation)
12. [API Layer](#12-api-layer)
13. [Frontend & Real-time Events](#13-frontend--real-time-events)
14. [Concurrency & State Management](#14-concurrency--state-management)
15. [A.L.I.C.E. — Interactive Pentesting Chat](#15-alice--interactive-pentesting-chat)

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
│   ├── settings.py        # /api/settings/* — LLM, policy, Burp, proxy, specialists
│   ├── traffic.py         # /api/traffic/* — HTTP traffic log
│   └── events.py          # WebSocket event stream
└── services/
    ├── crawler.py         # LLM-guided parallel web crawl
    ├── scanner.py         # Dynamic (agentic) scan + specialist agent dispatch
    ├── llm.py             # Multi-provider LLM client, agent tools, WSTG skills
    ├── prompts/           # Extracted modular prompt templates
    │   ├── reporting.py   # Reporting / post-scan review prompts
    │   ├── specialist.py  # Specialist agent prompts
    │   ├── test_lead.py   # Test Lead agent prompts
    │   └── validator.py   # Adversarial validator prompts
    ├── alice.py           # A.L.I.C.E. agentic loop & tool executor
    ├── alice_tasks.py     # Background task registry — survives client disconnects
    ├── burp_rest.py       # Burp Suite Professional REST API client
    ├── checkpoint.py      # Scan resume — persist and restore LLM conversation state
    ├── findings.py        # Deduplication, grouping, post-scan LLM pre-screen
    ├── scanner_sessions.py# Auth session vault (cookies, tokens)
    ├── scope.py           # Scan scope boundaries and out-of-scope filtering
    ├── task_graph.py      # Recon summary, pentest hypothesis & task tracking
    ├── validator.py       # Adversarial validator agent (LLM-assisted finding validation)
    ├── traffic.py         # HTTP capture (Playwright intercept + httpx)
    ├── events.py          # WebSocket event emission
    └── settings.py        # LLM config / scanner policy / Burp / proxy / specialist config
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
│  Routers: sites · settings · test_runs · scan               │
│           traffic · events                                  │
└──────┬───────────────────────┬──────────────────────────────┘
       │                       │
       ▼                       ▼
┌─────────────┐       ┌─────────────────────────────────────┐
│  Services   │       │  LLM Provider                       │
│  ─────────  │       │  (Anthropic / OpenAI / Google /     │
│  crawler    │◄──────│   Bedrock / Azure / OpenRouter)     │
│  scanner    │       └─────────────────────────────────────┘
│  findings   │
│  validator  │       ┌─────────────────────────────────────┐
│  task_graph │       │  Burp Suite Professional            │
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
│  TargetIntelItems · PentestHypotheses · PentestTasks        │
│  ScanLogs · AliceChatSessions · AliceChatMessages           │
│  BurpRestApiConfig · UpstreamProxyConfig                    │
└─────────────────────────────────────────────────────────────┘
```

A **test run** is the central unit of work. It ties together a target site, its credentials, the LLM config, the scanner policy, and all results (crawled pages, traffic, findings, hypotheses). A run progresses through phases: `created → crawling → crawled → scanning → scanned` (plus `thinking_scanning`).

---

## 4. Configuration

### LLM Configuration (`LLMProviderConfig` & `LLMConfig` models)

LLM settings are split into two entities to separate reusable provider connections/credentials from configuration/execution profiles:

#### 1. Reusable Provider Config (`LLMProviderConfig` model)

Defines API connections and rate limits for different LLM backends:

| Field | Default | Description |
|---|---|---|
| `name` | `Default Provider` | Label for the provider |
| `api_format` | `anthropic` | API format: `anthropic`, `openai`, `openai_compatible`, `openrouter`, `google`, `bedrock`, `azure_openai`, `azure_foundry` etc. |
| `api_key` | — | Provider API key (stored securely in DB, never exposed in API) |
| `base_url` | — | Override endpoint URL (e.g., custom OpenAI compatible base URLs or Azure Foundry endpoints) |
| `models_json` | `[]` | JSON list of available model names for this provider |
| `max_tpm` | — | Optional Token-Per-Minute rate limit for this provider (activates pacing) |
| `max_rpm` | — | Optional Request-Per-Minute rate limit for this provider (activates pacing) |

#### 2. Saved LLM Profile (`LLMConfig` model)

Defines execution parameters linked to a provider:

| Field | Default | Description |
|---|---|---|
| `name` | `Default` | Profile name label |
| `is_active` | `false` | Master active switch (only one profile active globally) |
| `provider_id` | — | Foreign key linking to the `LLMProviderConfig` connection |
| `model` | `claude-opus-4-5` | Specific model identifier to run |
| `max_tokens` | `4096` | Max tokens per LLM call (60000+ recommended for Claude 3.5 Sonnet) |
| `temperature` | `0.0` | Deterministic by default |
| `use_vision` | `false` | Include Playwright screenshots in prompts (requires vision-capable model) |

### Scanner Policy (`ScannerPolicy` model)

| Field | Default | Description |
|---|---|---|
| `scan_mode` | `safe_active` | `passive` (GET/HEAD only) · `safe_active` (+ POST) · `aggressive` (all methods) · `destructive` |
| `max_probes_per_page` | `50` | Cap on probe attempts per crawled page |
| `thinking_max_steps` | `120` | Step limit for the dynamic scan loop |
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

Singleton row (id = 1). Routes scanner and/or LLM traffic through an upstream HTTP proxy (e.g. Burp Suite's proxy listener or a corporate proxy).

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
| `trigger_specialist_on_burp` | `false` | Also dispatch a specialist alongside each Burp active scan |

### Adversarial Validator Config (`AdversarialValidatorConfig` model)

Singleton row (id = 1). Controls the adversarial validation agent that attempts to disprove each finding.

| Field | Default | Description |
|---|---|---|
| `enabled` | `true` | Use adversarial agent mode; `false` falls back to legacy static-probe validation |
| `max_steps` | `20` | Step budget per validation pass |
| `min_severity` | `low` | Skip validation for findings below this severity (`critical`\|`high`\|`medium`\|`low`\|`info`) |
| `auto_validate_inline` | `true` | Automatically validate each finding immediately after it is written during a dynamic scan |
| `require_concrete_disproof` | `true` | Strict mode — only return `false_positive` when the validator finds a concrete innocent explanation; when `false`, failure to reproduce counts as false positive |

---

## 5. Data Models

All models are defined in `src/aespa/models.py` using **SQLModel** (SQLAlchemy + Pydantic).

### Core entities

| Model | Purpose |
|---|---|
| `Site` | Target website (base URL, auth settings, associated credentials) |
| `Credential` | Login credentials tied to a site (username, password, login URL) |
| `LLMProviderConfig` | Reusable LLM provider connection settings (API keys, base URLs, rate limits) |
| `LLMConfig` | Saved LLM configuration/execution profile linked to a provider |
| `ScannerPolicy` | Scan behaviour policy for a test run |
| `BurpRestApiConfig` | Singleton — Burp Suite REST API connection and routing settings |
| `UpstreamProxyConfig` | Singleton — upstream HTTP proxy settings for scanner and LLM traffic |
| `TestRun` | A single scan session; owns all scan artefacts |
| `CrawledPage` | A discovered page/endpoint with LLM-assigned flags |
| `PageLink` | Directed edge between two `CrawledPage` nodes (site map graph) |
| `TrafficEntry` | A captured HTTP request/response pair |
| `ScanFinding` | A discovered vulnerability with evidence and CVSS score |
| `ScannerSession` | Reusable auth material (cookies, JWT, metadata) |
| `TargetIntelItem` | Normalised reconnaissance atom (endpoint, form, input, ID, script, xss_sink) |
| `PentestHypothesis` | Attack hypothesis seeded from crawl intelligence |
| `PentestTask` | Concrete work item under a hypothesis (URL, method, status) |
| `ScanLog` | Audit event emitted during crawl/scan phases |
| `AliceChatSession` | One ALICE chat tab per test run (title, ordering, active flag) |
| `AliceChatMessage` | One chat bubble inside an `AliceChatSession` (sender, type, text) |

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
| `finding_source` | Origin of the finding: `aespa_scanner` · `burp_active_scan` · `manual_import` · `unknown` |
| `validation_status` | `unvalidated` · `validating` · `confirmed` · `unconfirmed` · `false_positive` |

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

### LLM involvement

The crawler sends each page's content to the LLM twice:
- **Analysis prompt**: Classify the page (flags above) and extract intelligence atoms.
- **Navigation prompt**: Suggest which links are most interesting to follow next (prioritising high-value pages like login forms, API endpoints, admin areas).

Scope enforcement prevents crawling outside the target domain (configurable via `allow_subdomains`).

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
       2. Run JS sink analysis (_analyse_js_sinks) — fetches each
          discovered JS file (TargetIntelItem kind=script), regex-scans
          for unsanitized innerHTML/outerHTML/document.write sinks,
          saves TargetIntelItem(kind=xss_sink) and info-severity findings
       3. Authenticate → ScannerSession
       4. Build recon summary (_build_thinking_context_from_recon_summary)
          — structures crawl data into trust zones, entry points, and
          prioritised attack classes; stored on TestRun.recon_summary
       5. Seed PentestHypotheses + PentestTasks from recon summary
       6. Build LLM opening context from recon summary
       7. Detect auth cookies for boundary checks
       8. Restore checkpoint if this is a resumed scan
       └─ _do_agentic_thinking_loop(...)   ← main loop
```

### Scan resume

The checkpoint service (`services/checkpoint.py`) serialises the LLM conversation history to the database at regular intervals. If a scan is interrupted (server restart, user stop) it can be resumed with `start_thinking_scan_resume(run_id)`, which restores the conversation at the last saved checkpoint rather than starting over.

### Agentic loop

Two execution modes depending on the configured LLM provider:

| Mode | Providers | Description |
|---|---|---|
| **Native tool-use** | All models | Single continuous session; the LLM natively calls tools. Produces tighter reasoning chains. |
| **Step-by-step** | DEPRECATED| Each iteration sends the full conversation history; the LLM emits a JSON action; the harness executes it and appends the result. |

The loop terminates when:
- The LLM calls the `done` action (with a summary)
- `thinking_max_steps` is reached
- A stop is requested via the API
- An unrecoverable network error occurs

### Actions available to the LLM

| Action | Description |
|---|---|
| `http` | Issue an arbitrary HTTP request (method, URL, headers, body) |
| `browser` | Playwright commands: `goto`, `fill`, `click`, `wait`, `snapshot` |
| `jwt` | Forge a signed HS256 JWT from a discovered secret |
| `decode_jwt` | Decode a JWT's header and payload; optionally verify the HS256 signature against a known secret |
| `credential_check` | Test a login URL with candidate credentials |
| `finding_write` | Record a confirmed vulnerability |
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

### Task graph

The `PentestHypothesis` / `PentestTask` graph (managed in `services/task_graph.py`) gives the LLM and the UI a structured view of what has been explored:

- **Hypothesis**: a high-level attack theory (e.g. "IDOR on /api/orders/{id}")
- **Task**: a concrete attempt under a hypothesis (target URL, method, status: pending → in_progress → completed/failed)

Hypotheses are derived from the `attack_classes` in the recon summary so the task queue is directly grounded in the attack surface analysis.

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
         recon_summary_entry, session_vault, llm_cfg, max_steps
     )
       1. Build opening brief from dispatch payload + recon summary entry
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

`task_graph.build_recon_summary(run_id)` generates a structured `ReconSummary` from crawl data at the start of the dynamic scan. It is stored on `TestRun.recon_summary` and used in three places:

1. **LLM opening context** — the Test Lead receives the attack surface picture as its first message
2. **Specialist briefing** — when dispatching a specialist, its `recon_summary_entry` provides the relevant `attack_class` rationale and entry points
3. **Attack Surface UI panel** — rendered in the Tasks tab (Attack Surface sub-tab)

The `ReconSummary` schema:

```json
{
  "trust_zones":     { "public": [...], "authenticated_user": [...], "admin": [...] },
  "entry_points":    [ {"url": "...", "method": "POST", "params": ["email", "password"]}, ... ],
  "attack_classes":  [ {"class": "idor", "rationale": "...", "priority": 9, "entry_points": [...]}, ... ],
  "business_logic_pages": [...],
  "tech_stack":      { "server": "Apache/2.4.58", "language": "PHP 8.3", "db": "MySQL" },
  "credential_roles": [ {"role": "user", "source": "registration", "count": 1}, ... ]
}
```

---

## 9. LLM Integration

**File**: `src/aespa/services/llm.py`

The LLM service provides a **provider-agnostic client** that maps onto:

| Provider | SDK used |
|---|---|
| `anthropic` | `anthropic` Python SDK (native tool-use supported) |
| `openai` | `openai` Python SDK |
| `google` | `google-generativeai` |
| `bedrock` | `boto3` / `anthropic` Bedrock adapter |
| `azure_openai` | `openai` SDK with Azure base URL |
| `openai_compatible` | `openai` SDK with custom base URL |
| `openrouter` | `openai` SDK with OpenRouter base URL |

All structured outputs (probe lists, finding objects, page analysis) are produced via **JSON mode** or tool-use — the LLM is never asked to produce free-form text that is parsed by regex.

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

All LLM SDK clients (Anthropic, OpenAI, Azure, OpenRouter, Bedrock) honour an optional upstream proxy URL injected via a `ContextVar` (`_llm_proxy_var`). When `UpstreamProxyConfig.proxy_llm` is enabled, every outbound LLM request flows through the configured proxy. SSL verification is disabled globally when a proxy is active to support HTTPS interception setups (e.g. Burp Suite's proxy listener).

### Rate Limiting & Pacing

To prevent exceeding upstream LLM API limits (which can cause active scans to fail or encounter transient errors), `llm.py` implements a provider-level **Rate Limiting & Pacing** layer:

- **Token Bucket Algorithm:** Uses an asynchronous token-bucket rate limiter (`AsyncTokenBucketLimiter`) linked to each unique `(provider, model)` pair.
- **Estimated Pre-allocation:**
  - Before making an API request, the limiter estimates token usage (`estimate_tokens`) for prompt text (1.1x scaling of character count divided by 4) and vision payloads (765–1600 tokens depending on the provider).
  - It also includes the configured `max_tokens` (or a 4096 default) for the model's response.
  - If the bucket does not have enough capacity, the limiter sleeps until the required TPM (Tokens Per Minute) and RPM (Requests Per Minute) quotas are met.
- **Real-Time Notification:** If pacing triggers, a `rate_limit` scanner-phase SSE event is emitted (e.g. *"LLM rate limit reached. Pacing and temporarily slowing down requests... (Reserved X tokens)"*) to keep the user informed in the UI.
- **Post-Call Reconciliation:** Once the API call returns, the exact actual token counts consumed are retrieved, and the bucket's pre-allocation is reconciled (refunding estimated but unused tokens). If the request fails, the estimated tokens are fully refunded.

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

**Files**: `src/aespa/services/findings.py`, `src/aespa/services/validator.py`

### Deduplication

`findings.py` runs two deduplication passes:

1. **Title normalisation** — the LLM rewrites finding titles to a canonical form so near-identical findings (same vulnerability class, different parameter name) get the same heading
2. **Global deduplication** — findings are grouped by vulnerability class and host; the LLM identifies which are true duplicates and which are distinct instances

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

---

## 12. API Layer

**Files**: `src/aespa/api/`

The API is a **FastAPI** application. All routes are async and use SQLModel sessions injected via `Depends`.

### Key route groups

| Prefix | Router | Responsibility |
|---|---|---|
| `/api/sites/` | `sites.py` | CRUD for target sites and credentials |
| `/api/settings/llm-config` | `settings.py` | Get/set LLM provider config |
| `/api/settings/scanner-policy` | `settings.py` | Get/set scanner policy |
| `/api/settings/specialist-agent` | `settings.py` | Get/set specialist agent config |
| `/api/settings/burp-rest-api` | `settings.py` | Get/set Burp Suite REST API config |
| `/api/settings/burp-rest-api/test-connection` | `settings.py` | Test connectivity to Burp REST API |
| `/api/settings/upstream-proxy` | `settings.py` | Get/set upstream proxy config |
| `/api/test-runs/` | `test_runs.py` | Create runs, check status, retrieve site map graph |
| `/api/test-runs/{id}/thinking-scan/` | `scan.py` | Start/stop/status/resume for dynamic scan |
| `/api/test-runs/{id}/recon-summary` | `scan.py` | Get the structured attack surface summary for a run |
| `/api/test-runs/{id}/findings/` | `test_runs.py` | List, import, validate findings |
| `/api/test-runs/{id}/thinking-log/export` | `scan.py` | Export the full scan activity log |
| `/api/test-runs/{id}/alice/run` | `alice.py` | `POST` start · `DELETE` stop background ALICE task |
| `/api/test-runs/{id}/alice/stream` | `alice.py` | SSE event stream with cursor-based replay |
| `/api/test-runs/{id}/alice/status` | `alice.py` | Check whether an ALICE task is running |
| `/api/test-runs/{id}/alice/sessions` | `alice.py` | `GET`/`PUT` chat session persistence |
| `/api/traffic/` | `traffic.py` | Paginated HTTP traffic log |
| `/ws/events/{run_id}` | `events.py` | WebSocket event stream |

---

## 13. Frontend & Real-time Events

The web UI is a **single-page application** served from `src/aespa/web/`. It communicates with the backend over:
- **REST** for CRUD and control operations
- **WebSocket** (`/ws/events/{run_id}`) for real-time progress

### WebSocket event types (emitted by `services/events.py`)

Events are emitted at key points during crawling and scanning, enabling the UI to update live:

- Crawl progress (pages discovered, depth reached)
- Thinking-scan step (action taken, tool called, finding written)
- Finding created / updated
- Task graph changes (hypothesis seeded, task status update)
- `agent_status` — emitted by every agent type (Test Lead, Specialist, Burp, Validator, Reporting) with `agent_id`, `role`, `status`, `current_task`, `outcome`; persisted to `ScanLog` so the Agents panel survives page reload
- `specialist_step` — per-step event from a running specialist (action type, method, URL, hypothesis)
- `scanner_phase` — scanner lifecycle events (scan started, JS sink analysis, stored XSS sweep, post-scan review, etc.)
- `credential_discovered` — emitted when the dynamic scan finds and persists a valid credential; prompts the user to re-crawl with the new account
- Error events

### UI tabs

The run view has seven top-level tabs:

| Tab | Content |
|---|---|
| **Status** | Scan controls, run metadata, token usage; sub-tabs: **Agents** (all agent rows with status), **Specialists** (specialist-only thread view), **Log** (raw timestamped event feed) |
| **Site Map** | Interactive graph of `CrawledPage` nodes and `PageLink` edges |
| **Intelligence** | `TargetIntelItems` — endpoints, forms, inputs, IDs, scripts, `xss_sink` items |
| **Task Graph** | Sub-tabs: **Attack Surface** (rendered `ReconSummary` — trust zones, attack classes, tech stack) and **Task Queue** (`PentestHypothesis` tree with `PentestTask` leaves) |
| **Sessions** | `ScannerSession` records — auth cookies and tokens captured during crawl/scan |
| **Findings** | `ScanFinding` list sorted by severity, with CVSS scores, evidence, and validation controls |
| **Traffic Log** | All `TrafficEntry` records (request + response) |
| **A.L.I.C.E.** | Interactive chat panel; supports multiple named sessions (tabs); see §15 |

---

## 14. Concurrency & State Management

- **FastAPI async handlers** — all I/O is non-blocking via `asyncio`
- **Parallel crawl workers** — multiple Playwright browser instances share a `_CrawlShared` state object (asyncio locks around the URL frontier and seen-set)
- **Background tasks** — crawl and scan jobs run as `asyncio.Task`s; handles are stored in-memory so the API can stop them
- **Specialist agents** — each specialist runs as its own `asyncio.Task`; tracked in `_specialist_tasks[run_id]` so they are cancelled when the parent scan is stopped; concurrency is capped by `_specialist_running[run_id]` vs `SpecialistAgentConfig.max_concurrent`
- **ALICE background tasks** — `alice_tasks.py` holds a module-level `_registry: dict[int, AliceTask]` (one entry per run). Each task runs `run_alice_turn_stream` as an `asyncio.create_task`, decoupled from the HTTP connection; all emitted events are buffered in `AliceTask.events` so clients can replay from any cursor on reconnect
- **Scan checkpointing** — the LLM conversation history is serialised to the DB at regular intervals by `checkpoint.py`; `start_thinking_scan_resume` restores it on restart
- **Database** — SQLite via SQLAlchemy sync sessions wrapped in `run_in_executor` where needed; all schema changes are applied at startup via `db.py`
- **Auth session vault** — `ScannerSession` rows in the DB store serialised cookies/tokens; `scanner_sessions.py` manages load/save/invalidation

---

## 15. A.L.I.C.E. — Interactive Pentesting Chat

**Files**: `src/aespa/services/alice.py`, `src/aespa/services/alice_tasks.py`, `src/aespa/api/alice.py`

A.L.I.C.E. (Automated LLM-Integrated Chat Engine) is an **interactive, user-directed pentesting agent** embedded in the run detail view. Unlike the autonomous dynamic scan, ALICE responds to natural-language instructions typed by the user and conducts targeted investigations in real time — probing specific endpoints, testing hypotheses, and writing confirmed findings directly to the scan report.

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

