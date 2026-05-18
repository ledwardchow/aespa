# Plan: JS Sink Analysis + Cross-User Stored XSS

## Context

Aespa's stored XSS detection misses sinks where:
1. The injectable field is in a POST body (not a URL parameter), and
2. The payload only renders in a *different user's* view (cross-user stored XSS).

Root cause: the canary sweep re-fetches crawled pages as the **same authenticated user** who injected, so cross-user rendering is invisible. It also only injects via URL parameters — POST body fields like `description` in `/api/transfers` are never targeted specifically.

Strix found both XSS sinks by reading JS source first, identifying where `innerHTML` concatenations lacked `escapeHtml()`, tracing those variables back to their write endpoints, then verifying via DOM inspection logged in as a victim. This plan adds equivalent capability to Aespa in three parts.

---

## What changes

### Part 1 — `_analyse_js_sinks()` in `scanner.py`

New async function (add after `_stored_xss_sweep` near line 7273).

**Logic:**
1. Load all `TargetIntelItem(kind="script")` rows for the run — these are the JS file URLs discovered by the crawler.
2. Fetch each JS file body via the existing `httpx` client.
3. Regex-scan each body for dangerous rendering patterns:
   ```
   innerHTML|outerHTML|document\.write|insertAdjacentHTML
   ```
4. For each match, extract ±300 chars of surrounding context.
5. Check whether that context contains a sanitizer call:
   ```
   escapeHtml|DOMPurify|sanitize|htmlEncode|encodeHtml|\.escape\(
   ```
6. If **no sanitizer found**: try to extract the variable/field name from the expression
   (e.g. `tx.description`, `entry.notes`, `comment.body`) using a capture group regex.
7. Save one `TargetIntelItem` per unique unsanitized sink:
   - `kind="xss_sink"`
   - `key=field_name` (e.g. `"description"`)
   - `value=js_file_url`
   - `evidence=code_context_snippet`
   - `item_metadata={"js_file": url, "pattern": matched_pattern}`
8. Emit events and surface to the user (see Part 4 below).

**Call site:** Add call in `start_scan()` at line ~5023, before the existing `_stored_xss_sweep` call, passing the same `hx` client and `run_id`.

Also call at the start of `start_thinking_scan()` (line ~2262) so xss_sink items exist in DB when the agentic loop runs, even if the structured scan was skipped. The `_save_intel_item` deduplication already handles re-runs safely.

---

### Part 2 — Extend `_stored_xss_sweep()` for sink-targeted cross-user probes

**Signature change:**
```python
async def _stored_xss_sweep(
    run_id: int,
    hx: httpx.AsyncClient,
    canary: str,
    scanner_policy=None,
    victim_sessions: list[dict] | None = None,   # NEW
) -> None:
```

`victim_sessions` is the list of `cred_sessions` values (already built at line ~4950 in `start_scan()`). Pass the sessions that are NOT the primary attacker session — i.e. secondary credentials, or anonymous.

**New second pass after the existing canary sweep (append inside `_stored_xss_sweep`):**

1. Load all `TargetIntelItem(kind="xss_sink")` for the run.
2. For each sink:
   a. Look up `TargetIntelItem(kind="input", key=sink.key)` → yields the write endpoint URL + method.
   b. Also check `TargetIntelItem(kind="endpoint")` where `evidence` contains the field name as a fallback.
   c. If a write endpoint is found: POST the canary payload to it as the primary (attacker) session:
      ```json
      { "<field_name>": "<canary>" }
      ```
   d. If `victim_sessions` is non-empty: re-fetch crawled pages as each victim session and check for the canary appearing unescaped (same detection patterns as the existing sweep).
3. Any hit → create `ScanFinding` with evidence referencing both the injection request (attacker) and the render response (victim), noting the JS file and code context from the sink item.

**Call site update** in `start_scan()` at line ~5028:
```python
await _stored_xss_sweep(
    run_id, hx, xss_canary,
    scanner_policy=scanner_policy,
    victim_sessions=list(cred_sessions.values())[1:],  # skip primary
)
```

---

### Part 4 — User-visible exposure (two mechanisms)

**A) `scanner_phase` WebSocket event** (live scan log in UI)

After the sink analysis loop completes, emit one event:
```python
events_svc.emit(run_id, {
    "type": "scanner_phase",
    "phase": "js_sink_analysis",
    "status": "complete",
    "message": f"JS sink analysis: found {n} unsanitized innerHTML sink(s)",
    "sinks": [
        {"field": item.key, "js_file": item.value, "snippet": item.evidence[:200]}
        for item in sink_items
    ],
})
```
This appears immediately in the UI's scan log (same channel as "Stored XSS sweep: re-fetching N pages…").

**B) Informational `ScanFinding` per sink** (findings panel in UI)

For each unsanitized sink found, save a `ScanFinding` with:
- `severity="info"`
- `title="Potential stored XSS sink identified in JS source: <field_name>"`
- `description`: the code snippet showing the unescaped `innerHTML` concatenation, plus the JS file URL
- `affected_url`: the JS file URL
- `owasp_category="A03"`
- `finding_source="aespa_scanner"`
- `validation_status="unvalidated"`

This gives the user visibility into what was statically identified *before* dynamic confirmation. The confirmed finding from Part 2 (the canary actually found in a victim's page) is a separate `ScanFinding` at `severity="high"` — so the flow in the UI reads: info → high, matching the static→confirmed progression.

---

### Part 3 — Surface sink intel to the thinking scan agent in `llm.py`

**In the XSS WSTG skill block** (around line 1547), add after the existing JS-file guidance:

```
Before testing XSS dynamically, call context_tool with tool="target_inventory"
and kind="xss_sink". Pre-identified unsanitized innerHTML sinks are listed there
with the field name (key) and the JS file and code context (evidence). For each
sink: find the API endpoint that writes that field (check kind="input" items with
the same key), POST a payload to that endpoint, then verify rendering by browsing
to the page that loads the JS file as a different user session.
```

This makes the `xss_sink` items populated by Part 1 discoverable to the agentic loop without requiring it to re-fetch and re-parse JS source.

---

## Files to modify

| File | Change |
|---|---|
| `src/aespa/services/scanner.py` | Add `_analyse_js_sinks()` (~80 lines including event + info findings); call it from `start_scan()` and `start_thinking_scan()`; extend `_stored_xss_sweep()` signature and add second pass (~50 lines) |
| `src/aespa/services/llm.py` | Add 4-line guidance block to XSS WSTG skill (line ~1547) |

No model changes needed — `TargetIntelItem` already supports arbitrary `kind` values.

---

## Verification

1. Run a scan against bankofed. After the JS sink analysis phase event appears in the UI, query:
   ```
   SELECT kind, key, value, evidence FROM target_intel_item WHERE kind='xss_sink';
   ```
   Expect rows for `description` pointing to `dashboard.js` and `accounts.js`.

2. Confirm the stored XSS sweep finds the cross-user finding:
   - Requires two credentials configured for the site (attacker + victim).
   - Check `scan_finding` table for a finding with title containing "Stored XSS" and evidence referencing `tx.description`.

3. Run `start_thinking_scan` alone (without structured scan). Confirm xss_sink items appear in `target_inventory` response from context_tool.
