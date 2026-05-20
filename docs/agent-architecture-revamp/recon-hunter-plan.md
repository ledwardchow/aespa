# Specialist Agents, Adversarial Validator + Agents UI

## Progress

| Phase | Description | Status |
|---|---|---|
| 0 | Baseline metrics | **DONE** |
| 1 | Recon output contract | TODO |
| 2 | Specialist (hunter) agents | TODO |
| 3 | Adversarial validator | TODO |
| 4 | Agents UI | **DONE** |
| 5 | Role-specific LLM profiles *(optional)* | TODO |
| 6 | Rollout | TODO |

---

## Background

The [Cloudflare Project Glasswing post](https://blog.cloudflare.com/cyber-frontier-models/)
describes a multi-stage vulnerability-discovery harness. The two insights most applicable
to AESPA are:

1. **Adversarial validation** — *"putting two agents in deliberate disagreement is way more
   effective than telling one agent to be careful."* An independent agent that actively tries
   to disprove a finding eliminates far more noise than having the same agent double-check
   its own work.

2. **Specialist depth on confirmed leads** — when something interesting is found, narrow
   scope and focused context produce better follow-up than asking one broad agent to do
   everything. This is structurally identical to how Burp active scans are dispatched today.

The full parallel-hunter architecture (concurrent narrow workers, task claim/lease, global
rate semaphore, multi-worker checkpointing) was evaluated and rejected for this project.
AESPA scans one target at a time; the engineering cost of that architecture solves a
throughput problem AESPA does not have, and introduces four hard prerequisites before
multi-worker runs would be reliable. See the *Rejected: Parallel Hunter Architecture*
section at the bottom for the analysis.

### Architecture

```
Crawl  (recon output contract → attack-surface summary + PentestTask queue)
  └── Thinking scan  (unchanged — single agent, full context, unbounded steps)
        │
        ├── On interesting lead ——→  Specialist Agent
        │                            (narrow scope, inherits session vault,
        │                             short-lived, like Burp active scan dispatch)
        │
        └── On finding written ——→  Adversarial Validator Agent
                                     (mandate to disprove, different model/prompt,
                                      cannot create new findings)

Burp active scans  (existing dispatch, now surfaced in Agents UI)
```

All four agent types — Scanner, Specialist, Burp, Validator — emit `agent_status` SSE
events and appear as rows in the new Agents UI tab.

---

## Phases

### Phase 0 — Baseline `[DONE]`
1. Record baseline metrics (findings/run, confirmed-rate, false-positive-rate,
   duplicate-rate, time-to-confirmation) from existing run artifacts before any changes.

   **Status:** Complete. See [`docs/phase0-baseline.md`](phase0-baseline.md).

   Key numbers from two Bank of Ed runs (pre-improvement):

   | Metric | Run 1 (05-16) | Run 2 (05-18) | Combined |
   |---|---|---|---|
   | Findings/run | 60 | 35 | 47.5 avg |
   | Confirmed rate | 15.0% | 28.6% | — |
   | False-positive rate | 0.0% | 0.0% | 0% (no FP verdicts recorded) |
   | Low-confidence rate | 1.7% | 25.7% | — |
   | Still-unresolved | 83.3% | 45.7% | 67.1% combined |
   | Within-run duplicate titles | 37 | 15 | — |
   | Cross-run repeat rate | — | — | 7.5% |
   | Unique vulnerabilities (combined) | — | — | 40 |

   Time-to-confirmation is not measurable from export artifacts — no `confirmed_at`
   timestamp exists. Needs a DB migration to track in future runs.

### Phase 1 — Recon output contract `[TODO]`

**Goal:** The thinking scan currently opens with an ad-hoc compact context string built
from raw crawl data (`_build_compact_thinking_context` + `_build_target_intelligence_context`
in `scanner.py`). Replace this with a structured, persisted **attack-surface summary** that
gives the scanner — and later the Specialist agents — a reasoned picture of the target
before the first LLM turn.

#### 1a. What to produce

`seed_task_graph()` in `task_graph.py` already generates the *work queue* (prioritised
`PentestTask` records). Phase 1 adds a companion function `build_recon_summary(run_id)`
that produces a **`ReconSummary`** — a structured document describing the attack surface.
These two functions are called together at the same point in `_do_thinking_scan`:

```
Crawl completes
  └── task_graph.build_recon_summary(run_id)   ← NEW  stores to TestRun.recon_summary
  └── task_graph.seed_task_graph(run_id)       ← EXISTING  populates PentestTask queue
  └── scanner opens thinking-scan LLM with recon_summary as opening context  ← CHANGED
```

#### 1b. Where does the user see the summary?

The UI already has seven tabs: **Status · Site Map · Intelligence · Tasks · Sessions · Findings · Traffic**.
The **Tasks** tab currently shows `PentestHypothesis` and `PentestTask` records from
`seed_task_graph()`. The recon summary belongs here — it is the higher-level picture that
those tasks are derived from.

**Decision: add a two-sub-tab bar to the Tasks tab — "Attack Surface" (summary) and
"Task Queue" (existing hypotheses + tasks, unchanged).**

This co-locates the "why" (attack surface analysis) with the "what has been done" (task
progress), reuses the established sub-tab pattern already present in the Activity tab, and
does not add an eighth top-level tab.

The Attack Surface panel renders the `ReconSummary` JSON as three collapsible sections:

```
▸ Trust zones       PUBLIC (3)  USER (12)  ADMIN (8)
▾ Attack classes    [P10] Auth bypass  [P9] IDOR  [P8] SQLi  [P7] XSS ...
    [P10] auth_bypass — JWT secret exposed at /api/health (unauthenticated)
          Entry points: /api/health, /api/auth/login
    ...
▸ Tech stack / credentials
```

It is populated on mount via a new `GET /api/test-runs/{id}/recon-summary` endpoint and
requires no SSE — it is static after the crawl completes.

#### 1c. Does the recon summary make the task graph redundant?

**No, but it clarifies the division of labour.**

| | Recon summary | Task graph |
|---|---|---|
| Type | Immutable document — written once at crawl completion | Mutable work queue |
| Consumed by | LLM opening context; Attack Surface UI panel; Specialist agent briefing | `build_task_graph_context` (LLM mid-scan); Task Queue UI panel |
| Updated during scan | Never | Continuously — task statuses change as the LLM works |
| Granularity | Attack-surface categories (trust zones, attack classes) | Individual testable actions (one per URL/param pair) |
| Tracks "what has been done" | No | Yes |

The task graph adds two things the summary cannot: **runtime progress tracking** (which
tasks are queued/running/complete) and **mid-scan LLM guidance** (`build_task_graph_context`
is re-injected during the agentic loop to keep the scanner on track). These are genuinely
different from the static attack surface picture.

**However**, the `PentestHypothesis` layer is now largely a duplication of `attack_classes`
in the summary. For Phase 1 keep both, with `seed_task_graph()` deriving hypotheses
directly from the summary's `attack_classes` rather than re-deriving them independently.
The option to eliminate `PentestHypothesis` and link `PentestTask` directly to
`attack_class` strings in the summary is noted as a simplification to revisit after Phase 1
is proven — it is not in scope here.

The summary **influences** how the task graph is seeded (the `attack_classes` it identifies
become `PentestHypothesis.attack_area` and `owasp_category`), but it is not itself a node
in the queue. Mixing them would conflate "what the target looks like" with "what to test next".

#### 1c. `ReconSummary` schema

Persisted as a JSON blob in a new `recon_summary` TEXT column on `TestRun`.

```json
{
  "trust_zones": {
    "public":            ["/api/health", "/banking/", ...],
    "authenticated_user": ["/api/profile", "/api/accounts", ...],
    "admin":             ["/api/admin/customers", "/api/admin/system/reset", ...]
  },
  "entry_points": [
    {"url": "/api/auth/login",     "method": "POST",  "params": ["email", "password"]},
    {"url": "/api/admin/customers","method": "GET",   "params": ["search"]},
    ...
  ],
  "attack_classes": [
    {
      "class":       "idor",
      "rationale":   "Object-reference IDs in /api/transfers/external (from_account_id), /api/transactions/{id}",
      "priority":    9,
      "entry_points": ["/api/transfers/external", "/api/transactions/{id}"]
    },
    {
      "class":       "auth_bypass",
      "rationale":   "JWT issued by /api/auth/login; /api/health exposes jwt_secret unauthenticated",
      "priority":    10,
      "entry_points": ["/api/health", "/api/auth/login"]
    },
    ...
  ],
  "business_logic_pages": ["/api/transfers/external", "/api/fx/rates", "/api/transfers/check"],
  "tech_stack": {"server": "Apache/2.4.58", "language": "PHP 8.3", "db": "MySQL"},
  "credential_roles": [
    {"role": "user",  "source": "registration", "count": 1},
    {"role": "admin", "source": "login_endpoint", "count": 1}
  ]
}
```

`attack_classes` values are drawn from a fixed vocabulary aligned with WSTG skill keys so
they can be directly cross-referenced: `idor`, `auth_bypass`, `sqli`, `xss`, `business_logic`,
`ssrf`, `path_traversal`, `cors`, `crypto`, `config`.

#### 1d. How the task graph is seeded from it

`seed_task_graph()` is called *after* `build_recon_summary()` and accepts the summary as
an optional argument. Each `attack_class` entry maps to one or more `PentestHypothesis`
records, with `attack_area` = the class string and `rationale` drawn from the summary's
`rationale` field. This replaces the current purely heuristic hypothesis generation.

The `entry_points` list in each attack class seeds `PentestTask` records, replacing
ad-hoc `TaskSeed` generation in `_build_seed_specs()`. The task graph output doesn't
change shape — only the *quality* of hypotheses and tasks improves.

#### 1e. Thinking scan context change

In `_do_thinking_scan` (scanner.py lines ~2707–2714), replace:

```python
crawl_context = _build_compact_thinking_context(base_url, pages_snapshot, findings_snapshot)
intel_context = _build_target_intelligence_context(run_id)
if intel_context:
    crawl_context = f"{crawl_context}\n\n{intel_context}"
```

with:

```python
crawl_context = _build_thinking_context_from_recon_summary(run_id, base_url, findings_snapshot)
```

`_build_thinking_context_from_recon_summary` reads `TestRun.recon_summary` if present and
renders it as a structured LLM prompt block. If `recon_summary` is absent (old runs,
in-progress resumes), it falls back to the existing `_build_compact_thinking_context` path —
no regression on existing runs.

The rendered context prioritises **attack classes** and **trust zones** over the raw
page-count summary the current function produces, giving the scanner an analyst-quality
briefing rather than a stat dump:

```
Target: http://192.168.3.101  (Apache/2.4.58, PHP 8.3, MySQL)

Trust zones:
  PUBLIC (no auth): /api/health, /banking/, /admin/ — note: health endpoint exposes jwt_secret
  USER (JWT): /api/profile, /api/accounts, /api/transfers/*, /api/transactions/*
  ADMIN (separate JWT, iss=BankOfEdAdmin): /api/admin/*

High-priority attack classes:
  [P10] auth_bypass — JWT issued by /api/auth/login; /api/health exposes jwt_secret unauthenticated
  [P9]  idor        — Object-reference IDs in /api/transfers/external, /api/transactions/{id}
  [P8]  sqli        — Search parameter at /api/admin/customers; sort param at /api/transactions
  ...

Business logic pages: /api/transfers/external, /api/fx/rates, /api/transfers/check

Use context tools for full endpoint details.
```

#### 1f. Implementation steps

1. **DB migration**: add `recon_summary: str | None = None` (TEXT) to `TestRun` in `models.py`.
2. **`task_graph.py`**: add `build_recon_summary(run_id, pages, intel_items) -> dict`.
   - Derives trust zones from `CrawledPage.requires_auth` + URL-pattern heuristics.
   - Derives entry points from `CrawledPage.takes_input == True` + `TargetIntelItem` records.
   - Derives `attack_classes` from heuristic rules (same logic currently scattered across
     `_build_seed_specs`; consolidate here).
   - Persists JSON blob to `TestRun.recon_summary`.
3. **`task_graph.py`**: update `seed_task_graph()` to accept `summary: dict | None = None`;
   derive hypotheses from `summary["attack_classes"]` instead of re-running independent
   heuristics. Fall back to current logic if summary absent (backward-compat for old runs).
4. **`scanner.py`**: add `_build_thinking_context_from_recon_summary(run_id, base_url, findings_snapshot)`.
   Reads `TestRun.recon_summary` if present; falls back to `_build_compact_thinking_context`
   if absent — no regression on existing runs.
5. **`scanner.py`**: in `_do_thinking_scan`, call `build_recon_summary()` then `seed_task_graph(summary=...)`,
   then use the new context builder.
6. **`api/test_runs.py`** (or `api/scan.py`): add `GET /api/test-runs/{id}/recon-summary`
   endpoint returning `TestRun.recon_summary` (parsed JSON, or 404 if absent).
7. **`app.js`**: Tasks tab gets a sub-tab bar — "Attack Surface" (new) and "Task Queue"
   (existing content, unchanged). Attack Surface panel fetches from the new endpoint on mount
   and renders trust zones, attack classes, and tech stack. No SSE required.
8. **Unit tests**: `build_recon_summary` produces correct trust zones and attack classes for
   a Bank of Ed-style page set; `_build_thinking_context_from_recon_summary` falls back
   correctly when summary absent; `seed_task_graph` driven by summary produces expected
   hypothesis `attack_area` values.

### Phase 2 — Specialist agents *(bolt-on, Burp-style)* `[TODO]`
3. *Depends on 1.* When the thinking scan encounters a strong lead (e.g. a suspicious
   parameter, anomalous response, confirmed primitive that warrants deeper investigation),
   it can dispatch a **Specialist Agent** — a short-lived, narrow-scope LLM session focused
   on that specific lead.

   Dispatch mechanism mirrors the existing Burp active scan path in `burp_rest.py`:
   - Thinking scan writes an `agent_dispatch` action (alongside the existing `http`,
     `browser`, `done` action types).
   - `scanner.py` spawns the specialist as a background `asyncio.Task` on the same run.
   - Specialist inherits the `ScannerSession` vault (no extra auth bootstrap).
   - Specialist writes findings back to `ScanFinding` with `finding_source =
     "specialist_agent"`.
   - Thinking scan continues; specialist result is visible via context tools on the next
     LLM turn.

   Specialist agents are always sequential within a run (one at a time, like Burp scans),
   so no concurrent session, rate-limit, or DB contention problems arise.

### Phase 3 — Adversarial validator `[TODO]`
4. Rework `src/aespa/services/validator.py` from a probe-generation-and-check model into
   a proper adversarial agent.

   **Current behaviour:** LLM generates targeted probes → execute → LLM reviews results
   → verdict.

   **New behaviour:** An independent LLM agent receives the finding + all evidence and is
   given an explicit mandate to *disprove* it. It has access to a subset of the thinking
   scan's context tools (site_map, page_detail, history_search, compare_responses,
   traffic_search) and can issue HTTP requests. It produces a verdict only when it either:
   (a) successfully demonstrates the finding is a false positive, or (b) exhausts its
   attempt budget without being able to refute it (in which case it confirms).

   Key constraints enforced structurally:
   - The validator's output handler only permits writing to `validation_status` and
     `validation_note`. It cannot call any code path that creates a `ScanFinding`.
   - A different system prompt and (optionally) a different model from the main scanner.
   - The validator's LLM conversation is fresh per finding — it has no knowledge of other
     findings, so it cannot be biased by patterns from the main scan.

