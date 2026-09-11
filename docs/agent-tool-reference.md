# Agent Tool Reference

AESPA uses several LLM agents for web, API, and source-code security testing.
Agents share the same agentic loop, but each role receives a filtered tool set.
Runtime filters narrow the set further for some scan modes and ALICE requests.

This document lists the tools exposed to each agent. It describes LLM-callable
tools, not the internal service functions that execute them.

- Web and API tool schemas are defined in `THINKING_AGENT_TOOLS` in
  `src/aespa/services/prompts/test_lead.py`.
- Specialist and validator roles select subsets of those schemas.
- ALICE selects a subset and adds two interactive tools of its own.
- SAST uses separate tool sets for discovery, threat modelling, validation, and
  attack-path analysis.
- Context tools are subcommands called through the single `context_tool` tool.

## Agents and scan modes

| Agent | Scan mode | Tool set |
|---|---|---|
| Test Lead | Web dynamic scan | Full `THINKING_AGENT_TOOLS`, subject to coverage-mode checks |
| API Test Lead | Automated API scan | `get_api_test_lead_tools()` and the API context allowlist |
| SAST Validate Test Lead | Focused live validation of imported SAST leads | `get_sast_validate_tools()`; API runs omit browser and reauthentication |
| Specialist Agent | Dispatched from the web Test Lead or web ALICE | `SPECIALIST_AGENT_TOOLS`, with JWT tools added for crypto specialists |
| Adversarial Validator | Post-finding validation | `VALIDATOR_AGENT_TOOLS` |
| ALICE | Interactive web or API testing | `_get_alice_tools()`, narrowed by run type, coverage mode, and request intent |
| SAST Threat Model | Source-backed repository and threat modelling | `SAST_THREAT_MODEL_TOOLS` |
| SAST Discovery Worker | Source and sink review | `SAST_TOOLS` |
| SAST Candidate Validator | Independent review of one candidate | `SAST_VALIDATION_TOOLS` |
| SAST Attack-Path Analyst | Reachability and dynamic-test planning | `SAST_ATTACK_PATH_TOOLS` |
| Reporting Agent | Finding pre-screen after a scan | No tools; structured-output review only |

An ALICE request about AESPA status is treated as operational. For that request,
ALICE receives only `context_tool` and `done`. Goal mode changes the meaning of
`done`, but does not add tools.

## Web and API tools

These are top-level tools called directly by the model.

