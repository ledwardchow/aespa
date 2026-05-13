# Dynamic Scan Tool Calls

## Context tools (`action: "tool"`)

Read-only reconnaissance against collected crawl/scan data. Up to 3 consecutive before the LLM must execute a probe or write a finding.

| Tool | What it returns |
|---|---|
| `site_map` | Filtered list of discovered pages/routes with flags (auth required, takes input, etc.) |
| `page_detail` | Full context, page text, and flags for a specific page |
| `history_search` | Excerpts from prior request/response history matching a query |
| `finding_list` | Findings already written this session, filterable by severity/category |
| `target_inventory` / `search_assets` | Normalised endpoints, forms, inputs, scripts, storage keys, IDs extracted from crawl intelligence |
| `traffic_search` | Captured HTTP request/response log from crawl and scan phases |
| `endpoint_detail` | Consolidated page + intel + traffic + history for one specific URL |
| `compare_responses` | Status, length, similarity, and term deltas between two history steps |
| `mutate_request` | Proposes HTTP probe objects from a prior step via `input_validation`, `idor`, or `business_logic` mutations |
| `auth_matrix` | Endpoints worth testing across anonymous/user/role boundaries |
| `extract_entities` | URLs, paths, IDs, UUIDs, emails, JWT hints, error/debug lines from text or a prior step |

## Action types

| Action | What it does |
|---|---|
| `http` | Issues an arbitrary HTTP request (any method, headers, body, optional session) |
| `browser` | Runs Playwright steps — `goto`, `fill`, `type`, `click`, `press`, `wait`, `snapshot` |
| `jwt` | Forges an HS256 JWT from a discovered signing secret and stores it as a reusable session |
| `credential_check` | Posts a tiny explicit login dictionary (≤ 20 pairs) against a login endpoint; stores successful tokens as sessions |
| `finding_write` | Directly records a confirmed finding from prior evidence without issuing another request |
| `done` | Terminates the scan with a summary |

---

# Structured Scan

The structured scanner runs page-by-page, driven by a plan → execute → analyse loop with deterministic modules layered on top.

## Scan phases

| Phase | Description |
|---|---|
| Site plan | LLM analyses all pages upfront to produce a site-level attack context passed to every per-page scan |
| Per-page: plan probes | LLM plans probes for the page based on applicable OWASP checks (up to 60 probes) |
| Per-page: passive checks | Always runs — fetches page once, inspects headers/cookies without active payloads |
| Per-page: execute probes | Runs all planned + deterministic probes via HTTP client or Playwright |
| Per-page: follow-up probes | LLM reviews initial results and generates up to 20 targeted follow-up probes |
| Per-page: analyse | LLM analyses all results and writes findings; deterministic pattern-matcher runs independently |
| Post-scan: stored XSS sweep | Re-fetches every crawled page looking for the XSS canary injected during probing |
| Post-scan: auth matrix | Checks high-value endpoints anonymously and across credential roles |
| Post-scan: IDOR matrix | Compares object-reference pages across users using crawl ground truth |

## Probe types

| Type | How it runs | Notes |
|---|---|---|
| `http` | Direct HTTP request (any method, params, headers, body, `as_user`) | Used for APIs, URL/query param injection, header checks, JSON body tampering |
| `form` | Playwright browser interaction (selector, payload, submit, `as_user`) | Used when CSRF tokens or JS state are required |
| `idor` | Marks a URL for automatic expansion | Scanner finds peer IDs from other crawled users and tests a ±500 range; do not generate individual http probes per ID |

## Applicable OWASP checks (per page)

| Condition | Checks enabled |
|---|---|
| Always | A02 Cryptographic Failures, A05 Security Misconfiguration, A06 Vulnerable & Outdated Components, A08 Software & Data Integrity Failures, A09 Security Logging & Monitoring Failures |
| Page `req_auth = true` | + A01 Broken Access Control, A07 Identification & Authentication Failures |
| Page `takes_input = true` | + A03 Injection, A10 Server-Side Request Forgery |
| Page `has_object_ref = true` | + A01 Broken Access Control |
| Page `has_business_logic = true` | + A04 Insecure Design |

## Deterministic probes (auto-injected, no LLM)

| Probe set | Condition | What it tests |
|---|---|---|
| Input validation | `takes_input = true` | Injects SQLi, XSS (with canary variants), SSTI, path traversal, SSRF, CMDi payloads into every query parameter (up to 3 params, capped at 30 probes) |
| IDOR expansion | `has_object_ref = true` | Expands one `idor` marker per URL into probes covering peer IDs discovered in the crawl plus a ±500 numeric range |

## Passive checks (run on every page, no payloads)

| Check | What it looks for |
|---|---|
| Security headers | Missing: HSTS, Content-Security-Policy, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy |
| Auth bypass | Same request without cookies/Authorization — expects 401/403 |
| Cookie flags | Each `Set-Cookie` header checked for missing Secure, HttpOnly, SameSite |

## Deterministic findings (pattern-matched, no LLM required)

| Finding | OWASP | CVSS | Trigger |
|---|---|---|---|
| SQL injection error disclosure | A03 | 7.1 | SQL error patterns or 500 status after SQLi probe |
| Reflected cross-site scripting | A03 | 6.1 | Script-capable payload reflected unencoded in response body |
| Server-side template injection | A03 | 8.0 | `{{7*7}}` / `${7*7}` evaluated — `49` appears in response |
| Path traversal file disclosure | A05 | 7.5 | Traversal probe returns `root:x:0:0` |
| Command injection | A03 | 9.1 | `aespa_probe` marker appears in response after CMDi probe |
| Sensitive data in API response | A02 | 6.5 | Response contains field names matching known sensitive patterns (keys, tokens, hashes, debug state) |
| Missing security headers | A05 | varies | One or more security headers absent (from passive check) |
| Cookie attribute issues | A05 | varies | Cookie missing Secure, HttpOnly, or SameSite flag |
| Unauthenticated access to protected endpoint | A01 | 6.5 | Auth matrix: anonymous request to auth-required/sensitive endpoint returns 2xx |
| Unauthorized role access to admin endpoint | A01 | 8.1 | Auth matrix: credential without observed access to an `/admin` endpoint receives 2xx |
| Cross-user IDOR | A01 | 8.0 | IDOR matrix: user B can fetch user A's object-reference page and response contains A's content |
| Stored XSS via canary | A03 | 8.0 | Stored XSS sweep: XSS canary appears unescaped in any crawled page after scan |