### Phase 4 — Agents UI `[DONE]`
5. ~~*Depends on 2, 3.*~~ Add `agent_status` SSE events across all agent types and build the
   Agents sub-tab in the Activity panel.

   **Status:** Fully implemented ahead of Phases 2 and 3. All sub-items below are complete.

#### 5a. Backend — `agent_status` SSE events `[DONE]`

Emit from `crawler.py`, `scanner.py`, `validator.py`, and `burp_rest.py`. All flow
through the existing `events.emit()` / `events.stream()` path unchanged.

Event shape:
```json
{
  "type": "agent_status",
  "agent_id": "validator-42",
  "role": "Validator",
  "status": "active",
  "current_task": "Trying to disprove: Stored XSS in /comments",
  "outcome": null
}
```

| `role` value | When emitted | `agent_id` format |
|---|---|---|
| `"Scanner"` | Thinking scan start / step updates / complete | `"scanner"` |
| `"Specialist"` | Each specialist agent dispatch | `"specialist-{attack_class}"` e.g. `"specialist-jwt-forgery"` |
| `"Burp"` | Each Burp active scan start / completion (from `burp_rest.py` poll loop) | `"burp-{url_slug}"` |
| `"Validator"` | Each finding validation start / verdict | `"validator-{finding_id}"` |

