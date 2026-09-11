# Sandboxed Python Execution and Brokered Traffic — Implementation Plan

**Status:** Proposed  
**Date:** 2026-09-04  
**Scope:** Add a constrained `execute_python` capability to AESPA's dynamic web and API testing agents. Generated Python runs in an ephemeral, network-disabled sandbox and can reach an authorised target only through an AESPA-owned request broker. Every brokered request is scope-checked, policy-controlled, attributed to the correct run and agent, and recorded in the existing Traffic Log.

---

## 1. Outcome

AESPA agents should be able to write small Python programs when the built-in HTTP, browser, JWT, and context tools cannot express an edge case. Typical uses include:

- generating binary, compressed, signed, encrypted, or proprietary payloads;
- parsing unusual responses and correlating values across a workflow;
- running bounded concurrent request batches for race-condition testing;
- reproducing custom authentication exchanges;
- adapting later requests from earlier responses;
- constructing multipart or serialization formats that do not fit the normal `http_request` schema.

The feature must not give an LLM provider access to the AESPA host shell. In particular, the existing Codex provider remains read-only and continues to prohibit Codex-owned execution and file-editing tools. The provider calls only AESPA's dynamic `execute_python` tool.

The security boundary is:

```text
LLM agent
   │ execute_python(code, purpose, ...)
   ▼
AESPA execution service
   │ starts a constrained runtime
   ▼
Ephemeral sandbox (no network, no host files, no secrets)
   │ aespa_runtime.request(...) over framed IPC
   ▼
AESPA request broker
   ├── resolves a session handle without revealing credentials
   ├── enforces run identity, scope, scan mode, headers, size, rate, and budget
   ├── validates every redirect hop
   ├── sends the request through AESPA's scanner client/proxy configuration
   └── records request, response, provenance, and coverage evidence
   ▼
Authorised target
```

---

## 2. Product and Security Decisions

These decisions are part of the proposed design and should not be weakened during implementation without a separate threat-model review.

1. **No host shell.** Do not implement this by passing model output to the host's Python interpreter, a terminal, Claude Code, Codex `exec`, PowerShell, or `/bin/sh`.
2. **No direct sandbox networking.** Generated code cannot import its way around AESPA's request policy. The runtime has no externally routable network interface. Target access is available only through the broker.
3. **Session handles, not secrets.** Python may request `use_session="configured_primary"`, but cookies, bearer tokens, API keys, passwords, global secret headers, and proxy credentials are injected by the broker and never returned to the sandbox.
4. **Every real request is traffic.** Successful requests, HTTP errors, TLS/connect failures, timeouts, and cancelled in-flight requests are recorded in `TrafficEntry`. A request rejected before transmission is an execution-policy event, not fabricated network traffic.
5. **The normal finding pipeline remains authoritative.** Script output cannot create a finding directly. The agent must use `write_finding`, and validators continue to require concrete request/response evidence.
6. **Code execution is an escape hatch.** Built-in tools remain the recommended first choice. Prompts tell agents to use Python only when it provides a capability that typed tools cannot.
7. **Disabled by default in the first release.** Operators explicitly enable it after a runtime readiness check.
8. **No runtime package installation.** The sandbox image contains a pinned package set. `pip`, `uv`, `npm`, OS package managers, arbitrary downloads, and dynamic native extensions are unavailable.
9. **HTTP first.** The first release supports brokered HTTP(S) and bounded concurrent HTTP batches. Raw TCP, UDP, arbitrary WebSockets, browser CDP, and request-smuggling-grade raw HTTP are separate future capabilities with their own protocol-specific logging and controls.
10. **Fail closed.** If the sandbox runtime, policy state, scope, run identity, session reference, or traffic persistence is unavailable, the broker denies the request.

---

## 3. Current AESPA Foundations and Gaps

### Foundations to reuse

- `services/traffic.py` already persists HTTPX and Playwright traffic for web and API runs.
- `LoggingAsyncClient` records both completed requests and transport failures.
- `TrafficEntry` already carries run ownership, source, page, username, session label, and browser interaction provenance.
- `services/scope.py` provides live web scope checks, and API scans provide an API-specific scope predicate.
- `_request_scope_checked()` already implements manual, per-hop redirect checking.
- scanner session vaults already let tools select named sessions.
- API traffic callbacks and `post_probe_fn` support coverage attribution.
- scanner policy already defines scan modes, method lists, timeouts, delays, body limits, allowed schemes, blocked headers, redirect behaviour, and destructive-approval intent.
- `thinking_agentic_loop()` already supports dynamic tool schemas and executor callbacks across providers.

### Gaps that must be closed before enabling Python

1. There is no single final outbound-policy boundary used by all agent-originated requests.
2. Static inspection shows policy settings such as `methods_by_mode`, `allowed_schemes`, `blocked_headers`, `max_request_body_bytes`, and `require_approval_for_destructive`, but their enforcement is not centralised. Phase 0 must test current behaviour and close any enforcement gaps.
3. `require_approval_for_destructive` has no persisted approval grant that an executor can verify.
4. `LoggingAsyncClient` hard-codes `source="httpx"` and lacks generic agent/execution provenance.
5. Traffic bodies are text previews. Binary payloads need encoding, original-size, and hash metadata.
6. Web and API identifiers must always be accompanied by `run_kind`, even where the global run-identity migration makes numeric collisions less likely. New tables, cache keys, events, and queries must not key on an integer alone.
7. There is no sandbox runtime readiness/status surface or lifecycle manager.

---

## 4. Threat Model

Treat generated code as hostile. It may be influenced by target-controlled HTML, JavaScript, HTTP headers, API responses, uploaded source, or an LLM failure.

### Assets to protect

- host files, user documents, repository contents, and AESPA's database;
- LLM provider credentials, target credentials, session cookies, proxy credentials, and global headers;
- Docker/container control sockets and desktop application privileges;
- localhost services, LAN devices, cloud metadata endpoints, and unrelated internet hosts;
- CPU, memory, disk, process table, and network capacity;
- traffic-log integrity and finding provenance;
- data from other AESPA runs.

### Required controls

