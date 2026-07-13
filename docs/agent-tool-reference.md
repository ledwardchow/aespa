# Agent Tool Reference

AESPA drives several LLM agents across its web, API, and SAST scan modes. Every
agent runs the same shared agentic loop (`llm.thinking_agentic_loop`) but is handed
a **filtered subset** of a common tool vocabulary, so the tools a given agent can
call depend entirely on its role.

This document lists every tool, what it does, and which agent/scan mode can call it.

- **Web & API tools** are defined in `THINKING_AGENT_TOOLS` (`services/prompts/test_lead.py`); each role subsets it.
- **SAST tools** are a separate set (`SAST_TOOLS` in `services/prompts/sast.py`).
- **Context tools** are read-only reconnaissance sub-commands invoked through the single `context_tool` tool.

---

## Agents & scan modes

| Agent | Scan mode | Tool set (source) |
|---|---|---|
| **Test Lead** | Web dynamic scan (`scanner.py`) | Full `THINKING_AGENT_TOOLS` |
| **API Test Lead** | API scan (`api_scanner.py`) | `get_api_test_lead_tools()` API-aware subset; strict API context routing |
| **Specialist Agent** | Dispatched from web Test Lead / web ALICE | `SPECIALIST_AGENT_TOOLS` (+ crypto extras); API dispatch is withheld |
| **Adversarial Validator** | Post-finding validation (`validator.py`) | `VALIDATOR_AGENT_TOOLS` |
| **A.L.I.C.E.** | Interactive chat, web + API runs (`alice.py`) | `_ALICE_TOOL_NAMES` subset |
| **SAST Scanner** | Standalone static analysis (`sast_scanner.py`) | `SAST_TOOLS` |
| **Reporting Agent** | Post-scan finding pre-screen | No tools — structured-output review pass only |

---

## Tool-use tools

These are the top-level tools the LLM invokes by name.