`outcome` is populated on `status: "complete"` — e.g. `"Confirmed"`, `"False positive"`,
`"2 new findings"`.

Agent history is persisted to a new `AgentLog` DB table (analogous to `ScanLog`) so the
Agents list survives page refreshes. An `/api/test-runs/{id}/agent-log` endpoint hydrates
it on mount.

#### 5b. Frontend — Activity sub-tab bar `[DONE]`

When `activeTab === "activity"` (around `app.js` line 3634), render a
`.activity-sub-tab-bar` with two buttons: **Log** (existing content, unchanged) and
**Agents**. Add `activitySubTab` state (default `"log"`). URL routing
(`#/runs/{id}/activity`) is unchanged.

#### 5c. Frontend — Agents panel state `[DONE]`

- `agents`: array of `{id, role, status, currentTask, taskHistory: [{ts, task, outcome}]}`
- `expandedAgentIds`: Set
- SSE handler for `agent_status` (near `app.js` line 2818): upserts into `agents` by
  `agent_id`, appending each event as a new `taskHistory` entry.
- On mount: hydrate `agents` from `/api/test-runs/{id}/agent-log`.

#### 5d. Frontend — Agents panel render `[DONE]`

Active agents appear before complete agents (CSS `order: 0` vs `order: 1` on a flex
column). On `active → complete`, badge swaps, animation removed, row reflows to bottom.