| Threat | Required control |
|---|---|
| Read or modify host files | No host bind mounts; read-only runtime root; isolated ephemeral work directory |
| Read process environment | Minimal allowlisted environment; no AESPA/LLM/proxy secrets |
| Directly contact an unrelated host | Sandbox network disabled; all target traffic uses broker IPC |
| Scan localhost/LAN/cloud metadata | Broker accepts only the current run's explicit authority scope; no URL supplied by the target can expand scope |
| Follow redirect out of scope | Disable automatic redirect following in the transport; validate and send each hop through the broker |
| Steal target credentials | Expose opaque session names only; inject secrets after policy checks; redact logs returned to Python |
| Exhaust host resources | CPU, memory, PID, file-size, output, artifact, request, concurrency, and wall-clock limits |
| Fork bomb or lingering child | PID limit plus container/process-group kill on completion, cancellation, or timeout |
| Escape through privileged runtime access | Non-root UID, dropped capabilities, no-new-privileges, seccomp, no device mounts, no Docker socket |
| Install malicious dependencies | Immutable pinned image; no installer and no outbound package network |
| Hide activity from the user | Broker is the only network path; persist traffic before returning a response to the script |
| Forge evidence | Link traffic rows to a server-created execution ID; never accept traffic IDs or status claims from Python |
| Cross-run data access | Broker binds an unforgeable execution capability to `(run_kind, run_id, agent_id, step)` |
| Leak secrets in output | Recursively redact known session/global-header values from stdout, stderr, errors, artifacts metadata, and tool results |

### Out of scope for the first release

- safely executing untrusted code without an OS/container isolation boundary;
- multi-tenant hosted execution on a shared ordinary Docker daemon;
- raw packet generation, packet capture, ARP, ICMP, DNS rebinding research, or arbitrary protocol tunnelling;
- mounting uploaded source code or AESPA's working tree into the execution sandbox;
- installing arbitrary packages selected by the model.

---

## 5. Agent Tool Contract

Add one tool schema to `services/prompts/test_lead.py`:

```python
{
    "name": "execute_python",
    "description": (
        "Run a bounded Python program for payload construction, response analysis, "
        "or a custom multi-request workflow. Direct networking and host filesystem "
        "access are unavailable. Use aespa_runtime for brokered target requests. "
        "Prefer built-in tools when they can express the test."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "purpose": {
                "type": "string",
                "maxLength": 500,
                "description": "Concrete test objective and why built-in tools are insufficient."
            },
            "code": {
                "type": "string",
                "maxLength": 50000
            },
            "input_artifact_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "maxItems": 10
            },
            "requested_timeout_s": {
                "type": "integer",
                "minimum": 1,
                "maximum": 60,
                "description": "May lower but never raise the operator-configured limit."
            }
        },
        "required": ["purpose", "code"]
    }
}
```

The model does not choose memory, CPU, PID, disk, output, concurrency, or request ceilings. Those are trusted settings. `requested_timeout_s` is optional and is clamped downward.

### Initial role availability

| Role / mode | First release |
|---|---|
| A.L.I.C.E. web | Enabled when global feature and A.L.I.C.E. role are enabled |
| A.L.I.C.E. API | Enabled when global feature and A.L.I.C.E. role are enabled |
| Specialist | Enabled when global feature and Specialist role are enabled |
| Automated Test Lead | Enabled when the global feature and Test Lead role are enabled |
| SAST Validate | Enabled for its focused imported-lead workflows when the Test Lead role is enabled |
| SAST static scanner | Disabled; it receives jailed source-reading tools, not execution |
| Validator | Disabled; preserve deterministic, independently controlled validation |
| Reporting, crawler, mentor | Disabled |

Tool allowlists must be assembled by role, not by assuming every tool in `THINKING_AGENT_TOOLS` is safe everywhere. Update the API Test Lead, SAST Validate, specialist, and A.L.I.C.E. allowlist tests accordingly.

---

## 6. Sandbox Runtime API

Ship a small `aespa_runtime` package inside the immutable execution image. It must have no credentials and no database knowledge.

### 6.1 HTTP request

```python
from aespa_runtime import request

response = request(
    method="POST",
    url="https://target.example/api/import",
    headers={"Content-Type": "application/octet-stream"},
    body=payload_bytes,
    use_session="configured_primary",
    page_id=123,
    owasp_category="A03",
    test_class="deserialization",
    obligation_id=456,
    note="Send the custom serialized payload",
)

print(response.status_code)
print(response.headers)
print(response.body)       # bytes, truncated to the configured return limit
print(response.traffic_id) # server-created ID after TrafficEntry commit
```

Request arguments:

- `method`, `url`, `headers`;
- exactly one of `body`, `json`, `form`, or `multipart`;
- binary bodies encoded over IPC as base64 with an explicit byte length and SHA-256;
- `use_session` as an opaque label, including the special `anonymous` label;
- optional `page_id`, `owasp_category`, `test_class`, and `obligation_id`;
- optional `repeat_sequence` and `repeat_limit` under the same bounded repetition contract as `http_request`;
- optional `note`, `observation`, `hypothesis`, and `payload_purpose` for provenance;
- `follow_redirects` may request fewer redirects than policy permits, never more.

Response fields:

- status, headers after redaction, body bytes, elapsed time, final URL;
- `traffic_id` for the final hop and `redirect_traffic_ids` for earlier transmitted hops;
- `truncated`, `original_body_size`, content type, and body SHA-256;
- a structured policy error for denied requests, distinct from transport failure.

Do not return `Set-Cookie`, secret response tokens automatically captured into session storage, injected `Authorization`, `Cookie`, proxy headers, or other known secret values to the script. If a workflow must extract a non-secret value, it can read the ordinary redacted response body or headers. Authentication responses may use `store_as` so the broker captures a session without exposing the token.

### 6.2 Concurrent batches

Race testing needs an explicit primitive rather than encouraging scripts to create unbounded threads:

```python
from aespa_runtime import request_batch

responses = request_batch(
    requests=[...],
    concurrency=5,
    start_together=True,
    repeat_sequence="coupon-redemption-race",
    repeat_limit=8,
)
```

