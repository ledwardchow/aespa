# Specialist Agents, Adversarial Validator + Agents UI

## Background

The [Cloudflare Project Glasswing post](https://blog.cloudflare.com/cyber-frontier-models/)
describes a multi-stage vulnerability-discovery harness. The two insights most applicable
to AESPA are:

1. **Adversarial validation** â€” *"putting two agents in deliberate disagreement is way more
   effective than telling one agent to be careful."* An independent agent that actively tries
   to disprove a finding eliminates far more noise than having the same agent double-check
   its own work.

2. **Specialist depth on confirmed leads** â€” when something interesting is found, narrow
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
Crawl  (recon output contract â†’ attack-surface summary + PentestTask queue)
  â””â”€â”€ Thinking scan  (unchanged â€” single agent, full context, unbounded steps)
        â”‚
        â”œâ”€â”€ On interesting lead â”€â”€â†’  Specialist Agent
        â”‚                            (narrow scope, inherits session vault,
        â”‚                             short-lived, like Burp active scan dispatch)
        â”‚
        â””â”€â”€ On finding written â”€â”€â†’  Adversarial Validator Agent
                                     (mandate to disprove, different model/prompt,
                                      cannot create new findings)

Burp active scans  (existing dispatch, now surfaced in Agents UI)
```

All four agent types â€” Scanner, Specialist, Burp, Validator â€” emit `agent_status` SSE
events and appear as rows in the new Agents UI tab.

---

## Phases

### Phase 0 â€“ Baseline
1. Record baseline metrics (findings/run, confirmed-rate, false-positive-rate,
   duplicate-rate, time-to-confirmation) from existing run artifacts before any changes.

### Phase 1 â€“ Recon output contract
2. Formalise what `seed_task_graph()` in `src/aespa/services/task_graph.py` produces:
   a structured attack-surface summary (trust boundaries, entry points, interesting attack
   classes, `has_business_logic` pages called out explicitly) alongside the existing
   prioritised `PentestTask` queue. This summary becomes the thinking scan's opening
   context, replacing the current ad-hoc compact context build.

### Phase 2 â€“ Specialist agents *(bolt-on, Burp-style)*
3. *Depends on 1.* When the thinking scan encounters a strong lead (e.g. a suspicious
   parameter, anomalous response, confirmed primitive that warrants deeper investigation),
   it can dispatch a **Specialist Agent** â€” a short-lived, narrow-scope LLM session focused
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

### Phase 3 â€“ Adversarial validator
4. Rework `src/aespa/services/validator.py` from a probe-generation-and-check model into
   a proper adversarial agent.

   **Current behaviour:** LLM generates targeted probes â†’ execute â†’ LLM reviews results
   â†’ verdict.

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
   - The validator's LLM conversation is fresh per finding â€” it has no knowledge of other
     findings, so it cannot be biased by patterns from the main scan.

### Phase 4 â€“ Agents UI
5. *Depends on 2, 3.* Add `agent_status` SSE events across all agent types and build the
   Agents sub-tab in the Activity panel.

#### 5a. Backend â€” `agent_status` SSE events

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

`outcome` is populated on `status: "complete"` â€” e.g. `"Confirmed"`, `"False positive"`,
`"2 new findings"`.

Agent history is persisted to a new `AgentLog` DB table (analogous to `ScanLog`) so the
Agents list survives page refreshes. An `/api/test-runs/{id}/agent-log` endpoint hydrates
it on mount.

#### 5b. Frontend â€” Activity sub-tab bar

When `activeTab === "activity"` (around `app.js` line 3634), render a
`.activity-sub-tab-bar` with two buttons: **Log** (existing content, unchanged) and
**Agents**. Add `activitySubTab` state (default `"log"`). URL routing
(`#/runs/{id}/activity`) is unchanged.

#### 5c. Frontend â€” Agents panel state

- `agents`: array of `{id, role, status, currentTask, taskHistory: [{ts, task, outcome}]}`
- `expandedAgentIds`: Set
- SSE handler for `agent_status` (near `app.js` line 2818): upserts into `agents` by
  `agent_id`, appending each event as a new `taskHistory` entry.
- On mount: hydrate `agents` from `/api/test-runs/{id}/agent-log`.

#### 5d. Frontend â€” Agents panel render

Active agents appear before complete agents (CSS `order: 0` vs `order: 1` on a flex
column). On `active â†’ complete`, badge swaps, animation removed, row reflows to bottom.

```
â— Scanner        [ACTIVE  ]  Step 47: Testing IDOR on /api/orders/{id}
â— Specialist:    [ACTIVE  ]  Probing JWT forgery variants on /api/auth
  JWT Forgery
â— Validator:     [ACTIVE  ]  Trying to disprove: Stored XSS in /comments
  Stored XSS
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  Burp:          [COMPLETE]  Active scan: /api/search â€” 3 issues
  /api/search
  Validator:     [COMPLETE]  Confirmed: IDOR in /api/orders/{id}
  IDOR orders
  Specialist:    [COMPLETE]  No additional issues found
  SQLi /login
```

Expanded row (click to toggle):
```
â— Validator:     [ACTIVE  ]  Trying to disprove: Stored XSS in /comments  â–¼
  Stored XSS
  14:03:01  Received finding â€” evidence: 2 request/response pairs
  14:03:04  Fetched /comments as anonymous user â€” XSS payload absent
  14:03:09  Re-submitted payload with content-type variation â€” reflected
  14:03:14  Cannot disprove â€” marking confirmed  â† current
```

#### 5e. Frontend â€” CSS additions

After existing `.activity-*` rules (~`styles.css` line 1089):

| Class | Purpose |
|---|---|
| `.activity-sub-tab-bar` | Second-level tab bar container |
| `.activity-sub-tab-btn[.active]` | Sub-tab button + active underline state |
| `.agents-panel` | Panel container (flex column) |
| `.agent-row[--active\|--complete]` | Individual agent row with modifier states |
| `.agent-role-name` | Role text; `@keyframes pulse-opacity` (opacity 1â†’0.5â†’1, 0.9s ease-in-out infinite) via `--active` modifier only |
| `.agent-badge-active` | Pulsing accent badge |
| `.agent-badge-complete` | Static `var(--text-2)` badge |
| `.agent-current-task` | Inline task description |
| `.agent-task-history` | Expanded history container |
| `.agent-history-entry` | Single timestamped history row |

### Phase 5 â€“ Role-specific LLM profiles *(optional)*
6. *Depends on 3.* Add optional separate model/prompt settings for Scanner, Specialist,
   and Validator roles, while preserving the current single-config default. Cheaper/faster
   model for specialists on well-defined leads; conservative model for the validator.
   Implemented as a new `AgentRoleConfig` join table or extended `LLMConfig`.

### Phase 6 â€“ Rollout
7. *Depends on 1â€“6.* Canary on selected runs; compare metrics against Phase 0 baseline.

---

## Relevant Files

| File | Changes |
|---|---|
| `src/aespa/services/crawler.py` | Emit `agent_status` at crawl start/complete |
| `src/aespa/services/task_graph.py` | Formalise recon output contract; richer attack-surface summary |
| `src/aespa/services/scanner.py` | Add `agent_dispatch` action type; spawn specialist agents; emit `agent_status` per step |
| `src/aespa/services/validator.py` | Full rework as adversarial agent; emit `agent_status` |
| `src/aespa/services/burp_rest.py` | Emit `agent_status` on scan start and on each poll completion |
| `src/aespa/services/findings.py` | Tag `finding_source = "specialist_agent"` |
| `src/aespa/services/events.py` | No changes â€” `agent_status` uses existing `emit()`/`stream()` |
| `src/aespa/api/scan.py` | Add `/agent-log` endpoint |
| `src/aespa/models.py` | Add `AgentLog` table; optional `AgentRoleConfig` |
| `src/aespa/web/app.js` | Sub-tab bar; agents state; SSE handler; agents panel render |
| `src/aespa/web/styles.css` | Agents panel and sub-tab bar CSS |

---

## Verification

1. **Regression tests:** existing crawl, structured scan, and thinking scan behaviour
   unchanged â€” specialist dispatch and adversarial validator are additive.
2. **Unit tests:** adversarial validator cannot write `ScanFinding` records; specialist
   agent inherits session vault correctly.
3. **Integration tests:** specialist dispatch from thinking scan action; Burp `agent_status`
   events emitted on scan start and poll completion.
4. **UI tests:** Agents tab renders with zero agents, active agents, and after all complete;
   all four role types appear correctly; pulsing animation on active rows only; task history
   expands on click; list persists after page refresh.
5. **Benchmark runs:** confirmed-rate, false-positive-rate, and duplicate-rate vs. Phase 0
   baseline â€” primary target is false-positive-rate reduction from the adversarial validator.
6. **Manual replay:** verify adversarial validator marks a known false positive correctly;
   verify specialist agent surfaces a deeper finding on a confirmed lead.

---

## Decisions

- **Included:** recon output contract, specialist agent dispatch (bolt-on, Burp-style),
  adversarial validator, Agents UI with persistent agent history for all four agent types.
- **Excluded:** parallel hunter workers, task claim/lease, global rate semaphore,
  multi-worker checkpoint redesign â€” see *Rejected* section below.
- **Specialist agents run sequentially** (one at a time per run), matching the existing
  Burp active scan pattern. No concurrent session, rate-limit, or DB contention problems.
- **Adversarial validator** is structurally prohibited from creating findings; it receives
  a fresh LLM conversation per finding with no knowledge of other findings.
- **Burp active scans** gain `agent_status` visibility in the Agents UI with no change
  to their dispatch logic â€” only `burp_rest.py`'s poll loop gains `events.emit()` calls.
- **`agent_status` SSE** reuses existing `events.emit()` / `events.stream()` â€” no new
  transport infrastructure.
- **URL routing:** sub-tab bar is inside the `activity` block; `#/runs/{id}/activity`
  URL is unchanged.

---

## Rejected: Parallel Hunter Architecture

A full recon-hunter architecture with concurrent narrow workers was evaluated against the
Cloudflare model and rejected for this project. The analysis identified four hard
prerequisites that must be in place before multi-worker runs are reliable:

1. **Shared auth session vault + re-auth coordination** â€” each worker bootstrapping auth
   independently creates N Playwright login flows per credential, and a session expiry in
   one worker is invisible to others (they silently receive 401s that look like no finding).
2. **Global request rate semaphore** â€” `sleep_between_probes()` is per-worker; 5 concurrent
   workers Ã— the same `min_delay` means 5Ã— the aggregate request rate against the target,
   which reliably trips WAF / rate-limit thresholds and silences all workers at once.
3. **Atomic task claim with `BEGIN IMMEDIATE`** â€” the `PentestTask` claim/lease pattern
   is a read-then-write race condition on the current SQLModel session pattern; two workers
   can both read `claimed_by IS NULL` and both claim the same task.
4. **Per-worker checkpoint rows** â€” `ScanCheckpoint` has one row per `run_id`; a
   multi-worker resume would silently drop all but one worker's LLM conversation state.

Beyond the prerequisites, a pure narrow-hunter model also threatens business logic
coverage: `_do_thinking_scan()` relies on unified cross-endpoint context, the WSTG
`workflow` skill injected across the whole session, and confirmed findings fed back as
stepping stones â€” all of which are broken when context is siloed by attack class.

The engineering cost of these prerequisites solves a throughput problem AESPA does not
have (it scans one target at a time). The specialist-agent approach delivers the
highest-value Cloudflare insights (adversarial validation, specialist depth on leads)
without any of these costs.

