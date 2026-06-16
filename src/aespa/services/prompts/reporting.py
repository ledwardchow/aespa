"""Prompts for reporting and finding analysis functions."""


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

Severity levels: critical, high, medium, low, info
OWASP categories: A01 (Broken Access Control), A02 (Cryptographic Failures), \
A03 (Injection), A04 (Insecure Design), A05 (Security Misconfiguration), \
A06 (Supply Chain), A07 (Auth Failures), A08 (Data Integrity), \
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


# ── During-scan writeup replay ────────────────────────────────────────────────

_WRITEUP_REPLAY_PROMPT = """\
You are rewriting a security finding that was written during an agentic web application
penetration test.

Your job is to preserve the technical claim and evidence, but improve the report-ready
writeup. Do not invent new evidence. Do not add vulnerabilities that are not present in
the captured finding.

Captured agent/source: {source}
Target base URL: {base_url}

Original finding JSON:
{finding_json}

Supporting evidence:
{evidence_json}

Return ONLY valid JSON for one finding object, no markdown fences:
{{
  "owasp_category": "A03",
  "title": "Short, report-ready title",
  "description": "What is vulnerable and where.",
  "impact": "What an attacker could achieve.",
  "likelihood": "Practical exploitability in this observed context.",
  "recommendation": "Specific remediation steps.",
  "cvss_score": 6.1,
  "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N",
  "severity": "medium",
  "affected_url": "https://example.com/path",
  "evidence": "Short summary of the exact captured evidence that proves the finding."
}}

Use the original affected_url unless the captured finding clearly contains a more precise
affected URL. Preserve request_evidence and response_evidence only when they are present in
the original finding JSON.

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