The broker validates the entire batch and atomically reserves its request budget before starting it. Maximum concurrency and batch size come from trusted settings. Each transmitted request receives its own `TrafficEntry`; all rows share one `code_execution_id` and batch correlation ID. `start_together` uses a broker-side barrier so model code cannot bypass scheduling policy.

### 6.3 Artifacts

Provide:

- `read_artifact(id) -> bytes` for explicitly attached, run-owned input artifacts;
- `write_artifact(name, data, content_type)` for small output artifacts;
- `list_input_artifacts()`.

The host validates ownership before attachment. Use server-generated storage names; reject paths, traversal components, symlinks, device files, and oversized data. The sandbox sees logical names only.

### 6.4 Standard output

Normal `print()` output is captured as stdout. The protocol transport must not share an unframed stream with user stdout: a runtime harness captures script stdout/stderr and emits them as encoded protocol events. This prevents script output from forging broker messages.

---

## 7. Bidirectional Runner Protocol

Use a versioned, length-prefixed JSON protocol between AESPA and a trusted harness inside the sandbox image. Do not parse arbitrary newline-delimited script output as control messages.

### Host to harness

- `execution.start`: protocol version, execution ID, code, logical input-artifact descriptors, and effective limits;
- `broker.response`: response or policy error for a prior request ID;
- `execution.cancel`: cancellation reason;
- `artifact.data`: bounded artifact bytes requested by the script.

### Harness to host

- `execution.ready`: image/runtime versions and supported SDK features;
- `broker.request`: one structured request intent;
- `broker.request_batch`: bounded batch intent;
- `stdout.chunk` / `stderr.chunk`: base64-encoded captured output chunks;
- `artifact.write`: proposed output artifact;
- `execution.result`: exit code, result summary, and resource counters;
- `execution.error`: harness/runtime failure.

Every frame includes `protocol_version`, `execution_id`, a monotonic sequence, and a request/event ID. The host rejects mismatched execution IDs, duplicate IDs, unsupported versions, oversized frames, and out-of-order terminal events.

### Recommended container process layout

```text
docker run --network none -i <pinned-image-digest> aespa-harness
     stdin/stdout: framed host protocol
     │
     ├── creates private /work and local Unix socket
     ├── launches isolated script child as unprivileged UID
     ├── captures child stdout/stderr separately
     └── forwards aespa_runtime RPC between child and host protocol
```

AESPA starts Docker with `asyncio.create_subprocess_exec()` and an argv list, never a shell string. Code and inputs travel over the protocol; no host source directory or temporary code file is bind-mounted.

---

## 8. Outbound Request Policy Gateway

Create `src/aespa/services/outbound_policy.py` and `src/aespa/services/request_broker.py`.

### 8.1 Trusted request context

The caller constructs this context; Python cannot set or override it:

```python
@dataclass(frozen=True)
class RequestContext:
    run_kind: Literal["web", "api"]
    run_id: int
    agent_id: str
    agent_role: str
    agent_step: int
    source: Literal["test_lead", "specialist", "alice", "python"]
    code_execution_id: int | None
    scope_check: Callable[[str], str | None]
    session_vault: SessionVault
    scanner_policy: RunScannerPolicyOut
    post_probe_fn: Callable | None
```

The broker creates an unguessable in-memory capability mapped to this context for the lifetime of the execution. Protocol frames carry the capability, not a caller-selected run ID.

### 8.2 Request validation order

Before any network I/O:

1. Verify the execution is running and its capability matches the bound run and agent.
2. Parse the URL strictly; reject credentials in URLs, fragments, control characters, malformed authority, and non-HTTP schemes.
3. Require the scheme to be in `allowed_schemes` and also hard-limit the first release to HTTP(S).
4. Run the live web/API scope predicate against the exact authority including effective port.
5. Normalise and validate the method against `methods_by_mode[scan_mode]`.
6. Enforce destructive approval where required.
7. Drop or reject blocked headers case-insensitively. Always reserve `Host`, `Cookie`, `Authorization`, `Proxy-Authorization`, hop-by-hop headers, `Content-Length`, and transfer framing for the broker unless a future raw-HTTP mode explicitly handles them.
8. Validate decoded body length before allocation and before sending.
9. Resolve `page_id` or API endpoint attribution and reject a row owned by a different run.
10. Resolve the session label from the current run's vault; never accept raw cookie or credential material.
11. Atomically reserve per-execution, per-batch, per-page/endpoint, repetition, and run request budgets.
12. Apply minimum delay/rate controls, except for an explicitly authorised bounded concurrent batch.
13. Merge safe operator global headers and session headers after validating script-supplied headers.
14. Send with automatic redirects disabled.
15. For each redirect, resolve the new URL, repeat scheme/scope/method/body rules, log the completed hop, and only then transmit the next hop.
16. Persist traffic and coverage provenance before returning the response to the sandbox.

Policy denials increment the execution's denied counter and generate a `scanner_phase` event with redacted details. They do not create a `TrafficEntry` because no traffic occurred.

### 8.3 Destructive approval

Add an explicit run-bound approval grant. Do not interpret enabling global destructive mode as approval when `require_approval_for_destructive` is true.

Recommended model:

```python
class DestructiveScanApproval(SQLModel, table=True):
    id: int | None
    run_kind: str
    run_id: int
    scope_snapshot_hash: str
    policy_snapshot_hash: str
    approved_at: datetime
    revoked_at: datetime | None
```

The run-start UI displays the effective destructive methods and scope and requires a deliberate confirmation. Approval is invalidated if scope or relevant policy changes. Python requests use the same approval check as ordinary tools.

### 8.4 Migration strategy for existing request paths

Phase 0 introduces a common `send_request(intent, context)` path and migrates agent-originated requests before the executor is enabled:

- Test Lead `http_request`;
- specialist `http_request`;
- A.L.I.C.E. web and API `http_request`;
- API Test Lead probes;
- credential and registration tools where they issue model-directed requests;
- validator requests where applicable, with a validator-specific trusted context;
- deterministic probes in later slices if their semantics differ.

Keep `_request_scope_checked()` as an internal building block or replace it with broker redirect handling. Do not maintain two independent redirect-policy implementations.