| Tool | What it does |
|---|---|
| `http_request` | Sends one scoped HTTP request. It supports named or anonymous sessions, authentication-response capture with `store_as`, page attribution, OWASP category and test-class attribution, and bounded repeat sequences |
| `execute_python` | Runs a short Python script in AESPA's isolated sandbox for payload generation, response parsing, stateful workflows, or bounded request batches. The script has no direct network access and must use `aespa_runtime` for target requests |
| `browser` | Drives a Playwright browser using ordered steps. Supported operations are `goto`, `fill`, `type`, `click`, `check`, `uncheck`, `select_option`, `press`, `wait`, `snapshot`, `inspect_element`, `recover_click`, and `dom_check`. A saved crawler state can be restored with `page_id` and `replay` |
| `context_tool` | Reads collected scan context without sending a request to the target. See [Context tools](#context-tools) |
| `write_finding` | Records a confirmed finding from concrete evidence. API Test Lead findings are saved against the API run by the API-aware executor |
| `remove_finding` | Removes a finding written in error, confirmed as a duplicate, or invalidated. New calls identify it with `finding_reference`; `finding_id` is retained only for older context |
| `update_lead` | Records the outcome of testing an imported SAST lead and can link a confirmed lead to its finding |
| `forge_jwt` | Creates an HS256 JWT with modified claims after a signing secret has been found, with optional session storage |
| `decode_jwt` | Decodes a JWT header and payload and can verify an HS256 signature with a known secret |
| `credential_check` | Tests an explicit list of at most 20 credentials against a login endpoint and stores successful sessions |
| `register_account` | Creates one disposable account through a discovered registration endpoint and stores the resulting session |
| `reauthenticate` | Re-runs the configured web login flow, including supported TOTP and email-OTP steps, and refreshes the primary session |
| `skip_coverage` | Resolves a web Work Program obligation as not applicable or technically blocked, with a reason and supporting evidence when blocked |
| `agent_dispatch` | Starts a Specialist Agent for a specific lead. Supported classes include IDOR, authentication bypass, SQL injection, XSS, business logic, SSRF, path traversal, CORS, cryptography, configuration, and file upload |
| `done` | Proposes that the current agent's work is complete. Its schema and completion checks depend on the role |

### ALICE-only tools

| Tool | What it does |
|---|---|
| `tls_scan` | Runs a scoped TLS posture check for supported protocol versions, weak cipher acceptance, certificate details, and hostname matching |
| `rerun_validation` | Starts AESPA's managed validator for unconfirmed findings in a web run. The tool is present in ALICE's API tool list but returns an unsupported message for API runs |

## Context tools

Context commands are called as
`context_tool(tool=<subcommand>, args={...})`. They do not probe the target.
After three consecutive context calls, the agent must take an action or include
`context_budget_reason` explaining why one more targeted context call is needed.

### Shared and web context commands

| Subcommand | What it returns |
|---|---|
| `run_status` | Current run, crawl, scan, phase, and finding counts |
| `specialist_status` | Specialist handoffs and their current state |
| `site_map` | Filtered crawled pages and routes, including state and page flags |
| `page_detail` | Metadata, flags, text, replay information, traffic, and object references for one page |
| `history_search` | Matching excerpts from the current agent's request and response history |
| `finding_list` | Findings from the current run, with severity, OWASP, category, and text filters |
| `lead_list` | Imported SAST leads and their status |
| `lead_detail` | Full evidence, traces, controls, proof gaps, validation data, and attack path for one lead |
| `target_inventory` | Normalised endpoints, forms, inputs, scripts, storage keys, object references, and detected sinks from crawl intelligence |
| `search_assets` | A search-oriented view of the same web crawl inventory used by `target_inventory` |
| `traffic_search` | Captured HTTP requests and responses from crawl and scan activity |
| `endpoint_detail` | Consolidated page, intelligence, traffic, and history for one web URL |
| `compare_responses` | Status, length, similarity, and term differences between two history steps |
| `mutate_request` | Suggested HTTP probes derived from an earlier request for input validation, IDOR, or business-logic testing |
| `auth_matrix` | Endpoints worth comparing across anonymous, user, and role boundaries |
| `extract_entities` | URLs, paths, IDs, UUIDs, emails, JWT hints, and error or debug lines extracted from text or a history step |
| `coverage_gaps` | Unresolved web Work Program obligations |

The automated API Test Lead can use the safe shared analysis commands
`history_search`, `traffic_search`, `compare_responses`, `mutate_request`,
`extract_entities`, `lead_list`, and `lead_detail`. Web-only inventory commands
such as `target_inventory` and `search_assets` are rejected for API runs.

### API context commands

| Subcommand | Current availability | What it returns or changes |
|---|---|---|
| `endpoint_list` | API Test Lead and API ALICE | Parsed API endpoints with method, path, and parameters |
| `endpoint_detail` | API Test Lead and API ALICE | Schema, parameters, and collected intelligence for one API endpoint |
| `collection_info` | API Test Lead and API ALICE | Collection metadata, base URL, scope hosts, and authentication summary |
| `finding_list` | API Test Lead and API ALICE | Findings written for the API run |
| `lead_list` | API Test Lead and API ALICE | SAST leads imported into the API run |
| `lead_detail` | API Test Lead and API ALICE | Full detail for one imported API lead |
| `run_status` | Initial ALICE context only | Current API run state, phase, progress, and finding count |
| `report_finding` | Implemented by the API dispatcher, but not routed by the current API context wrapper | Records an API finding and links it to the matching coverage cell when possible |
| `coverage_matrix` | Implemented by the API dispatcher, but not routed by the current API context wrapper | API endpoint by OWASP category coverage, optionally filtered to one endpoint |
| `set_coverage` | Implemented by the API dispatcher, but not routed by the current API context wrapper | Marks an API coverage cell in progress, covered, skipped, or blocked without downgrading a stronger existing state |

The automated API Test Lead records findings with top-level `write_finding`.
API ALICE withholds that tool. Its prompt currently directs it to
`report_finding`, but `_make_api_context_tool_fn()` does not route that command.
The same mismatch affects callable `run_status`, `coverage_matrix`, and
`set_coverage` commands. The API run status is still added to ALICE's initial
context before the turn starts.

## SAST tools

All SAST file access is jailed to the extracted source archive. Each SAST phase
gets the four read-only file tools plus tools for its assigned job.

### Read-only file tools

| Tool | What it does |
|---|---|
| `list_files` | Lists files and directories below a relative path to a chosen depth |
| `glob` | Finds files with a glob pattern |
| `read_file` | Reads a relative file, optionally within a line range, with output capped at 20,000 characters |
| `grep` | Runs a regular-expression search below a relative path, optionally filtered by filename pattern, with at most 200 results |

### Discovery tools

These tools are in `SAST_TOOLS` with the read-only file tools.

| Tool | What it does |
|---|---|
| `get_work_program` | Returns the source or sink checks assigned to the worker |
| `record_disposition` | Records the evidence-backed result for one assigned work item |
| `record_semantic_disposition` | Resolves a threat-scenario or repository-model obligation as assessed, a candidate, not applicable, or blocked |
| `write_lead` | Records a candidate with its classification, root causes, location, source and sink traces, controls, and proof gaps |
| `filter_lead` | Scores and reviews a written candidate. Candidates below 0.7 confidence are discarded |
| `done` | Signals that the assigned SAST phase is complete |

### Threat-model tools

`SAST_THREAT_MODEL_TOOLS` contains the read-only file tools and:

| Tool | What it does |
|---|---|
| `record_model_fact` | Records a source-backed asset, actor, identity, boundary, operation, control, sink, dependency, deployment fact, input, or output |
| `record_threat_scenario` | Records a threat scenario tied to repository model facts |
| `finalize_threat_model` | Finalises the threat model, security objectives, assumptions, and open questions |
| `done` | Finishes after the threat model has been finalised |

### Candidate-validation tools

`SAST_VALIDATION_TOOLS` contains the read-only file tools and:

| Tool | What it does |
|---|---|
| `get_candidate` | Returns the assigned discovery candidate and its structured evidence |
| `record_adjacent_concern` | Queues a separate concern found during validation without confirming it as a finding |
| `validate_candidate` | Records an independent confirmed, dismissed, or inconclusive verdict with controls, counterevidence, and proof gaps |
| `done` | Finishes after the assigned candidate receives a verdict |

### Attack-path tools

`SAST_ATTACK_PATH_TOOLS` contains the read-only file tools and:

| Tool | What it does |
|---|---|
| `get_candidate` | Returns an independently validated candidate |
| `record_attack_path` | Saves ordered reachability, impact, severity reasoning, and a dynamic reproduction objective |
| `done` | Finishes after the supplied candidates have attack paths |

## Tool availability matrix

`Conditional` means that availability depends on the run type, scan mode, or
agent specialisation.

| Tool | Web Test Lead | API Test Lead | SAST Validate | Specialist | Validator | ALICE |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| `http_request` | Yes | Yes | Yes | Yes | Yes | Yes |
| `execute_python` | Yes | Yes | Yes | Yes | No | Yes |
| `browser` | Yes | No | Web only | Yes | No | Yes |
| `context_tool` | Yes | Yes | Yes | Yes | Yes | Yes |
| `write_finding` | Yes | Yes | Yes | Yes | No | Web only |
| `remove_finding` | Yes | No | No | No | No | Web only |
| `update_lead` | Yes | Yes | Yes | No | No | Yes |
| `forge_jwt` | Yes | Yes | No | Crypto only | No | Yes |
| `decode_jwt` | Yes | Yes | No | Crypto only | No | Yes |
| `credential_check` | Yes | Yes | No | No | No | Yes |
| `register_account` | Yes | Yes | No | No | No | Yes |
| `reauthenticate` | Yes | No | Web only | No | No | Web only |
| `skip_coverage` | Full mode | No | No | No | No | Web Full mode |
| `agent_dispatch` | Yes | No | No | No | No | Web only |
| `tls_scan` | No | No | No | No | No | Yes |
| `rerun_validation` | No | No | No | No | No | Web only in practice |
| `compare_responses` | Through context | Through context | Through context | Through context | Top level | Through context |
| `done` | Yes | Yes | Yes | Yes | Verdict schema | Yes |

Specialists cannot dispatch other specialists. The validator's `done` returns a
structured verdict, reasoning, and optional proof of concept. SAST tools are not
included in this matrix because their phase-specific sets are listed above.

## Source locations

| Tool set or dispatcher | Location |
|---|---|
| `THINKING_AGENT_TOOLS`, `get_api_test_lead_tools()`, `get_sast_validate_tools()`, `TLS_SCAN_TOOL` | `src/aespa/services/prompts/test_lead.py` |
| `SPECIALIST_AGENT_TOOLS`, `SPECIALIST_AGENT_TOOLS_CRYPTO`, `get_specialist_tools()` | `src/aespa/services/prompts/specialist.py` |
| `VALIDATOR_AGENT_TOOLS` | `src/aespa/services/prompts/validator.py` |
| `_ALICE_TOOL_NAMES`, `_get_alice_tools()`, ALICE-only schemas, API context commands | `src/aespa/services/alice.py` |
| Shared and web context dispatcher | `src/aespa/services/scanner.py` |
| Automated API context allowlist | `src/aespa/services/api_scanner.py` |
| `SAST_TOOLS`, `SAST_THREAT_MODEL_TOOLS`, `SAST_VALIDATION_TOOLS`, `SAST_ATTACK_PATH_TOOLS` | `src/aespa/services/prompts/sast.py` |

See [architecture.md](architecture.md), sections 7 through 9 for dynamic scans
and agents, section 15 for ALICE, section 16 for API scanning, and section 17
for SAST.
