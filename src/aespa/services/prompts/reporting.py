"""Prompts for reporting and finding analysis functions."""


# ── Severity calibration (shared fragment, embedded in finding analysis prompts) ─

_SEVERITY_CALIBRATION = """\
Severity calibration:
- Rate generic server or framework version disclosure as info by default, or low if the
  disclosed component is demonstrably obsolete or materially helps exploit a confirmed issue.
- Rate verbose stack traces, file paths, class names, and framework error pages as low by
  default. Raise to medium ONLY when the response exposes high-entropy secrets, credentials,
  or tokens. Do NOT raise to medium for generic database errors, query strings, or schema disclosures.
- Rate CORS arbitrary Origin reflection, including Access-Control-Allow-Credentials: true,
  as low by default unless a browser-based proof shows sensitive authenticated data can be
  read cross-origin. Do not escalate to medium or high solely because Access-Control-Allow-Credentials
  is true.
- Rate missing or weak security headers (Content-Security-Policy, HSTS, X-Frame-Options,
  X-Content-Type-Options, Referrer-Policy, etc.) as low (or info) by default.
- Rate user enumeration (via timing differences or distinct login/forgot-password error messages)
  as low by default.
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