Playwright remains a separate transport but should call the same URL/method policy validator for explicit `goto` steps and use route interception to block out-of-scope redirects/subresources where appropriate. Arbitrary JavaScript execution is not added to the browser tool as part of this feature.

---

## 9. Sandbox Backend

Create a backend interface so runtime choices do not leak into agent executors:

```python
class CodeRunner(Protocol):
    async def readiness(self) -> RunnerReadiness: ...
    async def execute(self, spec: ExecutionSpec, broker: BrokerHandler) -> ExecutionResult: ...
    async def cancel(self, execution_id: int) -> None: ...
```

Implement:

- `DisabledCodeRunner`: stable unavailable result when the feature/runtime is disabled;
- `DockerCodeRunner`: first supported runtime;
- future `GVisorCodeRunner` or remote microVM worker behind the same interface.

### Docker execution profile

Use an image referenced by immutable digest in releases. Suggested initial limits:

| Resource | Default | Hard configurable range |
|---|---:|---:|
| Wall clock | 30 s | 1–60 s |
| CPU | 0.5 core | 0.25–2 cores |
| Memory | 256 MiB | 64–1024 MiB |
| PIDs | 32 | 8–64 |
| Writable work area | 16 MiB tmpfs | 4–64 MiB |
| stdout + stderr | 64 KiB | 8–256 KiB |
| Output artifacts | 10 MiB total | 0–50 MiB |
| Brokered requests | 20 | 0–100, also bounded by scan policy |
| Concurrent requests | 5 | 1–10 |
| IPC frame | 2 MiB | fixed upper bound |

Container flags/profile must include:

- `--network none`;
- `--read-only` with only a bounded tmpfs work area;
- non-root numeric UID/GID;
- `--cap-drop ALL`;
- `--security-opt no-new-privileges`;
- default or stricter seccomp profile;
- `--pids-limit`, `--memory`, `--memory-swap`, `--cpus`, and bounded ulimits;
- no privileged mode, devices, host PID/IPC/network namespace, host paths, SSH agents, or Docker socket;
- minimal environment (`LANG`, deterministic Python flags, SDK socket path only);
- container label with execution ID for crash cleanup, containing no target or secret data;
- explicit stop/kill and removal in `finally`.

The image should contain Python in isolated mode, the trusted harness and SDK, and a deliberately small pinned library set such as `cryptography`, `PyJWT`, `pyotp`, `msgpack`, `protobuf`, and safe parsing utilities. Direct HTTP packages may be present for data structures but cannot reach a network. Document the exact supported package list in the tool prompt.

### Runtime readiness

Readiness checks verify:

- feature enabled;
- Docker executable/API reachable;
- expected image digest present;
- protocol and SDK version compatible;
- an offline self-test cannot reach the network or a host sentinel file;
- a broker loopback self-test succeeds without revealing a session secret.

Do not automatically pull an image during a scan. Installation/pull is an explicit settings action with progress and error reporting. A missing runtime disables the tool without failing unrelated scans.

---

## 10. Persistence and Migration

### 10.1 `CodeExecution`

Add to `models.py`:

```python
class CodeExecution(SQLModel, table=True):
    __tablename__ = "code_execution"

    id: int | None = Field(default=None, primary_key=True)
    run_kind: str = Field(index=True)                 # web | api
    run_id: int = Field(sa_column=_run_identity_fk())
    agent_id: str = Field(index=True)
    agent_role: str
    agent_step: int | None = Field(default=None)
    purpose: str
    code_redacted: str | None = Field(default=None)
    code_sha256: str
    status: str = Field(index=True)                   # queued|running|succeeded|failed|timed_out|cancelled|runtime_unavailable
    runtime_backend: str
    runtime_version: str | None = Field(default=None)
    image_digest: str | None = Field(default=None)
    protocol_version: str
    limits_json: str = Field(default="{}")
    request_count: int = Field(default=0)
    denied_request_count: int = Field(default=0)
    stdout_preview: str | None = Field(default=None)
    stderr_preview: str | None = Field(default=None)
    result_json: str | None = Field(default=None)
    exit_code: int | None = Field(default=None)
    error_message: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
```

Store a redacted code copy for auditability and a hash of the exact submitted bytes. Exact source retention should be a configurable local-data policy; the default can retain redacted code because AESPA is localhost-oriented, but exports must exclude or clearly opt into execution source. Never put unredacted credentials into code intentionally.

### 10.2 `CodeArtifact`

```python
class CodeArtifact(SQLModel, table=True):
    __tablename__ = "code_artifact"

    id: int | None = Field(default=None, primary_key=True)
    execution_id: int = Field(foreign_key="code_execution.id", index=True)
    direction: str                              # input | output
    logical_name: str
    content_type: str | None
    size_bytes: int
    sha256: str
    stored_path: str
    created_at: datetime
```

Use the existing AESPA data-directory conventions rather than repository-relative storage. Deleting a run removes executions and artifacts. Startup recovery marks stale `running` executions as interrupted and removes labelled orphan containers and temporary artifact files.

### 10.3 `TrafficEntry` additions

Add nullable, generally useful provenance fields:

- `code_execution_id` FK/index;
- `batch_id` and `batch_index`;
- `agent_id`, `agent_step`;
- `owasp_category`, `test_class`, `obligation_id`;
- `request_body_encoding`, `request_body_size`, `request_body_sha256`;
- `response_body_encoding`, `response_body_size`, `response_body_sha256`;
- optional request/response artifact IDs when full bounded binary evidence is retained.

Keep `source` as a transport/origin label and add `source="python"` for brokered Python requests. Existing rows remain valid with null provenance and `source` values `httpx` or `playwright`.

### 10.4 Alembic

Follow the repository migration workflow:

1. update SQLModel definitions;
2. autogenerate a revision;
3. inspect constraints, indexes, nullable defaults, and downgrade order;
4. test upgrade from a legacy database without the new tables/columns;
5. test cascade/cleanup behaviour and web/API ownership.

Avoid adding ad-hoc `_ensure_column` migrations for the new feature unless required by the repository's legacy-bootstrap path; Alembic remains authoritative.