```
● Scanner        [ACTIVE  ]  Step 47: Testing IDOR on /api/orders/{id}
● Specialist:    [ACTIVE  ]  Probing JWT forgery variants on /api/auth
  JWT Forgery
● Validator:     [ACTIVE  ]  Trying to disprove: Stored XSS in /comments
  Stored XSS
────────────────────────────────────────────────────────────────────────────
  Burp:          [COMPLETE]  Active scan: /api/search — 3 issues
  /api/search
  Validator:     [COMPLETE]  Confirmed: IDOR in /api/orders/{id}
  IDOR orders
  Specialist:    [COMPLETE]  No additional issues found
  SQLi /login
```

Expanded row (click to toggle):
```
● Validator:     [ACTIVE  ]  Trying to disprove: Stored XSS in /comments  ▼
  Stored XSS
  14:03:01  Received finding — evidence: 2 request/response pairs
  14:03:04  Fetched /comments as anonymous user — XSS payload absent
  14:03:09  Re-submitted payload with content-type variation — reflected
  14:03:14  Cannot disprove — marking confirmed  ← current
```

#### 5e. Frontend — CSS additions `[DONE]`

After existing `.activity-*` rules (~`styles.css` line 1089):

| Class | Purpose |
|---|---|
| `.activity-sub-tab-bar` | Second-level tab bar container |
| `.activity-sub-tab-btn[.active]` | Sub-tab button + active underline state |
| `.agents-panel` | Panel container (flex column) |
| `.agent-row[--active\|--complete]` | Individual agent row with modifier states |
| `.agent-role-name` | Role text; `@keyframes pulse-opacity` (opacity 1→0.5→1, 0.9s ease-in-out infinite) via `--active` modifier only |
| `.agent-badge-active` | Pulsing accent badge |
| `.agent-badge-complete` | Static `var(--text-2)` badge |
| `.agent-current-task` | Inline task description |
| `.agent-task-history` | Expanded history container |
| `.agent-history-entry` | Single timestamped history row |

