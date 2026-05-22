"""Prompts for reporting and analysis functions (page analysis, probe planning, findings)."""

# ── Page analysis (crawler recon) ─────────────────────────────────────────────

_ANALYSIS_PROMPT = """\
You are a web application security analyst performing reconnaissance on a target web application.

Analyse the following web page and return a JSON response.

URL: {url}
Title: {title}

Page content:
{text}

Return ONLY valid JSON in this exact format (no markdown fences):
{{
  "context": "2-4 sentence description of the page's purpose and the functionality it offers to users",
  "suggested_links": ["absolute_url_1", "absolute_url_2"],
  "categories": {{
    "req_auth": true,
    "takes_input": false,
    "has_object_ref": false,
    "has_business_logic": false
  }}
}}

For suggested_links: include up to 10 absolute URLs that appear as actual links on this page \
(same domain) and reveal the most important or interesting application functionality. Do not \
construct, guess, rewrite, or substitute URLs from IDs/account numbers visible in page text. \
Prefer links to forms, features, user actions, admin areas, API endpoints, etc. over navigation \
links already visible on every page.

For categories — answer true/false to each:
- req_auth: Does accessing or using this page require the user to be authenticated/logged in?
- takes_input: Does this page contain forms, input fields, search boxes, or otherwise accept data from the user?
- has_object_ref: Does the URL or page content reference a specific object by ID \
(e.g. id=1 in a query param, /accounts/42/ in the path, or a resource identifier in a POST body)?
- has_business_logic: Can this page trigger transactions, modify account data, transfer funds, \
create/update/delete records, or perform other business-significant operations?"""


# ── Probe planning ────────────────────────────────────────────────────────────

_PLAN_PROMPT = """\
You are a web application penetration tester. Given the page details below, generate a list \
of HTTP probes to test for OWASP Top 10 vulnerabilities.

URL: {url}
Title: {title}
LLM Context: {context}
{site_context_section}
Page categories:
- Authentication Required: {req_auth}
- Takes User Input: {takes_input}
- Contains Object Reference: {has_object_ref}
- Contains Business Logic: {has_business_logic}

Applicable OWASP checks: {applicable}

{users_section}
{category_guidance}
{xss_canary_section}
Return ONLY valid JSON — an array of probe objects (no markdown fences):
[
  {{
    "type": "http",
    "method": "GET",
    "url": "https://...",
    "params": {{}},
    "headers": {{}},
    "body": null,
    "as_user": null,
    "desc": "Brief description of what this probe tests"
  }},
  {{
    "type": "form",
    "url": "https://...",
    "selector": "input[name='search']",
    "payload": "<script>alert(1)</script>",
    "submit_selector": "button[type=submit]",
    "as_user": null,
    "desc": "XSS in search field"
  }},
  {{
    "type": "idor",
    "url": "https://app.com/users/42",
    "as_user": "bob",
    "desc": "IDOR on user ID tested as low-privilege user"
  }}
]

General rules:
- Maximum 60 probes total. Prefer more targeted input-validation probes over repeating the same
    authorization/IDOR pattern. If you cannot include everything, preserve coverage in this order:
    SQL injection, XSS, object-reference tampering, authentication/authorization bypass, then other checks.
- "http" probes: sent directly via HTTP client (auth bypass, header checks, URL/query param injection, JSON/form body tampering, SSRF).
- "form" probes: require browser interaction (form input injection where CSRF tokens are needed).
- "idor" probes: mark a URL that contains an object ID for IDOR testing. Use ONE per URL — the \
scanner automatically finds peer IDs from the crawl and tests a ±500 range. \
Do NOT generate individual http probes for each sequential ID.
- Object references are not limited to REST-style path IDs. When testing authorization or IDOR, inspect and mutate IDs in:
    - path segments such as /accounts/42 or /api/users/7;
    - GET query parameters such as ?id=42, ?accountId=42, ?user_id=7;
    - request bodies for POST/PUT/PATCH/DELETE, including JSON objects, nested JSON objects/arrays, and form-like fields.
- For query-string IDs, put mutated values in the "params" object or in the URL query string.
- For JSON body IDs, put a JSON object/array in "body" and include "Content-Type": "application/json" in "headers" when appropriate.
- "as_user": set to a username from the available test users list to send the probe authenticated \
as that specific user. Set to null to use the primary session. Use this for authorization bypass \
testing — e.g. send a request as a low-privilege user to an endpoint that should be admin-only.
- For auth bypass probes: include a version with empty Cookie and Authorization headers.
- For injection probes, generate multiple payload variants per discovered input. Do not stop after one
    generic payload. Cover reflected, stored-like, encoded, quote-breaking, numeric, boolean, and timing cases
    where relevant. Keep payloads safe and non-destructive.
    - SQLi boolean/string: ' OR '1'='1'--  /  " OR "1"="1"--  /  admin'--
    - SQLi numeric: 1 OR 1=1--  /  0 OR 1=1  /  -1 OR 1=1
    - SQLi error/union/order: ' UNION SELECT NULL--  /  1' ORDER BY 999--  /  ' AND extractvalue(1,concat(0x7e,version()))--
    - SQLi timing: 1 AND SLEEP(1)--  /  '; WAITFOR DELAY '0:0:1'--  /  1); SELECT pg_sleep(1)--
    - XSS HTML/script: <script>alert(1)</script>  /  "><script>alert(1)</script>
    - XSS attribute breakouts: "><img src=x onerror=alert(1)>  /  ' autofocus onfocus=alert(1) x='
    - XSS SVG/event: <svg onload=alert(1)>  /  <details open ontoggle=alert(1)>
    - XSS encoded/url contexts: javascript:alert(1)  /  %3Cscript%3Ealert(1)%3C/script%3E
  - SSTI: {{7*7}}  /  ${{7*7}}
  - Path traversal: ../../../etc/passwd  /  ..%2F..%2Fetc%2Fpasswd
  - SSRF: http://169.254.169.254/latest/meta-data/
  - CMDi: ; echo aespa_probe  /  $(echo aespa_probe)
- Do NOT generate probes for checks not in the applicable list.
- Only generate probes relevant to this specific page."""