---

## 11. Traffic Logging and UI

### Backend logging changes

Refactor `traffic._write()` to accept a `TrafficProvenance` object or explicit keyword-only provenance rather than continuing to grow a positional argument list. Update HTTPX hooks and Playwright logging to use keyword arguments.

Extend `LoggingAsyncClient` with trusted constructor fields:

```python
LoggingAsyncClient(
    run_id=...,
    api_run_id=...,
    source="python",
    username="specialist",
    page_id=...,
    session_label="configured_primary",
    provenance=TrafficProvenance(...),
)
```

For brokered requests, traffic must be committed before the broker response containing `traffic_id` is sent back to Python. Change `_write()` to return the new row ID. Preserve WAF detection and API traffic hooks.

Header logging must redact values but preserve useful names. Do not expose injected credentials back to Python. The UI may continue to show redacted placeholders such as `[REDACTED]`.

### Binary body representation

Use these preview encodings:

- `text`: valid displayable text, truncated by byte-aware logic;
- `base64`: bounded binary preview when it materially aids reproduction;
- `hex`: short diagnostic preview where configured;
- `omitted`: sensitive or oversized content.

Always store original byte size and SHA-256 independently of preview truncation. Full binary retention is opt-in and bounded; when enabled, store it as a run-owned artifact and link it rather than inflating the traffic table.

### Traffic Log interface

Update `frontend/src/components/TrafficView.jsx` and related CSS:

- add a distinct `python` source badge;
- allow filtering by execution ID, agent, session, category, and test class as well as URL/method/status/source;
- show `Execution #N`, agent, step, purpose, batch position, session, and coverage attribution in the detail header;
- link to an execution detail drawer containing redacted code, stdout, stderr, limits, runtime, artifacts, and policy denials;
- label encoded/truncated bodies and show original sizes/hashes;
- offer artifact download only for retained, authorised artifacts;
- preserve current web and API polling behaviour.

Suggested table behaviour:

```text
#   Time          Source   Agent           Method Status URL                         Execution
81  12:03:41.221  python   specialist-3    POST   201    /api/jobs                   #42 1/3
82  12:03:41.407  python   specialist-3    GET    200    /api/jobs/781               #42 2/3
83  12:03:41.690  python   specialist-3    GET    200    /api/jobs/781/result        #42 3/3
```

Do not overload `interaction_id`, which currently means a replayed browser action. Use `code_execution_id` and `batch_id` explicitly.

### APIs

Add thin routes backed by a service module:

- `GET /api/test-runs/{id}/code-executions`;
- `GET /api/test-runs/{id}/code-executions/{execution_id}`;
- API-run aliases using `api_test_run_id` ownership;
- `GET .../code-artifacts/{artifact_id}` with run ownership validation;
- optional cancellation endpoint for an active execution, also invoked by scan stop.

Traffic responses can include the new nullable provenance fields without a second query. Execution detail is fetched lazily.

---

## 12. Agent and Scan-Engine Integration

### Shared execution service

Create `src/aespa/services/code_execution.py`:

```python
async def execute_agent_python(
    *,
    run_kind: str,
    run_id: int,
    agent_id: str,
    agent_role: str,
    agent_step: int,
    purpose: str,
    code: str,
    input_artifact_ids: list[int],
    session_vault: dict[str, dict],
    scanner_policy,
    scope_check_fn,
    post_probe_fn=None,
    stop_check=None,
) -> str:
    """Persist, execute, broker requests, emit events, and return a bounded tool result."""
```

The returned tool result includes:

- execution ID/status;
- stdout/stderr previews;
- request count and traffic IDs;
- artifact descriptors;
- policy denial summaries;
- timeout/cancellation/runtime errors;
- a reminder that script output is not finding evidence unless linked traffic demonstrates it.

### Test Lead

Wire `execute_python` into `_do_agentic_thinking_loop()` alongside other action types. It must:

- pass the current run's scope predicate and session vault;
- count as one agent tool step while every internal request counts as a probe;
- participate in Execution Monitor strategy/progress tracking;
- append a compact execution result to conversation history;
- checkpoint only after the execution reaches a terminal state;
- cancel immediately when the run stop flag is set.

### Specialists

Add an executor branch to `_run_specialist_agent()`. Bind the specialist's authoritative target/page/session scope, but still permit other URLs already in the run's authorised scope where the handoff contract allows it. Use `agent_id` and handoff metadata for traffic provenance.

### A.L.I.C.E.

Add a branch to `_execute_alice_tool()` for web and API runs. Use `_traffic_run_id=None` plus `api_run_id` for API traffic, matching existing attribution. The user's chat stop action must cancel active Python executions.

Because A.L.I.C.E. is user-directed, expose the redacted code block and purpose in its live step UI before or while the execution runs. This is informational in the first release; it is not a per-execution approval prompt unless the request requires destructive approval.

### API scanner

Use API collection scope, `api_test_run_id`, API session vault, and the existing `post_probe_fn`. Require each brokered request to declare `owasp_category`; preserve `test_class` and obligation linkage. API coverage hooks must not double-count the same request when both generic traffic hooks and `post_probe_fn` are active—define one authoritative callback path and test it.

### Prompts

Update Test Lead, API Test Lead, specialist, and A.L.I.C.E. prompts with:

- when Python is appropriate;
- the supported package and SDK surface;
- no direct sockets, filesystem assumptions, installers, subprocesses, or browser automation;
- session labels are handles and secrets must not be printed;
- every request needs meaningful OWASP/test attribution where applicable;
- bounded batch guidance;
- output must summarise observations, not claim a vulnerability without traffic evidence;
- repeated policy denials mean switch strategy, not attempt a sandbox bypass.

Provider adapters need no native execution privilege. They receive the dynamic tool schema through the existing tool-call machinery.

---

## 13. Configuration and Operator Experience

Prefer a separate `CodeExecutionConfig` singleton rather than adding runtime-specific fields to `ScannerPolicy`:

