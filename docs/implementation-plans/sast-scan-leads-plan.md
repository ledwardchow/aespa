# SAST Scan → Scan Leads: Implementation Plan

> Historical plan: references below to `PentestHypothesis` describe a task-graph feature retired on 2026-07-15. `ScanLead` remains the active cross-run lead model.

**Status:** Implemented
**Date:** 2026-06-12
**Implemented:** 2026-06-12
**Scope:** Add **SAST as a first-class scan type** — an agentic static-analysis scan over uploaded source code that explores the codebase with read-only file tools, traces data flow from entry points to sinks, and produces *investigation leads*. Leads are kept strictly separate from validated scan findings; the dynamic API/web scanner later confirms them. SAST gets its own run model, start/stop/status lifecycle, live agent/progress UI, and a leads surface. **When an API scan starts on a collection that has uploaded source, a SAST run is auto-created and linked to that API scan as a pre-phase; the API scan then picks up the saved endpoints and the SAST leads to investigate.** SAST can also be launched standalone.

---

## 1. Goals & Constraints

1. **First-class SAST scan, auto-linked to dynamic scans.** SAST is its own scan type alongside the web scan and API scan — with a run record, background task lifecycle, live agent/progress UI, and stop/resume — not a hidden step inside document parsing. When an API scan starts on a collection with uploaded source, a SAST run is **auto-created and linked** to it and runs as a pre-phase so its leads are ready before dynamic testing begins. SAST can also be started standalone.
2. **Agentic exploration, not chunking.** The analyzer navigates the codebase on demand with read-only file tools (list/glob/read/grep), anchors on the entry points already extracted, and **traces data flow across files** from user input to sensitive sinks. (This mirrors how Anthropic's own `/security-review` works — see §3.)
3. **Low noise via two-stage triage.** Candidate vulnerabilities pass through a dedicated false-positive / confidence filter; only high-confidence candidates become leads.
4. **Guidance, not findings.** SAST output is a set of *unproven hypotheses* (`ScanLead`). The dynamic scanner must investigate and confirm them live; only confirmed issues become real `ScanFinding`s.
5. **No noise in findings.** SAST output must **never** appear in the findings list. It lives in its own data store and UI surface.
6. **Generalised.** Leads are run-type-agnostic so the web app scanner can produce and consume them later with minimal extra work.
7. **Non-blocking & isolated.** The SAST scan runs against a sandboxed extraction of the uploaded archive (read-only tools, path-jailed). Failures never affect document parsing or the dynamic scan.

---

## 2. Core Concept: `ScanLead`

A **lead** is an unproven "thing to investigate", produced by a SAST scan. It is distinct from a **finding** (`ScanFinding`), which is a validated, reportable vulnerability.

| | `ScanLead` (new) | `ScanFinding` (existing) |
|---|---|---|
| Meaning | Unproven hypothesis to investigate | Proven / reportable issue |
| Produced by | SAST scan (now); recon, manual (future) | Agent `write_finding` after dynamic proof |
| Shown in Findings UI | **No** | Yes |
| Lifecycle | open → investigating → confirmed / dismissed / inconclusive | unvalidated → validating → confirmed / unconfirmed / false_positive |
| Promotes to | a `ScanFinding` when confirmed | — |

> **Why not reuse `PentestHypothesis`?** That table is hard-FK-bound to `test_run.id` (web runs only) and is not currently fed into the agentic loop. A new, run-type-agnostic `ScanLead` table cleanly serves SAST, web, and API runs and keeps the concern isolated.

---

## 3. Methodology: how this mirrors Anthropic's security review

Anthropic's `/security-review` command and the open-source [claude-code-security-review](https://github.com/anthropics/claude-code-security-review) GitHub Action establish the proven approach. Key takeaways we adopt:

- **Agentic exploration with file tools, not token-chunking.** Claude is given `Read`, `Glob`, `Grep`, `LS` (and `Task` for sub-agents) and *navigates* the code. Fixed character chunks sever data-flow paths (handler → service → query layer live in different files) and can't follow imports — so we do not chunk.
- **Scoped to an anchor.** The action analyzes the **PR diff** and follows code paths outward. Our equivalent anchor is the **extracted entry points / routes** (and the most-relevant files): start at each handler, trace inward.
- **Explicit 3-step funnel:** (1) a sub-task identifies candidate vulnerabilities using exploration tools; (2) a *separate parallel sub-task per candidate* applies false-positive-filtering instructions; (3) **drop anything below a high confidence threshold** (they use ≥8/10). Their guidance: *"Better to miss some theoretical issues than flood the report with false positives."*
- **Read to triage; don't execute.** The SAST stage reads code to judge exploitability. aespa then goes one step further than Claude's review: **dynamic confirmation by the live scanner.**

Resulting three-stage funnel (stronger than static review alone):

```
static agentic triage (→ ScanLead, high-confidence only)
        → dynamic confirmation by the scanner (→ ScanFinding)
```

---

## 4. Architecture Overview

```
Upload source zip ──► (existing) route extraction ──► ApiEndpoint rows (entry points / anchors)
        │
        ▼
   User starts an API scan  ──►  ApiTestRun (status=running)
        │
        ├── (auto) source present & no fresh SAST run?  ──►  SastRun created
        │         (triggered_by_run_type="api", triggered_by_run_id=<ApiTestRun.id>)
        │         status=pending; linked back via ApiTestRun.sast_run_id
        │
        ▼
   PRE-PHASE: api_scanner awaits sast_scanner.run_sast_scan(sast_run_id)
        │   • extract archive to sandboxed temp dir (path-jailed, read-only)
        │   • agentic loop with file tools: list_files / glob / read_file / grep
        │   • anchored on extracted endpoints; trace data flow → sinks
        │   • write_lead (candidate) → filter_lead (FP/confidence) → keep high-confidence
        │   • emits events (agent_status / scanner_phase) + AgentLog rows  ──► live UI
        ▼
   ScanLead rows (producer_run_type="sast", source="sast", status="open", collection_id=…)
        │
        ▼
   API scan MAIN PHASE reads saved ApiEndpoints + OPEN leads for the collection
        │   → crawl_context: "Endpoints" block + "Investigation leads" block
        │   agent tests each endpoint and investigates each lead live; update_lead records outcome
        ▼
   Confirmed lead ──► write_finding ──► ScanFinding (normal validated flow)
```

Standalone SAST (no API scan) is identical except the run is user-created with no `triggered_by_run_*`, and leads are consumed by whichever dynamic run next targets the collection.

**Linkage.** The SAST run records *what triggered it* (`triggered_by_run_type` / `triggered_by_run_id`), and the API run records *its* SAST run (`ApiTestRun.sast_run_id`) so the UI can deep-link between them. Lead consumption is decoupled via `collection_id`: the API scan reads all OPEN leads for the collection (those its pre-phase produced, plus any from earlier SAST runs). A lead also carries `producer_run_id` (the SAST run that created it) and `investigated_by_run_id` (the dynamic run that picks it up).

---

## 5. Backend Changes

### 5.1 New model: `SastRun`
**File:** `src/aespa/models.py` (mirror `ApiTestRun`, ~L155)

```python
class SastRun(SQLModel, table=True):
    """A static-analysis scan over a source archive in an ApiCollection."""
    __tablename__ = "sast_run"

    id: Optional[int] = Field(default=None, primary_key=True)
    collection_id: int = Field(foreign_key="api_collection.id", index=True)
    document_id: Optional[int] = Field(default=None, index=True)  # the source_zip analyzed
    name: str
    status: str = Field(default="pending")  # pending|scanning|completed|failed|cancelled
    # what triggered this run: None=standalone, or the dynamic run that spawned it as a pre-phase
    triggered_by_run_type: Optional[str] = Field(default=None)   # "api" | "web"
    triggered_by_run_id: Optional[int] = Field(default=None, index=True)
    llm_config_id: Optional[int] = Field(default=None, foreign_key="llm_config.id")
    leads_count: int = Field(default=0)
    error_message: Optional[str] = Field(default=None)
    token_usage_json: Optional[str] = Field(default=None)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
```

Reciprocally, `ApiTestRun` gains a soft back-reference so the run pages deep-link to each other:

```python
# ApiTestRun (~L155): new nullable column
sast_run_id: Optional[int] = Field(default=None, index=True)  # the auto-linked SAST pre-phase run
```

### 5.2 New model: `ScanLead`
**File:** `src/aespa/models.py` (near `PentestHypothesis`, ~L542)

```python
class ScanLead(SQLModel, table=True):
    """An unproven investigation lead (from a SAST scan). Distinct from ScanFinding."""
    __tablename__ = "scan_lead"

    id: Optional[int] = Field(default=None, primary_key=True)
    collection_id: Optional[int] = Field(default=None, index=True)  # so dynamic runs on the collection can consume leads
    producer_run_type: str = Field(default="sast", index=True)      # "sast" (future: "recon")
    producer_run_id: int = Field(index=True)                        # SastRun.id that created it
    source: str = Field(default="sast", index=True)
    category: str = Field(default="")            # OWASP A0x / API0x (best-effort)
    severity: str = Field(default="medium")      # high | medium | low
    confidence: float = Field(default=0.0)       # 0..1 from the triage filter
    title: str = Field(default="")
    description: str = Field(default="")
    location: str = Field(default="")            # file:line / endpoint hint
    evidence: str = Field(default="")            # code snippet + data-flow note (from SAST)
    note: str = Field(default="")                # agent's investigation outcome note (update_lead)
    status: str = Field(default="open", index=True)  # open | investigating | confirmed | dismissed | inconclusive
    investigated_by_run_type: Optional[str] = Field(default=None)  # "api" | "web"
    investigated_by_run_id: Optional[int] = Field(default=None)
    linked_finding_id: Optional[int] = Field(default=None)  # set when promoted to a finding
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
```

`producer_run_id` / `investigated_by_run_id` are soft references (no DB FK) so the table serves SAST, API, and web runs uniformly.

### 5.3 Migration
**File:** `src/aespa/db.py`

- `SastRun` and `ScanLead` are new tables → created by SQLModel `create_all`. Confirm both models are imported so they register.
- One new column on an existing table: add `_ensure_column(engine, "api_test_run", "sast_run_id", "INTEGER")` in `_migrate()` (~L88) for the back-reference. No other column changes (SAST no longer caches onto `ApiDocument`).

### 5.4 SAST scanner service (the first-class scan)
**File (new):** `src/aespa/services/sast_scanner.py`

Mirrors `api_scanner.py`'s lifecycle (background task registry, status, stop):

```python
_sast_tasks: dict[int, asyncio.Task] = {}
_sast_stop_requested: set[int] = set()

async def start_sast_scan(sast_run_id: int) -> None:
    # register events, set status="scanning"+started_at, create_task(_sast_scan_task(...))

def get_sast_status(sast_run_id: int) -> dict:        # {"running": bool, "status": str}
async def stop_sast_scan(sast_run_id: int) -> bool:   # cancel task, status="cancelled"

async def _sast_scan_task(sast_run_id: int) -> None:
    # 1. load the source_zip document, extract via _safe_unzip into a sandboxed temp dir
    # 2. build entry-point anchors from extracted ApiEndpoint rows for the collection
    # 3. run the agentic exploration loop (see §5.5)
    # 4. persist surviving high-confidence candidates as ScanLead rows
    # 5. status="completed"+completed_at+leads_count; cleanup temp dir in finally
```

The archive is extracted to a unique temp dir and removed in a `finally`. File tools are path-jailed to that dir (resolve realpath, reject anything outside — defends against traversal in crafted archives, reinforcing `_safe_unzip`'s existing checks).

### 5.5 Agentic exploration loop + read-only file tools
**Reuses:** `llm.thinking_agentic_loop(...)` (`src/aespa/services/llm.py` ~L2803) — same engine the dynamic scanners use (`system_message`, `initial_user_message`, `tool_executor`, `emit_fn`, `stop_check`, `tools`).

**New tool set** (defined in `src/aespa/services/prompts/sast.py`, dispatched by a `tool_executor` closure in `sast_scanner.py`):

| Tool | Purpose |
|---|---|
| `list_files` | List files under a sub-path (jailed to the extraction root). |
| `glob` | Find files by pattern (e.g. `**/*.py`). |
| `read_file` | Read a file (optionally a line range); truncated to a char limit. |
| `grep` | Regex search across the tree; returns file:line matches. |
| `write_lead` | Record a **candidate** vulnerability (type, severity, file, line, data-flow description, suggested endpoint). |
| `filter_lead` | (or a post-pass) apply false-positive/confidence scoring to a candidate; drop < threshold. |
| `done` | Finish with a summary. |

Loop behaviour (the 3-step funnel from §3):
1. **Explore & generate candidates.** System prompt seeds the entry points (routes + their files). The agent reads handlers, follows imports/calls into services and query/auth layers, traces tainted data to sinks, and emits `write_lead` candidates with a concrete data-flow path.
2. **Filter.** Each candidate is evaluated against false-positive-filtering instructions and assigned a confidence (0..1). This can be a second sub-pass (a focused LLM call per candidate, optionally concurrent with a bounded semaphore) mirroring the action's parallel filter sub-tasks.
3. **Keep high-confidence only.** Persist candidates at/above the threshold (default ≈0.8) as `ScanLead`s; discard the rest.

`emit_fn` streams `agent_status` / `scanner_phase` events (file opened, candidate found, candidate filtered) so the UI shows live progress; `stop_check` consults `_sast_stop_requested`.

### 5.6 SAST prompts
**File (new):** `src/aespa/services/prompts/sast.py`

- `SAST_SYSTEM_PROMPT` — senior security engineer; methodology (Phase 1 context research, Phase 2 trace data flow from entry points to sinks, Phase 3 assess exploitability); the file-tool contract; explicit framing that outputs are hypotheses for later dynamic confirmation.
- `SAST_FALSE_POSITIVE_INSTRUCTIONS` — hard exclusions + confidence scoring, adapted from the security-review precedents (e.g. skip DOS/rate-limiting, theoretical races, client-side-only authz, framework-safe XSS; require a concrete attack path).
- `SAST_TOOLS` — the JSON tool schemas above.

### 5.7 Lead service
**File (new):** `src/aespa/services/scan_leads.py`

```python
def create_leads(producer_run_id: int, collection_id: int | None, leads: list[dict]) -> int: ...
def list_leads_for_run(producer_run_id: int) -> list[ScanLead]: ...           # for the SAST run UI
def get_open_leads_for_collection(collection_id: int) -> list[ScanLead]: ...   # for dynamic runs
def needs_fresh_sast(collection_id: int) -> bool:
    """True if the collection has source but no recent completed SastRun → auto-create one."""
def update_lead(lead_id: int, *, status: str, note: str = "",
                investigated_by_run_type: str | None = None,
                investigated_by_run_id: int | None = None,
                linked_finding_id: int | None = None) -> None: ...
def format_leads_for_context(collection_id: int, cap: int = 20) -> str:
    """Shared 'Investigation leads' block for the dynamic context builders. '' if none."""
```

`create_sast_run(...)` (creating the `SastRun` row, used by both the standalone route and the API-scan auto-create hook) lives in `sast_scanner.py` so the orchestration and lifecycle stay in one service.

### 5.8 Auto-create the SAST pre-phase & inject endpoints + leads into the dynamic scan
**File:** `src/aespa/services/api_scanner.py` — `start_api_scan()` / `_scan_task()` (~L1236).

**Auto-create + run as a pre-phase.** At the start of the API scan task, before the main agentic loop:

```python
# pseudo-flow inside the API scan task
coll = get_collection(api_run.collection_id)
if coll.has_source_zip and scan_leads.needs_fresh_sast(coll.id):   # no recent completed SAST run
    sast_run = create_sast_run(collection_id=coll.id, document_id=coll.source_zip_id,
                               triggered_by_run_type="api", triggered_by_run_id=api_run.id,
                               llm_config_id=api_run.llm_config_id, name=f"SAST for {api_run.name}")
    api_run.sast_run_id = sast_run.id; commit()
    emit(api_run.id, scanner_phase="Static analysis (SAST) pre-phase…")
    await sast_scanner.run_sast_scan(sast_run.id)   # awaited inline; its own events stream to the SAST run UI
```

- The SAST pre-phase **awaits to completion** so leads exist before dynamic testing. It is the *same* `run_sast_scan` used standalone; it emits to the **SAST run's** event stream/agent log (own Progress UI), while the API run emits a single `scanner_phase` marker so the API status tab shows "running SAST pre-phase".
- The pre-phase is **best-effort**: if SAST fails or is skipped (no source, or a fresh SAST run already exists), the API scan logs it and proceeds with endpoints only — it never blocks the dynamic scan.
- Respect stop/cancel: cancelling the API run also stops the in-flight SAST pre-phase.

**Consume saved endpoints + leads.** `_build_api_crawl_context()` (~L919) already emits the saved `ApiEndpoint` rows; after that block, append `scan_leads.format_leads_for_context(collection_id)`. Each formatted lead includes its `lead_id` so the agent can reference it via `update_lead`. The API scan therefore investigates **both** the extracted endpoints and the SAST leads tied to the collection.

(Web later: same auto-create hook in the web scan task + the one-line context addition in `_build_thinking_context_from_recon_summary`, `scanner.py` ~L711.)

### 5.9 `update_lead` agent tool (records investigation outcome)
**Files:** `src/aespa/services/prompts/test_lead.py` (schema in `THINKING_AGENT_TOOLS`); `src/aespa/services/scanner.py` (`_tool_executor`, ~L2711, near `write_finding`).

The dynamic agent calls this after investigating a lead, so a lead it *couldn't* confirm is explicitly marked rather than silently dropped.

```json
{
  "name": "update_lead",
  "description": "Record the outcome of investigating a static-analysis lead.",
  "input_schema": {
    "type": "object",
    "properties": {
      "lead_id":   {"type": "integer"},
      "outcome":   {"type": "string", "enum": ["confirmed", "dismissed", "inconclusive"]},
      "note":      {"type": "string", "description": "What was tested and what happened."},
      "finding_id":{"type": "integer", "description": "ScanFinding id raised, if outcome=confirmed."}
    },
    "required": ["lead_id", "outcome", "note"]
  }
}
```

Handler: map `outcome` → `ScanLead.status`; persist `note`, `updated_at`, `investigated_by_run_*`, and `linked_finding_id`; validate the lead belongs to the run's collection. Exposed in both API and web modes via a small `update_lead_fn` callback on `_do_agentic_thinking_loop` (mirrors the existing API-mode override callbacks). Agent instruction added to `_API_THINKING_AGENT_SYSTEM` (and `_THINKING_AGENT_SYSTEM` later): *"Investigation leads are UNPROVEN static-analysis hypotheses. Reproduce each against the live target. Only `write_finding` for leads you confirm with dynamic proof. After investigating each lead, call `update_lead` with the outcome and a short note."*

### 5.10 API routes
**File (new):** `src/aespa/api/sast_runs.py` (router mounted at `/api/sast-runs`), mirroring `api_test_runs.py`:

- `POST /api/api-collections/{collection_id}/sast-runs` (in `api_collections.py`) → create a `SastRun` (optional `document_id`, `llm_config_id`).
- `GET  /api/sast-runs/{run_id}` → run summary.
- `POST /api/sast-runs/{run_id}/scan/start` · `POST .../scan/stop` · `GET .../scan/status`.
- `GET  /api/sast-runs/{run_id}/events` → SSE stream (reuse `events_svc.stream`).
- `GET  /api/sast-runs/{run_id}/agent-log` (+ `/export`) → reuse `AgentLog` with a `run_kind="sast"` discriminator.
- `GET  /api/sast-runs/{run_id}/leads` → leads produced by this run.
- `DELETE /api/sast-runs/{run_id}`.
- `GET  /api/api-test-runs/{run_id}/leads` → collection leads for a dynamic API run (current status).

`events.py` gains `register_sast_run()` and `AgentLog`/`ScanLog` accept `run_kind="sast"`.

---

## 6. Frontend Changes

The web UI is a Preact/`htm` app in `src/aespa/web/app.js`. API helpers live in the `api` object; the API run detail view is `ApiTestRunDetail` with tabs in `API_RUN_TABS`.

### 6.1 Start a SAST scan + run navigation
- In the API collection detail / Files view (`ApiFilesManager`): SAST Scans section (visible only when a `source_zip` is present) with a **"Run SAST Scan"** button that creates + starts a `SastRun` then navigates to its detail page; table of prior SAST runs.
- New route: `#/sast-runs/{id}/{tab}` → `SastRunDetail` component.
- API helpers: `createSastRun`, `getSastRun`, `startSastScan`, `stopSastScan`, `getSastScanStatus`, `getSastAgentLog`, `getSastLeads`, `listSastRuns`, `getApiRunLeads`.

### 6.2 `SastRunDetail` component (live progress + leads)
Two tabs:
- **Progress** — SSE + agent-log polling (every 4s while running), same pattern as `ApiRunStatusTab`.
- **Leads** — `SastLeadsTab` renders leads from `getSastLeads(id)`; shared `LeadsPanel` component.

### 6.3 Scan Leads tab in the dynamic run detail view
- `{ key: "leads", label: "Scan Leads" }` added to `API_RUN_TABS`.
- `ApiRunLeadsTab` polls `getApiRunLeads(runId)` every 6s while scan is running.
- Shared `LeadsPanel` component renders leads grouped by status with confidence, location, evidence, and outcome note.

---

## 10. Implementation Progress

| # | Task | Status | File(s) |
|---|---|---|---|
| 1 | `SastRun` + `ScanLead` models; `ApiTestRun.sast_run_id` | ✅ Done | `models.py` |
| 2 | DB migration (new tables + column) | ✅ Done | `db.py` |
| 3 | SAST prompts (`SAST_SYSTEM_PROMPT`, `SAST_TOOLS`) | ✅ Done | `services/prompts/sast.py` |
| 4 | `scan_leads.py` service (CRUD, context formatting, `needs_fresh_sast`) | ✅ Done | `services/scan_leads.py` |
| 5 | `sast_scanner.py` service (lifecycle, agentic loop, path-jailed tools) | ✅ Done | `services/sast_scanner.py` |
| 6 | `events.py` — `register_sast_run`, `run_kind="sast"` discriminator | ✅ Done | `services/events.py` |
| 7 | `SastRunSummary` + `ScanLeadOut` schemas | ✅ Done | `schemas.py` |
| 8 | `sast_runs.py` API router; wired into `main.py` | ✅ Done | `api/sast_runs.py`, `main.py` |
| 9 | `api_scanner.py` — auto-create SAST pre-phase + leads in crawl context + stop propagation | ✅ Done | `services/api_scanner.py` |
| 10 | `test_lead.py` — `update_lead` tool schema; `scanner.py` — `update_lead` handler | ✅ Done | `services/prompts/test_lead.py`, `services/scanner.py` |
| 11 | Frontend: API helpers, routing, `SastRunDetail`, `ApiRunLeadsTab`, `LeadsPanel`, `ApiFilesManager` SAST section | ✅ Done | `web/app.js` |
- `DELETE /api/sast-runs/{run_id}`.

`events.py` gains `register_sast_run()` (mirrors `register_api_run`) and `AgentLog`/`ScanLog` accept `run_kind="sast"`.

---

## 6. Frontend Changes

The web UI is a Preact/`htm` app in `src/aespa/web/app.js`. API helpers live in the `api` object (~L20–160); the API run detail view is `ApiTestRunDetail` (~L2439) with tabs in `API_RUN_TABS` (~L2395); the live progress UI is `ApiRunStatusTab` (~L3067, SSE + agent-log polling).

### 6.1 Start a SAST scan + run navigation
- In the API collection detail / Files view, add a **"Run SAST scan"** action that creates a `SastRun` and navigates to its detail page (standalone use).
- New route in `parseHash`: `#/sast-runs/{id}/{tab}` → `SastRunDetail`. List SAST runs alongside test runs on the collection page.
- **Deep-link the auto-linked pair.** When an API run has a `sast_run_id`, `ApiTestRunDetail` shows a "Static analysis: SAST run #N" link (and its status) near the header; `SastRunDetail` shows "Triggered by API run #M" when `triggered_by_run_id` is set. The API status tab surfaces the "SAST pre-phase" marker while it runs.
- API helpers:
  ```js
  createSastRun:   (collId, body) => req(`/api/api-collections/${collId}/sast-runs`, { method:"POST", body }),
  getSastRun:      (id) => req(`/api/sast-runs/${id}`),
  startSastScan:   (id) => req(`/api/sast-runs/${id}/scan/start`, { method:"POST" }),
  stopSastScan:    (id) => req(`/api/sast-runs/${id}/scan/stop`,  { method:"POST" }),
  getSastStatus:   (id) => req(`/api/sast-runs/${id}/scan/status`),
  getSastAgentLog: (id) => req(`/api/sast-runs/${id}/agent-log`),
  getSastLeads:    (id) => req(`/api/sast-runs/${id}/leads`),
  ```

### 6.2 `SastRunDetail` view with live progress
**Component (new):** `SastRunDetail` — mirrors `ApiTestRunDetail` with a Start/Stop button driven by `getSastStatus` polling. Tabs:
- **Progress** — reuse the `ApiRunStatusTab` pattern (SSE `/api/sast-runs/{id}/events` for live `agent_status`; poll `getSastAgentLog` every ~4s while running) to show the agent exploring files, candidates found, and candidates filtered. This is the "agent UI" requested.
- **Leads** — render leads from `getSastLeads(id)` grouped by status/severity with confidence, `location`, data-flow `evidence`, and (once a dynamic run investigates them) the outcome `note` + a link to the linked `ScanFinding`. Banner: *"Leads are unproven static-analysis hypotheses confirmed later by a dynamic scan — not findings."*

### 6.3 Scan Leads tab in the dynamic run detail view
- Add `{ key: "leads", label: "Scan Leads" }` to `API_RUN_TABS` (~L2395) — a new top-level tab beside *Status*/*Findings* (placement confirmed).
- `getApiLeads: (id) => req(`/api/api-test-runs/${id}/leads`)` returns the collection's leads with their current investigation state; render with the same `ApiRunLeadsTab` component used in 6.2's Leads tab. A dynamic API run reads `get_open_leads_for_collection(collection_id)` at scan start to populate context.

---

## 7. Generalisation to the Web Scanner (enabled, not built here)

- `ScanLead` is already run-type-agnostic. A web `TestRun` consuming leads only needs a `get_open_leads_for_collection`-style lookup keyed to its target.
- The SAST scanner service is target-agnostic: point it at any extracted source tree (a future web-side upload or repo checkout).
- `scan_leads.format_leads_for_context(...)` drops into `_build_thinking_context_from_recon_summary` (`scanner.py` ~L711) identically; add `update_lead` to `_THINKING_AGENT_SYSTEM` and a `/api/test-runs/{id}/leads` alias.
- The `SastRunDetail` Progress/Leads components are reused unchanged.

---

## 8. Verification

1. Create a SAST run on a collection with a known-vulnerable zip → **Start** → the Progress tab shows the agent listing/reading files and emitting candidates live (SSE + agent log); run reaches `completed`.
2. High-confidence candidates appear as `ScanLead` rows (`status="open"`, with `confidence`, `location`, data-flow `evidence`); low-confidence candidates are filtered out (no flood). `ScanFinding` stays empty.
3. Stop mid-scan → task cancels, status `cancelled`, temp dir cleaned up.
4. **Auto-create:** start an API scan on a collection that has source and no fresh SAST run → a linked `SastRun` is created (`triggered_by_run_type="api"`, `ApiTestRun.sast_run_id` set), runs as an awaited pre-phase (visible in its own Progress tab and as a marker on the API status tab), then the API scan's `crawl_context` contains **both** the saved endpoints and the "Investigation leads" block; the agent calls `update_lead` recording `confirmed`/`dismissed`/`inconclusive`; a confirmed lead links to a real `ScanFinding`.
5. **Skip path:** an API scan on a collection with no source (or with a fresh SAST run already present) proceeds with endpoints only and never blocks; a failing SAST pre-phase is logged and the dynamic scan continues.
6. Leads never appear in the Findings tab — only in the Scan Leads / SAST Leads surfaces.
7. Crafted archive with `../` paths cannot escape the extraction root (file tools path-jailed; `_safe_unzip` checks hold).
8. SAST scan failure (LLM error) → run `failed` with `error_message`; document parsing and dynamic scans unaffected.
9. Tests: new `tests/test_sast_scanner.py` (lifecycle, path-jail, candidate→filter→lead funnel, non-blocking failure, **auto-create + await from the API scan**) + `tests/test_scan_leads.py` (CRUD, context formatting, update_lead, `needs_fresh_sast`) + extend `tests/test_api_scanner.py` (auto-create hook, endpoints + leads in context). `pytest` green; `tests/test_web_assets.py` covers UI assets.

---

## 9. Decisions & Resolved Questions

**Decisions**
- **SAST is a first-class scan type** (`SastRun`) with background-task lifecycle, start/stop/status, event streaming, agent log, and a live Progress + Leads UI — mirroring the API scan.
- **Auto-created & linked to the API scan.** Starting an API scan on a collection with source auto-creates a linked `SastRun` (`triggered_by_run_*` ↔ `ApiTestRun.sast_run_id`) and runs it as an awaited, best-effort pre-phase; the API scan then consumes the saved endpoints **and** the SAST leads. SAST can still be run standalone.
- **Agentic exploration with read-only, path-jailed file tools** (list/glob/read/grep), anchored on extracted entry points, tracing data flow across files — **not** character chunking (see §3).
- **Two-stage triage:** candidate generation → false-positive/confidence filter → keep only high-confidence (default ≈0.8). Explicitly biased toward fewer false positives.
- **Leads stored in a new generic `ScanLead` table**, fully separate from `ScanFinding` → no user noise; keyed to the collection so any dynamic run can consume them.
- **Dynamic confirmation** by the live scanner promotes a confirmed lead to a `ScanFinding`; the `update_lead` tool (v1) records every outcome.
- **Scan Leads tab placement confirmed:** new top-level tab beside *Status*/*Findings* in the dynamic run detail view, plus a Leads tab in the SAST run detail view.

**Resolved earlier questions**
1. **Does the strategy work / how does Claude do SAST?** Resolved in §3 — replaced chunking with the proven agentic-exploration + parallel FP-filter + confidence-threshold approach used by Anthropic's `/security-review`.
2. **Lead → finding linkage:** `update_lead` tool ships in v1 (§5.9); leads carry `investigated_by_run_*` and `linked_finding_id`.
3. **Tab placement:** confirmed (§6.3).
4. **Whole-codebase analysis:** the agent reads the actual application code (handlers, services, query/auth layers, sinks, config) by navigating with file tools — not just route-declaration lines.
5. **Trigger model:** resolved — an API scan auto-creates a linked SAST pre-phase (§5.8); standalone SAST is also supported. Auto-create on upload was rejected in favour of auto-create on scan start so a SAST run only happens when the user actually scans.

**Remaining considerations**
- **Cost/time ceiling:** bound the agentic loop with a max-step budget and (optionally) a max-candidates cap; surface elapsed/step count in the Progress UI. Large monorepos analyze the prioritized entry-point neighborhood first within the budget.
- **Prompt-injection caution:** uploaded source is untrusted input fed to the LLM with tool access. Tools are read-only and path-jailed; the system prompt should instruct the agent to treat file contents as data, not instructions. (Anthropic's action carries the same caveat.)