### Phase 5 — Role-specific LLM profiles *(optional)* `[TODO]`
6. *Depends on 3.* Add optional separate model/prompt settings for Scanner, Specialist,
   and Validator roles, while preserving the current single-config default. Cheaper/faster
   model for specialists on well-defined leads; conservative model for the validator.
   Implemented as a new `AgentRoleConfig` join table or extended `LLMConfig`.

### Phase 6 — Rollout `[TODO]`
7. *Depends on 1–6.* Canary on selected runs; compare metrics against Phase 0 baseline.

---

## Relevant Files

| File | Changes | Status |
|---|---|---|
| `src/aespa/services/crawler.py` | Emit `agent_status` at crawl start/complete | DONE |
| `src/aespa/services/task_graph.py` | Add `build_recon_summary()`; update `seed_task_graph()` to accept summary and drive hypothesis generation from it | TODO |
| `src/aespa/services/scanner.py` | Add `_build_thinking_context_from_recon_summary()`; update `_do_thinking_scan`; add `agent_dispatch` action type; spawn specialist agents; emit `agent_status` per step | Partial — `agent_status` done; recon context + `agent_dispatch` TODO |
| `src/aespa/services/validator.py` | Full rework as adversarial agent; emit `agent_status` | Partial — `agent_status` done; adversarial rework TODO |
| `src/aespa/services/burp_rest.py` | Emit `agent_status` on scan start and on each poll completion | DONE |
| `src/aespa/services/findings.py` | Tag `finding_source = "specialist_agent"` | TODO |
| `src/aespa/services/events.py` | No changes — `agent_status` uses existing `emit()`/`stream()` | DONE |
| `src/aespa/api/test_runs.py` | Add `GET /recon-summary` endpoint; add `/agent-log` endpoint | Partial — `/agent-log` done; `/recon-summary` TODO |
| `src/aespa/models.py` | Add `recon_summary` column to `TestRun`; add `AgentLog` table; optional `AgentRoleConfig` | Partial — `AgentLog` done; `recon_summary` + `AgentRoleConfig` TODO |
| `src/aespa/web/app.js` | Tasks tab: add "Attack Surface" / "Task Queue" sub-tab bar; Attack Surface panel; sub-tab bar; agents state; SSE handler; agents panel render | Partial — agents panel done; Tasks sub-tabs TODO |
| `src/aespa/web/styles.css` | Attack Surface panel CSS; agents panel and sub-tab bar CSS | Partial — agents CSS done; attack surface CSS TODO |