```python
class CodeExecutionConfig(SQLModel, table=True):
    id: int = 1
    enabled: bool = False
    backend: str = "docker"
    image_ref: str = "ledwardchow/aespa-python-executor:0.1"
    allowed_roles_json: str = '["alice","specialist","test_lead"]'
    timeout_s: int = 30
    memory_mb: int = 256
    cpu_cores: float = 0.5
    pids_limit: int = 32
    workspace_mb: int = 16
    output_limit_bytes: int = 65536
    artifact_limit_bytes: int = 10485760
    max_requests_per_execution: int = 20
    max_concurrent_requests: int = 5
    max_concurrent_executions: int = 2
    retain_redacted_source: bool = True
    retain_binary_artifacts: bool = False
    updated_at: datetime
```

Add `/api/settings/code-execution` GET/PUT and `/api/settings/code-execution/status`. The status response reports availability without exposing daemon paths or sensitive host details.

Settings UI should provide:

- feature toggle and warning explaining that model-generated code will run in an isolated runtime;
- role checkboxes;
- timeout/resource/request limits;
- runtime/image version and readiness;
- explicit Install/Pull or Verify Runtime action;
- a self-test result;
- a note that scans continue without Python if the runtime is unavailable.

Record the effective execution configuration and image digest in each run's execution snapshot for reproducibility. A global settings change must not silently expand the permissions of an already-running scan; capture effective limits at execution start from the run snapshot or only allow stricter live changes.

---

## 14. Lifecycle, Cancellation, and Concurrency

- Maintain active executions in a registry keyed by `(run_kind, run_id, execution_id)`.
- Use a global semaphore for `max_concurrent_executions` and per-run fairness so one scan cannot occupy every slot indefinitely.
- Queueing time does not consume wall-clock execution time, but a stopped run removes queued work.
- Run stop, API run stop, A.L.I.C.E. stop, process shutdown, and execution timeout all signal cancellation, wait briefly, then kill the container/process group.
- Always transition the database row to a terminal status in `finally`.
- On application startup, mark stale `queued`/`running` rows as interrupted and remove only containers carrying AESPA's exact execution label namespace.
- Never delete arbitrary containers by image name, name prefix alone, or unresolved IDs.
- Do not resume Python at a half-completed instruction pointer after restart. The agent checkpoint records the execution's terminal/interrupted result and decides whether to generate a new bounded execution.
- Apply stdout, stderr, artifacts, protocol, and traffic preview backpressure while the process runs; do not accumulate unbounded data in memory.

---

## 15. Secrets, Redaction, and Exports

Centralise redaction in a service that receives the current run's known secret values and safe labels. Apply it to:

- persisted redacted code;
- stdout/stderr and exceptions;
- tool results and event payloads;
- traffic request/response header displays;
- artifact names and metadata;
- execution exports and debug logs.

Do not expose a generic `get_session()` or environment API in `aespa_runtime`. Session metadata may list labels and non-sensitive account names only if that information is already available to the calling agent.

Site/API export behaviour must be explicit:

- default export includes execution metadata, hashes, request linkage, and redacted previews;
- exact source and binary artifacts require an opt-in export flag;
- provider credentials, proxy secrets, session material, and destructive-approval internal tokens are always excluded;
- import validates all execution IDs and artifact paths and does not recreate runnable executions.

Ordinary server logs should not print generated code or payload bodies. Keep detailed execution data in the local database/UI under the same testing-traffic privacy posture as existing traffic logs.

---

## 16. Packaging and Distribution

### Repository/runtime image

Add a dedicated directory, for example:

```text
runtime/python-executor/
├── Dockerfile
├── requirements.lock
├── aespa_harness/
├── aespa_runtime/
└── tests/
```

Build the image reproducibly in CI, run sandbox escape/negative tests, generate an SBOM, scan dependencies, sign the image, and publish a digest. AESPA release metadata pins the digest rather than a mutable tag.

### Desktop applications

Do not bundle a Docker daemon inside the PyInstaller application. Bundle only the small runner metadata/protocol definitions and detect an external supported runtime.

Update `scripts/build_mac.sh`, `scripts/build_win.ps1`, and `scripts/AESPA.spec` if new runtime manifests, seccomp profiles, templates, or helper binaries are read at runtime. Frozen path resolution must check `sys.frozen`/`sys._MEIPASS`.

macOS and Windows releases should:

- show a clear unavailable state when Docker Desktop is absent or stopped;
- never hang startup while probing Docker;
- never pull a large image automatically on first scan;
- support explicit setup with progress and cancellation;
- pass the same protocol tests as Linux despite host path/pipe differences, because code travels over stdin/stdout rather than a bind-mounted Unix socket.

For a future hosted service, prefer gVisor or a microVM/remote-worker backend and keep the broker on the trusted AESPA side. Do not expose the Docker daemon TCP API to the sandbox.

---

## 17. Events and Observability

Emit persisted `scanner_phase` events:

- `code_execution_queued`;
- `code_execution_started`;
- `code_execution_request` with traffic ID after commit;
- `code_execution_policy_denied`;
- `code_execution_completed`;
- `code_execution_failed` / `timed_out` / `cancelled`.

Event payloads contain execution ID, agent, step, purpose preview, counters, and redacted summaries. Do not stream exact source or secrets through general agent-status events.

Operational metrics per run:

- executions by role/status;
- runtime startup latency and execution duration;
- brokered/denied requests;
- bytes in/out and artifacts produced;
- executions with no measurable progress;
- built-in-tool fallback rate after Python failure;
- findings whose evidence includes Python-originated traffic.

Feed execution results into `ExecutionMonitor`. Repeated identical code hashes, identical request sequences, policy denials, or executions with no requests/artifacts/useful output should count as non-progress and trigger mentor guidance or termination under existing policy.

---

## 18. Testing Strategy

No unit or integration test may contact an external target, Docker registry, or live LLM.

### 18.1 Unit tests: policy gateway