| Tool | What it does |
|---|---|
| `http_request` | Issue one arbitrary HTTP request (method, URL, headers, body, `use_session`, `owasp_category`). The workhorse for APIs, raw assets, header checks, and direct endpoint testing |
| `browser` | Drive a real Playwright browser through ordered steps — `goto`, `fill`, `type`, `click`, `press`, `wait`, `snapshot`. Used when JS execution, hash routes, form interaction, or DOM rendering is required |
| `context_tool` | Read-only reconnaissance against collected crawl/scan data — see [Context tools](#context-tools) below |
| `write_finding` | Record a confirmed finding (title, severity, affected URL, evidence, CVSS, OWASP category). Only with concrete prior evidence |
| `remove_finding` | Delete a previously recorded finding by `finding_id` (written in error, confirmed duplicate, or invalidated) |
| `update_lead` | Record the outcome of investigating a static-analysis (SAST) lead, whether or not a vulnerability was confirmed |
| `forge_jwt` | Forge an HS256 JWT with a modified payload from a discovered signing secret; optionally store it as a reusable session |
| `decode_jwt` | Decode a JWT's header and payload; optionally verify the HS256 signature against a known secret |
| `credential_check` | Test a small explicit list of credentials (≤ 20) against a login endpoint; stores successful tokens as sessions |
| `register_account` | Create one disposable account via a discovered registration endpoint and store the resulting session |
| `agent_dispatch` | Dispatch a Specialist Agent to deep-dive on a strong, specific lead (`attack_class`, `target_url`, `rationale`, `priority`). Runs concurrently |
| `done` | End the run with a summary. For the validator, instead returns a structured `verdict` + `reasoning` (+ optional PoC) |

### Context tools

Invoked as `context_tool(tool=<sub-command>, args={...})`. They never hit the target.
The loop uses an **adaptive checkpoint**: after 3 consecutive context calls the agent
should take a real action, or continue by including `context_budget_reason` (a short
summary, current hypothesis, and why another targeted context round will change the
next action).

| Sub-command | Returns |
|---|---|
| `site_map` | Filtered list of crawled pages/routes with flags (auth required, takes input, etc.) |
| `page_detail` | Full metadata, flags, and page text for a specific page |
| `history_search` | Excerpts from prior request/response history matching a query |
| `finding_list` | Findings already written this session, filterable by severity/category |
| `target_inventory` | Normalised endpoints, forms, inputs, scripts, storage keys, IDs, and pre-identified `xss_sink` items extracted from crawl intelligence |
| `traffic_search` | Captured HTTP request/response log from crawl and scan phases |
| `endpoint_detail` | Consolidated page + intel + traffic + history for one specific URL |
| `compare_responses` | Status, length, similarity, and term deltas between two history steps |
| `mutate_request` | Proposes HTTP probe objects from a prior step via `input_validation`, `idor`, or `business_logic` mutations |
| `auth_matrix` | Endpoints worth testing across anonymous/user/role boundaries |
| `extract_entities` | URLs, paths, IDs, UUIDs, emails, JWT hints, error/debug lines from text or a prior step |

**API-run sub-commands.** Automated API scans use a strict allowlist: API-specific
inventory commands plus `history_search`, `traffic_search`, `compare_responses`,
`mutate_request`, and `extract_entities`. Web-only or unknown names are rejected rather
than falling through to the web handler. API ALICE uses the API-specific commands below.

| Sub-command | Returns |
|---|---|
| `endpoint_list` | Parsed `ApiEndpoint` rows for the collection (method, path, params) |
| `endpoint_detail` | Full schema, params, and intel for one endpoint |
| `collection_info` | Collection metadata, base URL, scope hosts, auth summary |
| `finding_list` | Findings written this API run |
| `report_finding` | Persist a confirmed finding on an API run (the API-aware replacement for `write_finding`) |
| `lead_list` *(ALICE)* | Open `ScanLead` copies explicitly imported into this API test run |

### SAST file tools

The SAST scanner gets its own set instead of the web/API tools. All file tools are
**path-jailed** to the archive extraction root.

| Tool | What it does |
|---|---|
| `list_files` | Directory listing under a sub-path, up to a configurable depth |
| `glob` | Pattern match across the file tree |
| `read_file` | Read a file by path; optional `start_line`/`end_line`; capped at 20,000 chars |
| `grep` | Regex or literal search across files; capped at 200 results |
| `write_lead` | Record a candidate vulnerability lead (title, description, category, severity, confidence, location, evidence) |
| `filter_lead` | Confirm/score a candidate; leads with confidence ≥ 0.7 become persisted `ScanLead` rows |
| `done` | End the SAST pass with a summary |

---

## Tool availability matrix

✓ = available · — = withheld

| Tool | Test Lead | API Test Lead | Specialist | Validator | A.L.I.C.E. | SAST |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| `http_request` | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| `browser` | ✓ | — | ✓ | — | ✓ | — |
| `context_tool` | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| `write_finding` | ✓ | ✓¹ | ✓ | — | ✓¹ | — |
| `remove_finding` | ✓ | — | — | — | ✓ | — |
| `update_lead` | ✓ | ✓ | — | — | ✓ | — |
| `forge_jwt` | ✓ | ✓ | crypto only² | — | ✓ | — |
| `decode_jwt` | ✓ | ✓ | crypto only² | — | ✓ | — |
| `credential_check` | ✓ | ✓ | — | — | ✓ | — |
| `register_account` | ✓ | ✓ | — | — | ✓ | — |
| `agent_dispatch` | ✓ | — | —³ | — | ✓⁶ | — |
| `done` | ✓ | ✓ | ✓ | ✓⁴ | ✓ | ✓ |
| `compare_responses` | — | — | — | ✓⁵ | — | — |
| SAST file tools | — | — | — | — | — | ✓ |

**Notes**
1. The automated API Test Lead uses API-aware top-level `write_finding`; API ALICE uses `context_tool(tool='report_finding')` and withholds top-level `write_finding`.
2. Specialists get `forge_jwt` / `decode_jwt` only for the `crypto` attack class (`SPECIALIST_AGENT_TOOLS_CRYPTO`); the base specialist set is `http_request`, `browser`, `context_tool`, `write_finding`, `done`.
3. Specialists cannot call `agent_dispatch` — this prevents recursive specialist dispatch.
4. The validator's `done` returns a structured `verdict` (`confirmed` / `false_positive` / …) + `reasoning` + optional PoC, not a free-text summary.
5. The validator gets `compare_responses` as a dedicated top-level tool (not just the `context_tool` sub-command) so it can diff a re-run probe against the original evidence.
6. `agent_dispatch` is available to web ALICE only. API ALICE withholds it until the Specialist executor is fully API/run-kind aware.

---

## Where each tool set is defined

| Set | Location |
|---|---|
| `THINKING_AGENT_TOOLS` | `services/prompts/test_lead.py` |
| `get_api_test_lead_tools()` | `services/prompts/test_lead.py` |
| `SPECIALIST_AGENT_TOOLS` / `SPECIALIST_AGENT_TOOLS_CRYPTO` / `get_specialist_tools()` | `services/prompts/specialist.py` |
| `VALIDATOR_AGENT_TOOLS` | `services/prompts/validator.py` |
| `_ALICE_TOOL_NAMES` / `_get_alice_tools()` | `services/alice.py` |
| `SAST_TOOLS` | `services/prompts/sast.py` |

See [architecture.md](architecture.md) §7–§9 (dynamic scan, multi-agent system, LLM
integration), §15 (A.L.I.C.E.), §16 (API scanning), and §17 (SAST) for how these
agents are wired together.