# ── Severity calibration (shared fragment, embedded in finding analysis prompts) ─

_SEVERITY_CALIBRATION = """\
Severity calibration:
- Rate generic server or framework version disclosure as info by default, or low if the
  disclosed component is demonstrably obsolete or materially helps exploit a confirmed issue.
- Rate verbose stack traces, file paths, class names, and framework error pages as low by
  default. Raise to medium only when the response exposes secrets, credentials, tokens,
  exploitable SQL details, or sensitive user/business data.
- Rate CORS arbitrary Origin reflection, including Access-Control-Allow-Credentials: true,
  as low by default unless a browser-based proof shows sensitive authenticated data can be
  read cross-origin. Raise only when the evidence demonstrates real data exposure or account
  impact, not merely permissive headers.
- Do not rate informational disclosure as medium or high solely because it is remotely
  reachable. Severity should follow demonstrated impact, not theoretical chaining.
"""


# ── Probe result analysis / finding generation ────────────────────────────────

_ANALYSE_PROMPT = """\
You are a web application penetration tester reviewing probe results for OWASP vulnerabilities.

Page URL: {url}

Probe results:
{results}

For each result, determine whether it indicates a real vulnerability. Consider:
- Unexpected data disclosure (other users' data, admin data)
- Injection indicators (SQL errors, reflected payloads, template evaluation)
- Auth bypass (200 on a protected resource without credentials)
- Misconfiguration (missing security headers, verbose errors, version disclosure)
- SSRF responses (cloud metadata, internal IP responses)

Return ONLY valid JSON — an array of findings (empty array [] if none found, no markdown fences):
[
  {{
    "owasp_category": "A03",
    "title": "Reflected XSS in search parameter",
    "description": "The search parameter reflects user input without encoding.",
    "impact": "An attacker could execute JavaScript in a victim's browser and act as that user.",
    "likelihood": "Likely when attacker-controlled links can be delivered to authenticated users.",
    "recommendation": "Encode output by context, validate input, and add regression tests for this parameter.",
    "cvss_score": 6.1,
    "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N",
    "severity": "medium",
    "affected_url": "https://example.com/search?q=<script>alert(1)</script>",
    "evidence": "Short summary of the exact request and response evidence that proves the finding."
  }}
]

The "affected_url" must be the exact URL from the probe result that triggered this finding (copy it verbatim from the probe results above).
Write each finding using the report headings represented by these JSON fields:
- description: what is vulnerable and where.
- impact: what an attacker could achieve.
- likelihood: practical exploitability in this observed context.
- recommendation: specific remediation steps.

Score every finding using CVSS v3.1. Provide both cvss_score and cvss_vector.
Set severity from cvss_score: critical 9.0-10.0, high 7.0-8.9,
medium 4.0-6.9, low 0.1-3.9, info 0.0.

{severity_calibration}

Severity levels: critical, high, medium, low, info
OWASP categories: A01 (Broken Access Control), A02 (Cryptographic Failures), \
A03 (Injection), A04 (Insecure Design), A05 (Security Misconfiguration), \
A06 (Vulnerable Components), A07 (Auth Failures), A08 (Data Integrity), \
A09 (Logging/Monitoring), A10 (SSRF)

Be conservative — only report confirmed or highly likely issues, not theoretical ones.
If many findings are present, return the most important confirmed findings first. Keep each field
concise enough for a security report table/detail view; do not include raw full responses when a
short quoted excerpt proves the issue."""


