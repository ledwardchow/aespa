# AESPA — Architecture & Internal Workings

AESPA (AI-Enabled Security Pentesting Agent) is an LLM-driven automated web application security scanner. It discovers endpoints through an intelligent crawl, then probes them for vulnerabilities using two complementary scan modes: a **structured scan** (LLM plans deterministic probes page-by-page) and a **dynamic/thinking scan** (the LLM acts as an autonomous agent, deciding what to attack next in a loop).

---

## Table of Contents

1. [Repository Layout](#1-repository-layout)
2. [How to Run](#2-how-to-run)
3. [System Overview](#3-system-overview)
4. [Configuration](#4-configuration)
5. [Data Models](#5-data-models)
6. [Crawling](#6-crawling)
7. [Structured Scan](#7-structured-scan)
8. [Dynamic Scan (Thinking Mode)](#8-dynamic-scan-thinking-mode)
9. [LLM Integration](#9-llm-integration)
10. [Findings & Validation](#10-findings--validation)
11. [API Layer](#11-api-layer)
12. [Frontend & Real-time Events](#12-frontend--real-time-events)
13. [Concurrency & State Management](#13-concurrency--state-management)
14. [Security Controls](#14-security-controls)

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
│   ├── scan.py            # /api/test-runs/{id}/scan/* & thinking-scan/*
│   ├── test_runs.py       # /api/test-runs/* — CRUD, status, site map graph
│   ├── sites.py           # /api/sites/* — target website management
│   ├── settings.py        # /api/settings/* — LLM & policy configuration
│   ├── traffic.py         # /api/traffic/* — HTTP traffic log
│   └── events.py          # WebSocket event stream
└── services/
    ├── crawler.py         # LLM-guided parallel web crawl
    ├── scanner.py         # Structured scan + dynamic (agentic) scan
    ├── llm.py             # Multi-provider LLM client abstractions
    ├── findings.py        # Deduplication, grouping, reporting
    ├── scanner_sessions.py# Auth session vault (cookies, tokens)
    ├── task_graph.py      # Pentest hypothesis & task tracking
    ├── validator.py       # LLM-assisted finding validation
    ├── traffic.py         # HTTP capture (Playwright intercept + httpx)
    ├── events.py          # WebSocket event emission
    └── settings.py        # LLM config / scanner policy service layer
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
│  validator  │
│  task_graph │
│  traffic    │
│  events     │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│  SQLite database  (aespa.db — via SQLModel / SQLAlchemy)    │
│  Sites · Credentials · TestRuns · CrawledPages · PageLinks  │
│  TrafficEntries · ScanFindings · ScannerSessions            │
│  TargetIntelItems · PentestHypotheses · PentestTasks        │
│  ScanLogs                                                   │
└─────────────────────────────────────────────────────────────┘
```

A **test run** is the central unit of work. It ties together a target site, its credentials, the LLM config, the scanner policy, and all results (crawled pages, traffic, findings, hypotheses). A run progresses through phases: `created → crawling → crawled → scanning → scanned` (plus `thinking_scanning`).

---

## 4. Configuration

### LLM Configuration (`LLMConfig` model)

| Field | Default | Description |
|---|---|---|
| `provider` | `anthropic` | One of: anthropic, openai, google, bedrock, azure_openai, openai_compatible, openrouter |
| `model` | `claude-opus-4-5` | Model identifier for the chosen provider |
| `api_key` | — | Provider API key (stored in DB, never returned in API) |
| `base_url` | — | Override endpoint URL (for openai_compatible / Azure) |
| `max_tokens` | `4096` | Max tokens per LLM call (60000 recommended for Sonnet) |
| `temperature` | `0.0` | Deterministic by default |
| `enable_vision` | `false` | Include page screenshots in prompts |

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

---

## 5. Data Models

All models are defined in `src/aespa/models.py` using **SQLModel** (SQLAlchemy + Pydantic).

### Core entities

| Model | Purpose |
|---|---|
| `Site` | Target website (base URL, auth settings, associated credentials) |
| `Credential` | Login credentials tied to a site (username, password, login URL) |
| `LLMConfig` | LLM provider settings for a test run |
| `ScannerPolicy` | Scan behaviour policy for a test run |
| `TestRun` | A single scan session; owns all scan artefacts |
| `CrawledPage` | A discovered page/endpoint with LLM-assigned flags |
| `PageLink` | Directed edge between two `CrawledPage` nodes (site map graph) |
| `TrafficEntry` | A captured HTTP request/response pair |
| `ScanFinding` | A discovered vulnerability with evidence and CVSS score |
| `ScannerSession` | Reusable auth material (cookies, JWT, metadata) |
| `TargetIntelItem` | Normalised reconnaissance atom (endpoint, form, input, ID, script) |
| `PentestHypothesis` | Attack hypothesis seeded from crawl intelligence |
| `PentestTask` | Concrete work item under a hypothesis (URL, method, status) |
| `ScanLog` | Audit event emitted during crawl/scan phases |

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
| `validation_status` | `unvalidated` · `validating` · `confirmed` · `unconfirmed` · `false_positive` |

---

## 6. Crawling

**File**: `src/aespa/services/crawler.py`  
**Entry point**: `async start_crawl(run_id)`

The crawler performs a **multi-user, LLM-guided BFS** across the target site using Playwright browser instances.

### Process

```
start_crawl(run_id)
  └─ _do_crawl(run_id)
       1. Load site config & credentials
       2. Authenticate via Playwright (manual login flow or scripted)
       3. Export auth cookies → ScannerSession
       4. Spawn N parallel browser workers (_CrawlShared state)
       └─ Per worker, BFS loop:
            a. Load page in Playwright, intercept network traffic
            b. Extract page text, links, forms, inputs
            c. Send page content to LLM → analyse flags (req_auth, takes_input, etc.)
            d. Ask LLM "where next?" → ranked link suggestions
            e. Enqueue new URLs (in-scope, within depth/page limits)
            f. Persist CrawledPage + PageLinks + TrafficEntries
       5. Extract TargetIntelItems (endpoints, forms, inputs, IDs, scripts, JWT hints)
       6. Update TestRun status → crawled
```

### LLM involvement

The crawler sends each page's content to the LLM twice:
- **Analysis prompt**: Classify the page (flags above) and extract intelligence atoms.
- **Navigation prompt**: Suggest which links are most interesting to follow next (prioritising high-value pages like login forms, API endpoints, admin areas).

Scope enforcement prevents crawling outside the target domain (configurable via `allow_subdomains`).

---

## 7. Structured Scan

**File**: `src/aespa/services/scanner.py`  
**Entry point**: `async start_scan(run_id, page_ids=None)`

The structured scan works **page-by-page**: for each crawled page the LLM plans a set of probes, those probes are executed, and the responses are fed back to the LLM for analysis.

### Process

```
start_scan(run_id)
  └─ _do_scan(run_id)
       For each CrawledPage:
         1. Auth: export cookies/tokens from ScannerSession
         2. Plan:  send page metadata + intel to LLM
                   LLM returns a list of ProbeSpec objects
         3. Execute probes:
              - http   → direct httpx request (injection, SSRF, auth bypass)
              - form   → Playwright form submission (CSRF, state manipulation)
              - idor   → expand IDOR markers into concrete ID ranges
         4. Analyse: send probe responses to LLM
                     LLM returns ScanFinding (or null)
         5. Persist: store finding with evidence, screenshots, traffic
```

### Probe types

| Type | Mechanism | Typical targets |
|---|---|---|
| `http` | Direct httpx request | Auth bypass, header injection, SSRF, SQLi, parameter tampering |
| `form` | Playwright browser submission | CSRF, business-logic, state manipulation |
| `idor` | Enumerate ID variants (±500 range around known IDs) | Broken object-level access control |

The LLM-generated `ProbeSpec` specifies method, URL, headers, body, and the intended hypothesis. The scanner enforces `ScannerPolicy` limits (blocked headers, allowed methods, body size cap) before sending any request.

---

## 8. Dynamic Scan (Thinking Mode)

**File**: `src/aespa/services/scanner.py`  
**Entry point**: `async start_thinking_scan(run_id)`

The dynamic scan is an **autonomous agentic loop**: the LLM is given a toolkit and decides each action itself, building on prior observations. This allows it to chain multi-step attacks that the structured scan cannot discover.

### Bootstrap

```
start_thinking_scan(run_id)
  └─ _do_thinking_scan(run_id)
       1. Load crawl data, prior findings, TargetIntelItems
       2. Authenticate → ScannerSession
       3. Seed PentestHypotheses + PentestTasks from intel
       4. Build compact crawl summary (context for LLM)
       5. Detect auth cookies for boundary checks
       └─ _do_agentic_thinking_loop(...)   ← main loop
```

### Agentic loop

Two execution modes depending on the configured LLM provider:

| Mode | Providers | Description |
|---|---|---|
| **Native tool-use** | Anthropic models | Single continuous session; the LLM natively calls tools via the Anthropic tool-use API. Produces tighter reasoning chains. |
| **Step-by-step** | All others | Each iteration sends the full conversation history; the LLM emits a JSON action; the harness executes it and appends the result. |

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
| `credential_check` | Test a login URL with candidate credentials |
| `finding_write` | Record a confirmed vulnerability |
| `tool` | Call a read-only context tool (see below) |
| `done` | Finish the scan with a summary |

### Context tools (read-only reconnaissance)

These can be called up to 3 consecutive times before the LLM must take a real action.

| Tool | Returns |
|---|---|
| `site_map` | Filtered list of crawled pages |
| `page_detail` | Full metadata, flags, text for a page |
| `history_search` | Query prior HTTP requests/responses by keyword |
| `finding_list` | Already-confirmed findings |
| `target_inventory` | Extracted endpoints, forms, inputs, IDs, scripts |
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

The LLM seeds hypotheses from the crawl intelligence and updates task statuses as it works.

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

Vision support (when `enable_vision=true`) attaches base64-encoded Playwright screenshots to prompts, giving the LLM visual context about what a page looks like.

---

## 10. Findings & Validation

**Files**: `src/aespa/services/findings.py`, `src/aespa/services/validator.py`

### Deduplication

After the scan, `findings.py` groups findings that are likely duplicates (same vulnerability on different parameter names, for example). The grouping is LLM-assisted: findings are compared by title, OWASP category, affected URL pattern, and evidence similarity. Duplicates are merged into the same heading (each instance is kept by URL/param.)

### Validation

Each finding starts with `validation_status = unvalidated`. The validator service (`validator.py`) can be invoked to re-run the probe and confirm the finding is reproducible. The LLM then rechecks the response:
- **confirmed** — vulnerability is reproducible and real
- **unconfirmed** — could not be reproduced
- **false_positive** — LLM determines finding was incorrect

External findings can be imported via `POST /api/test-runs/{run_id}/findings/import`.

---

## 11. API Layer

**Files**: `src/aespa/api/`

The API is a **FastAPI** application. All routes are async and use SQLModel sessions injected via `Depends`.

### Key route groups

| Prefix | Router | Responsibility |
|---|---|---|
| `/api/sites/` | `sites.py` | CRUD for target sites and credentials |
| `/api/settings/` | `settings.py` | Get/set LLM config and scanner policy |
| `/api/test-runs/` | `test_runs.py` | Create runs, check status, retrieve site map graph |
| `/api/test-runs/{id}/scan/` | `scan.py` | Start/stop/status for structured scan |
| `/api/test-runs/{id}/thinking-scan/` | `scan.py` | Start/stop/status for dynamic scan |
| `/api/test-runs/{id}/findings/` | `test_runs.py` | List, import, validate findings |
| `/api/traffic/` | `traffic.py` | Paginated HTTP traffic log |
| `/ws/events/{run_id}` | `events.py` | WebSocket event stream |

---

## 12. Frontend & Real-time Events

The web UI is a **single-page application** served from `src/aespa/web/`. It communicates with the backend over:
- **REST** for CRUD and control operations
- **WebSocket** (`/ws/events/{run_id}`) for real-time progress

### WebSocket event types (emitted by `services/events.py`)

Events are emitted at key points during crawling and scanning, enabling the UI to update live:

- Crawl progress (pages discovered, depth reached)
- Scan progress (page being probed, probe count)
- Thinking-scan step (action taken, tool called, finding written)
- Finding created / updated
- Task graph changes (hypothesis seeded, task status update)
- Error events

### UI panels

| Panel | Data shown |
|---|---|
| Activity log | Timestamped crawl/scan events |
| Site map | Interactive graph of `CrawledPage` nodes and `PageLink` edges |
| Intelligence log | `TargetIntelItems` — endpoints, forms, inputs, IDs |
| Task graph | `PentestHypothesis` tree with `PentestTask` leaves |
| Traffic log | All `TrafficEntry` records (request + response) |
| Findings | `ScanFinding` list sorted by severity, with CVSS and evidence |

---

## 13. Concurrency & State Management

- **FastAPI async handlers** — all I/O is non-blocking via `asyncio`
- **Parallel crawl workers** — multiple Playwright browser instances share a `_CrawlShared` state object (asyncio locks around the URL frontier and seen-set)
- **Background tasks** — crawl and scan jobs run as `asyncio.Task`s; handles are stored in-memory so the API can stop them
- **Database** — SQLite via SQLAlchemy sync sessions wrapped in `run_in_executor` where needed; all schema changes are applied at startup via `db.py`
- **Auth session vault** — `ScannerSession` rows in the DB store serialised cookies/tokens; `scanner_sessions.py` manages load/save/invalidation