- allowed in-scope URL succeeds;
- explicit web/API scope separation and correct effective-port handling;
- out-of-scope host, port, scheme, URL credentials, and malformed URL rejected;
- every redirect hop rechecked; out-of-scope redirect logged only for the transmitted prior hop;
- methods enforced for passive, safe-active, aggressive, and destructive modes;
- destructive request denied without a valid run/scope/policy-bound approval;
- blocked/reserved headers rejected case-insensitively;
- raw cookie/authorization attempts cannot override the session vault;
- request body limit evaluated on decoded bytes, including base64/multipart overhead cases;
- response truncation preserves original size/hash;
- request budgets reserved atomically under concurrency;
- repeat contracts and race batches cannot exceed limits;
- delay/rate rules applied correctly;
- session and page/endpoint references cannot cross runs;
- policy denial produces no `TrafficEntry`.

### 18.2 Unit tests: protocol and harness

- version negotiation;
- partial reads and multiple frames per read;
- maximum frame size;
- forged execution ID/capability;
- duplicate/out-of-order messages;
- arbitrary stdout resembling protocol frames;
- malformed JSON/base64 and incorrect declared byte length/hash;
- host cancellation during a request;
- harness crash and unexpected EOF;
- output/artifact truncation and backpressure;
- terminal result exactly once.

### 18.3 Unit tests: persistence and traffic

- web traffic sets `test_run_id` and leaves `api_test_run_id` null;
- API traffic sets `api_test_run_id` and leaves `test_run_id` null;
- all rows link to the right `code_execution_id`, agent, step, batch, session, and coverage fields;
- `source="python"` displayed and filterable;
- failed transports are persisted; preflight policy denials are not;
- `_write()` returns an ID only after commit;
- API coverage callback fires exactly once;
- WAF detection still runs;
- binary preview metadata and artifacts are correct;
- cleanup deletes run-owned execution rows/artifacts without affecting another run;
- migration works from representative legacy schemas.

### 18.4 Agent integration tests

Using a fake `CodeRunner` and fake broker transport:

- tool schema is present only for allowed roles/modes;
- Test Lead, specialist, web A.L.I.C.E., and API A.L.I.C.E. bind correct context;
- Codex/other providers see only AESPA's dynamic tool, not host tools;
- session labels work without exposing secret values in tool results;
- script output cannot write a finding automatically;
- execution result enters history/checkpoint once;
- stop/cancel reaches runner and terminal status;
- Execution Monitor detects repeated/non-progress executions;
- runtime unavailable produces a useful tool result and scan continues.

### 18.5 Docker isolation integration tests

Run only in an explicitly marked CI job with a local prebuilt image:

- cannot resolve or connect to the internet, target network, host gateway, or metadata addresses directly;
- cannot read a host sentinel file;
- cannot see AESPA environment secrets;
- cannot access Docker socket/devices;
- cannot write outside bounded work area;
- fork bomb hits PID limit;
- memory/CPU/disk/output limits terminate safely;
- subprocess children do not survive execution;
- brokered request to a local fake target succeeds and is logged;
- image digest/protocol mismatch fails closed.

### 18.6 Frontend tests and visual QA

- Python source badge, execution columns, encoded-body labels, and detail drawer;
- filtering and sorting with nullable legacy fields;
- web and API Traffic Log routes;
- large code/output previews do not break layout;
- secrets appear redacted;
- desktop-width screenshot verifies the Traffic Log and execution drawer bounds;
- run the frontend undefined-variable check after refactoring and then `npm run build`.

### 18.7 Security regression suite

Maintain adversarial scripts attempting:

- direct `socket`, `urllib`, `requests`, DNS, IPv4/IPv6, localhost, and host-gateway access;
- `/proc`, environment, filesystem, device, and Docker socket reads;
- shell/process escape, symlink/hardlink abuse, oversized base64, decompression bombs, and output floods;
- broker protocol spoofing and traffic-ID forgery;
- session enumeration and secret reflection;
- cross-run IDs and stale execution capabilities;
- redirect, alternate IP notation, Unicode hostname, and port confusion;
- race-based budget oversubscription.

The feature cannot ship if any negative test reaches an unbrokered network destination or reads a host secret.

---

## 19. Implementation Slices

### Slice 0 — Policy baseline and enforcement

1. Add tests that demonstrate the intended behaviour of every existing scanner policy field.
2. Implement the shared outbound-policy/request path.
3. Migrate Test Lead, specialist, A.L.I.C.E., and API agent HTTP calls.
4. Add persisted destructive approval and UI confirmation.
5. Verify scope-checked redirects, session isolation, traffic, WAF detection, and coverage remain correct.

**Exit criterion:** all agent-originated HTTP calls pass the same policy test suite; no Python feature is enabled yet.

### Slice 1 — Traffic provenance and binary evidence

1. Add migrations for generic traffic provenance/body metadata.
2. Refactor traffic writes to keyword provenance and return committed traffic IDs.
3. Extend `LoggingAsyncClient` with configurable source/provenance.
4. Update traffic APIs and UI for `python`-ready provenance.
5. Preserve current HTTPX/Playwright behaviour with regression tests.

**Exit criterion:** a synthetic trusted caller can write `source="python"` traffic linked to an execution fixture and view it in web/API Traffic Logs.

### Slice 2 — Persistence, protocol, and fake runner

1. Add `CodeExecution`, `CodeArtifact`, config models, migrations, cleanup, and APIs.
2. Implement protocol codecs/state machine.
3. Implement `DisabledCodeRunner` and an in-process **test-only** fake runner.
4. Build `code_execution.py`, broker capability binding, events, cancellation, and redaction.
5. Test the complete flow without Docker.

**Exit criterion:** deterministic fake scripts can make brokered fake requests with full attribution and lifecycle handling.

### Slice 3 — Docker image and runner

1. Implement harness and `aespa_runtime` SDK.
2. Build immutable image and locked dependencies.
3. Implement Docker runner with hard limits and cleanup.
4. Add readiness/self-test and explicit image setup.
5. Run isolation and failure-injection tests on Linux, macOS Docker Desktop, and Windows Docker Desktop.

**Exit criterion:** network-disabled code can reach only the fake target through the broker; all escape tests fail safely.

### Slice 4 — A.L.I.C.E. and specialist rollout

1. Add tool schemas/prompts and allowlists for web/API A.L.I.C.E. and specialists.
2. Add execution details to live agent steps and Traffic Log.
3. Ensure stop/cancel and API run attribution.
4. Ship disabled by default and collect local operational metrics during opt-in testing.