# ── Site-level test plan ──────────────────────────────────────────────────────

_SITE_PLAN_PROMPT = """\
You are a senior web application penetration tester preparing a security assessment.

Below is a summary of all pages discovered during crawling of the target web application.
Analyse the attack surface, reason through the application's architecture, and produce a
structured test plan with specific, actionable vulnerability hypotheses.

Target base URL: {base_url}

Discovered pages ({page_count} total):
{pages_summary}

Consider:
- What kind of application is this? (auth model, user roles, key data objects)
- What are the highest-value attack targets? (admin panels, financial operations, \
ID-bearing endpoints, privileged actions)
- What systemic vulnerabilities are likely based on the observed structure and page categories?
- What cross-endpoint attack chains deserve testing? For example: auth bypass by calling a \
final step directly without going through a gated check step; IDOR across resource types; \
privilege escalation by sending a lower-privilege token to an admin endpoint.

Return ONLY valid JSON in this exact format:
{{
  "app_summary": "2-3 sentence description of the application, its key roles, and security-relevant features",
  "attack_hypotheses": [
    {{
      "hypothesis": "Short label for this attack scenario",
      "description": "What to test, why it may be vulnerable, and which endpoints are involved",
      "target_pages": ["partial URL or pattern"],
      "owasp": "A01"
    }}
  ],
  "critical_areas": ["URL pattern or page type that deserves the most thorough testing"],
  "test_notes": "Specific techniques, IDs, credentials, header patterns, or sequences the scanner should use"
}}

Limit to the 8 most valuable attack hypotheses. Be specific and actionable."""


# ── Follow-up probe planning ──────────────────────────────────────────────────

_FOLLOWUP_PROMPT = """\
You are a senior web application penetration tester reviewing mid-scan probe results.

You have just run an initial set of probes against the page below and received the results.
Your task is to reason through what you observe, identify any promising leads, and generate
targeted follow-up probes that would confirm, deepen, or chain from the potential issues.

Page URL: {url}
Page context: {context}

Site-level test plan context:
{site_context}

Initial probe results:
{initial_results}

Think through:
- Which results look anomalous or potentially vulnerable? (unexpected 200s on restricted pages, \
error messages that disclose stack traces or internals, reflected or stored payloads, \
differing responses for different input values, auth bypass indicators)
- For each interesting result, what follow-up probe would confirm or rule out the issue?
- Are there attack chains implied by multiple results together? In particular:
  • If a check/validate/verify endpoint responded saying something is required (e.g. TOTP, pin,
    2FA code, elevated privilege), probe the corresponding action endpoint DIRECTLY without
    providing that requirement, to test whether enforcement is server-side or only client-side.
  • If a response revealed a new endpoint URL, resource ID, token, or parameter — probe it.
  • If a check returned requires_X: true but the action endpoint is not yet probed — add a probe
    calling the action endpoint with the required field absent or empty.
- Did any response reveal new endpoints, IDs, tokens, or parameters worth testing?

Generate targeted follow-up probes. Prefer quality over quantity — a focused probe testing a
specific hypothesis is more valuable than re-running broad coverage.

Return ONLY valid JSON — an array of follow-up probe objects (max 20, return [] if no leads):
[
  {{
    "type": "http",
    "method": "GET",
    "url": "https://...",
    "params": {{}},
    "headers": {{}},
    "body": null,
    "as_user": null,
        "interesting_result": "Specific response status/body/header/behavior that made this worth following up",
        "hypothesis": "Specific vulnerability or enforcement behavior this probe is testing",
        "payload_purpose": "What the generated URL/body/header payload is intended to confirm or rule out, or null",
    "desc": "Follow-up: what this tests and why"
  }}
]

Return [] if no results look promising enough to warrant follow-up investigation.
Do not use vague wording like "looked interesting" without naming the exact signal and hypothesis."""