---

## Verification

1. **Regression tests:** existing crawl, structured scan, and thinking scan behaviour
   unchanged — specialist dispatch and adversarial validator are additive.
2. **Unit tests:** adversarial validator cannot write `ScanFinding` records; specialist
   agent inherits session vault correctly.
3. **Integration tests:** specialist dispatch from thinking scan action; Burp `agent_status`
   events emitted on scan start and poll completion.
4. **UI tests:** Agents tab renders with zero agents, active agents, and after all complete;
   all four role types appear correctly; pulsing animation on active rows only; task history
   expands on click; list persists after page refresh.
5. **Benchmark runs:** confirmed-rate, false-positive-rate, and duplicate-rate vs. Phase 0
   baseline — primary target is false-positive-rate reduction from the adversarial validator.
6. **Manual replay:** verify adversarial validator marks a known false positive correctly;
   verify specialist agent surfaces a deeper finding on a confirmed lead.

---

## Decisions

- **Included:** recon output contract, specialist agent dispatch (bolt-on, Burp-style),
  adversarial validator, Agents UI with persistent agent history for all four agent types.
- **Excluded:** parallel hunter workers, task claim/lease, global rate semaphore,
  multi-worker checkpoint redesign — see *Rejected* section below.
- **Specialist agents run sequentially** (one at a time per run), matching the existing
  Burp active scan pattern. No concurrent session, rate-limit, or DB contention problems.
- **Adversarial validator** is structurally prohibited from creating findings; it receives
  a fresh LLM conversation per finding with no knowledge of other findings.
- **Burp active scans** gain `agent_status` visibility in the Agents UI with no change
  to their dispatch logic — only `burp_rest.py`'s poll loop gains `events.emit()` calls.
- **`agent_status` SSE** reuses existing `events.emit()` / `events.stream()` — no new
  transport infrastructure.
- **URL routing:** sub-tab bar is inside the `activity` block; `#/runs/{id}/activity`
  URL is unchanged.

---

## Rejected: Parallel Hunter Architecture

A full recon-hunter architecture with concurrent narrow workers was evaluated against the
Cloudflare model and rejected for this project. The analysis identified four hard
prerequisites that must be in place before multi-worker runs are reliable:

1. **Shared auth session vault + re-auth coordination** — each worker bootstrapping auth
   independently creates N Playwright login flows per credential, and a session expiry in
   one worker is invisible to others (they silently receive 401s that look like no finding).
2. **Global request rate semaphore** — `sleep_between_probes()` is per-worker; 5 concurrent
   workers × the same `min_delay` means 5× the aggregate request rate against the target,
   which reliably trips WAF / rate-limit thresholds and silences all workers at once.
3. **Atomic task claim with `BEGIN IMMEDIATE`** — the `PentestTask` claim/lease pattern
   is a read-then-write race condition on the current SQLModel session pattern; two workers
   can both read `claimed_by IS NULL` and both claim the same task.
4. **Per-worker checkpoint rows** — `ScanCheckpoint` has one row per `run_id`; a
   multi-worker resume would silently drop all but one worker's LLM conversation state.

Beyond the prerequisites, a pure narrow-hunter model also threatens business logic
coverage: `_do_thinking_scan()` relies on unified cross-endpoint context, the WSTG
`workflow` skill injected across the whole session, and confirmed findings fed back as
stepping stones — all of which are broken when context is siloed by attack class.

The engineering cost of these prerequisites solves a throughput problem AESPA does not
have (it scans one target at a time). The specialist-agent approach delivers the
highest-value Cloudflare insights (adversarial validation, specialist depth on leads)
without any of these costs.