**Exit criterion:** an operator can run an edge-case Python workflow, see each request in Traffic Log, and link evidence to the normal finding pipeline.

### Slice 5 — Automated Test Lead rollout

1. Enable behind a separate role flag.
2. Add heuristics/prompt guidance to prefer typed tools.
3. Integrate checkpoints, completion policy, execution monitor, and mentor intervention.
4. Compare scan completion, finding quality, request volume, and non-progress rates against a no-Python baseline.

**Exit criterion:** Python improves representative blocked scans without materially increasing scope denials, duplicate probing, false positives, or resource failures.

### Slice 6 — Hardening and optional stronger backend

1. Add gVisor or remote microVM backend for hosted/high-risk deployments.
2. Add signed image/SBOM verification and release automation.
3. Consider protocol-specific WebSocket or raw-HTTP brokers only after separate threat models and Traffic UI designs.

---

## 20. File Change Map

| Area | Expected files |
|---|---|
| Models/migrations | `src/aespa/models.py`, `alembic/versions/<revision>.py`, `src/aespa/db.py` only if legacy bootstrap needs registration |
| Schemas/settings | `src/aespa/schemas.py`, `src/aespa/services/settings.py`, `src/aespa/api/settings.py` |
| Policy/broker | new `src/aespa/services/outbound_policy.py`, new `src/aespa/services/request_broker.py` |
| Execution lifecycle | new `src/aespa/services/code_execution.py`, new `src/aespa/services/code_runners/` |
| Traffic | `src/aespa/services/traffic.py`, `src/aespa/api/traffic.py`, API traffic alias routes |
| Agent tools/prompts | `src/aespa/services/prompts/test_lead.py`, `specialist.py`, `alice.py` |
| Agent executors | `src/aespa/services/scanner.py`, `api_scanner.py`, `alice.py`, execution-monitor/checkpoint helpers |
| Cleanup/export | `src/aespa/services/run_cleanup.py`, site/API export/import services |
| Frontend settings | `frontend/src/pages/Settings/`, `frontend/src/lib/policy.jsx` or a separate execution-config helper, API client |
| Frontend traffic | `frontend/src/components/TrafficView.jsx`, web/API traffic tabs, CSS |
| Runtime image | new `runtime/python-executor/` |
| Desktop packaging | `scripts/AESPA.spec`, `scripts/build_mac.sh`, `scripts/build_win.ps1`, frozen path helpers if runtime manifests are bundled |
| Documentation | `docs/architecture.md`, user setup/security documentation, `CHANGELOG.md` at implementation time |
| Tests | traffic, scanner, API scanner, A.L.I.C.E., settings, migration, cleanup, failure injection, frontend, and new runtime isolation suites |

Every non-trivial implementation slice must update `pyproject.toml` using the repository's date/revision versioning rule. This planning document alone does not change the version.

---

## 21. Acceptance Criteria

The feature is complete only when all of the following are true:

1. Generated Python cannot directly reach the target, internet, localhost, LAN, cloud metadata, or host gateway.
2. Generated Python cannot read AESPA's database, repository, host files, environment secrets, target secrets, proxy secrets, or Docker control socket.
3. `aespa_runtime.request()` can perform scoped HTTP(S) requests and useful bounded concurrent batches.
4. Every transmitted Python request—success, HTTP error, timeout, TLS error, connection failure, or cancellation—is visible in the correct web/API Traffic Log.
5. Every traffic row is linked to the exact execution, agent, step, session label, batch position, and declared coverage metadata.
6. Policy-denied attempts are visible in execution details but do not masquerade as network traffic.
7. Scope, method, body, header, redirect, delay, repetition, destructive approval, and request-budget rules are enforced server-side and cannot be relaxed by code.
8. Credentials are referenced by opaque session label and never returned to the sandbox or exposed in code/output/events/traffic display.
9. Binary request/response previews show encoding, original size, and hash; retained full data is bounded and run-owned.
10. Stopping a scan or A.L.I.C.E. cancels queued/running executions and leaves no child process/container behind.
11. Runtime absence or failure produces a clear, bounded tool result and does not fail unrelated scanning.
12. Existing HTTPX, Playwright, WAF, proxy, session, coverage, checkpoint, validation, export, and run-cleanup behaviour passes regression tests.
13. The feature remains disabled by default until runtime readiness succeeds and the operator opts in.
14. Codex/Claude/other provider processes never receive host execution privileges as a side effect of enabling the feature.
15. Desktop builds either support the configured external runtime or clearly report it unavailable; they never silently fall back to unsafe host execution.

---

## 22. Deferred Extensions

These are valuable but should not be folded into the first implementation:

- brokered WebSocket connections with frame-level Traffic Log entries;
- constrained raw HTTP for header ordering, duplicate headers, malformed framing, and request-smuggling research;
- scoped raw TCP/TLS transcripts for non-HTTP services;
- a shared per-run scratch workspace across executions;
- model-selected dependency environments;
- direct browser automation or CDP from Python;
- remote execution pools and multi-tenant scheduling;
- interactive user editing/re-running of generated scripts.

Each extension changes the attack surface and evidence model. In particular, raw protocols need byte-level destination controls and a transcript model rather than pretending they are ordinary `TrafficEntry` HTTP rows.

---

## 23. Recommended First Milestone

Implement Slices 0–3 without exposing the tool to an agent. Demonstrate the following end-to-end test through the fake agent executor:

1. AESPA creates an execution bound to a web run and named session.
2. Network-disabled Python generates a binary payload.
3. Python calls `aespa_runtime.request()` three times through the broker.
4. AESPA injects credentials, validates scope/policy, and sends to a local fake target.
5. Three `source="python"` rows appear in the Traffic Log with execution and binary metadata.
6. An attempted out-of-scope fourth request is denied, appears only in execution policy events, and produces no traffic row.
7. The sandbox cannot contact the fake target directly.
8. Stop/cancellation removes the runtime and marks the execution terminal.

Only after that milestone passes the security regression suite should `execute_python` be added to A.L.I.C.E. and specialist tool allowlists.