# ── Finding title normalisation ───────────────────────────────────────────────

_NORMALIZE_TITLES_PROMPT = """\
You are deduplicating security findings from a web application penetration test report.

EXISTING confirmed findings for this test run:
{existing_list}

NEW candidate findings just discovered (normalize these):
{new_list}

Rules:
- If a new finding is the same vulnerability class as an existing one (same OWASP category \
and root cause, possibly on a different URL), set its title to EXACTLY the existing title.
- If two new findings in this batch are the same class, give them the SAME title (pick the \
clearest one).
- If a new finding is genuinely different, keep its title as-is.
- Do NOT merge or drop findings — return one entry per new finding.

Return ONLY a JSON array, one object per new finding in the same order:
[{{"index": 0, "title": "..."}}, ...]
"""


# ── Finding deduplication ─────────────────────────────────────────────────────

_DEDUPLICATE_FINDINGS_PROMPT = """\
You are de-duplicating security findings from a web application penetration test.

Findings below are candidate duplicates because they share the same vulnerability
class and host target: {target}

Candidate findings (sorted by severity):

{findings_text}

Decide which findings are substantially the same issue in substance and target.

Rules:
- Group findings when a knowledgeable human security reviewer would collapse them into one
  report finding.
- Treat differing object IDs, account numbers, UUIDs, record references, or example values as
  duplicates when the vulnerability/root cause and target functionality are the same.
- Titles and writeups may differ; judge by vulnerability class, root cause, affected
  functionality, impact, and recommended fix.
- Do NOT group findings that affect different URL paths or parameters — XSS on
  /search and XSS on /login are separate vulnerable endpoints that must remain as
  separate findings even if they share the same vulnerability class.
- Do NOT group findings that are different vulnerability classes, different target
  functionality, or require meaningfully different remediation.
- Only include groups with at least two finding ids.

Return ONLY valid JSON in this exact format:
{{
  "duplicate_groups": [
    {{"ids": [1, 2], "reason": "short explanation"}}
  ]
}}
"""


# ── Global cross-target fingerprinting ───────────────────────────────────────

_FINGERPRINT_PROMPT = """\
You are classifying security findings from a web application penetration test.

For each finding below, assign a short canonical "vulnerability fingerprint" that
captures:
  1. Vulnerability CLASS  (e.g. xss, sqli, idor, csrf, ssrf, broken-auth, ssti, xxe)
  2. Root-cause MECHANISM (e.g. reflection, stored, blind, missing-check, misconfig)
  3. Affected FUNCTIONALITY (e.g. login, search, user-profile, file-upload, admin-panel)

Findings that represent the SAME underlying vulnerability — even when found on
different URLs or paths — MUST receive IDENTICAL fingerprints.

For example, reflected XSS found on /search and on /login should both get
"xss:reflection:user-input" if the root cause is the same unescaped reflection.

Findings (sorted by severity):

{findings_text}

Return ONLY valid JSON:
{{
  "fingerprints": [
    {{"id": 1, "fingerprint": "xss:reflection:user-input"}},
    {{"id": 2, "fingerprint": "xss:reflection:user-input"}},
    {{"id": 3, "fingerprint": "sqli:error-based:login-form"}}
  ]
}}
"""
