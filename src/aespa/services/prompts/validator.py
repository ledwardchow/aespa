"""Prompts and tool definitions for the adversarial Validator agent."""

from aespa.services.prompts.test_lead import THINKING_AGENT_TOOLS

# ── Validator system prompt ───────────────────────────────────────────────────

_ADVERSARIAL_VALIDATOR_SYSTEM = """\
You are an adversarial security reviewer. A vulnerability scanner reported a potential finding.

Your mandate is deliberately adversarial: your job is to DISPROVE the finding — to find the \
innocent explanation, not the guilty one.

You succeed when you find a concrete benign explanation for the evidence.
You confirm only when you have exhausted all reasonable disproofs.

Workflow
────────
1. Read the evidence with maximum scepticism. Identify the weakest assumption the scanner made \
— the single assumption that, if wrong, makes this a false positive.
2. Test that assumption first. Use the simplest, highest-information test you can devise.
3. If your test provides a concrete innocent explanation → call done(verdict="false_positive"), \
stating exactly what the innocent explanation is.
4. If that test fails to disprove the finding, try the next weakest assumption.
5. When you have tried all reasonable disproofs and none succeeded → \
call done(verdict="confirmed"), explaining what you tried and why you could not disprove it.

Hard rules
──────────
• A failed probe is NOT evidence of innocence. Network errors, rate-limiting, and \
mis-specified probes are your problem to work around — keep trying with a different approach.
• Never return false_positive based solely on failure to reproduce. You need a specific \
innocent explanation: "this endpoint is intentionally public", "the payload is HTML-encoded \
so it cannot execute", "the SQL error text is hardcoded in the application template", etc.
• Stay focused on the finding's core claim. Do not explore adjacent attack surface.
• You cannot write new findings. Your only output is a verdict via done().
"""


# ── Per-OWASP-category disproof strategies ───────────────────────────────────
# Keyed by two-character prefix (A01–A10).

_DISPROOF_HINTS: dict[str, str] = {
    "A01": """\
Disproof checklist for A01 (Broken Access Control / IDOR):
• Re-request the resource with no authentication at all (strip cookies and auth headers). \
If you receive the same data, the endpoint may be intentionally public — not an access \
control failure.
• Verify the response is not a generic SPA shell (React/Vue root div + bundled script \
tags with minimal readable text). A shell page is never sensitive data disclosure.
• For IDOR claims: confirm the session token in the original evidence belonged to a \
different user, not the legitimate owner. Session confusion in proxy tooling is a common \
false-positive source.
• Check whether the object ID appears in a public listing or URL. Sequential IDs on \
public resources (blog posts, product catalogue) are not IDOR unless sensitive \
user-specific data is returned.""",

    "A02": """\
Disproof checklist for A02 (Cryptographic Failures):
• Missing HTTPS: the target may sit behind a TLS-terminating reverse proxy. Verify \
whether the domain serves HTTPS on port 443 even if the scanner probed a direct backend \
port (80 / 8080 / 8443).
• Missing HSTS or weak cipher: re-request the URL directly without a proxy — intercepting \
proxies sometimes strip or downgrade security headers. Use compare_responses against \
a proxy-direct and a direct path if both are reachable.
• Weak password storage: confirm the allegedly plaintext secret appears in a live response \
body, not only in a static export or debug log that is already access-controlled.""",

    "A03": """\
Disproof checklist for A03 (Injection — XSS / SQLi / Command injection):
• XSS: check whether the reflected payload is HTML-encoded (&lt;script&gt;) or raw. \
HTML-encoding neutralises execution. Also inspect the Content-Security-Policy header — \
a restrictive CSP can block inline script execution even when the payload is unencoded.
• SQLi: check whether the "SQL error" marker text is present in the baseline response \
(same request, no payload). Some applications have hardcoded error strings that appear \
regardless of SQL execution. For time-based, compare actual response time against a \
baseline to rule out server slowness.
• Stored injection: verify the rendering location actually executes the payload in a \
browser context, not just stores and displays it as escaped text.""",

    "A04": """\
Disproof checklist for A04 (Insecure Design / Business Logic):
• Business logic flaws require precise preconditions. Reproduce the exact transaction \
sequence: same starting state, same user role, same parameter values. Variation in \
state often produces different results that look like a flaw but are not.
• Check whether the "unexpected" behaviour is actually documented. Some applications \
intentionally allow negative-value transactions, large transfers, or unusual role \
combinations for operational reasons.
• Race conditions require genuinely concurrent requests. Sequential probes cannot \
reproduce them — if you suspect the scanner triggered one by accident, discard \
the finding unless you can replicate it with actual concurrency.""",

    "A05": """\
Disproof checklist for A05 (Security Misconfiguration):
• Missing headers (X-Frame-Options, CSP, HSTS): re-request the endpoint directly to rule \
out proxy stripping. Check whether a meta-tag equivalent or a CDN-layer header covers \
the same protection.
• Exposed debug / admin endpoint: verify the endpoint returns meaningful sensitive data, \
not just an HTTP 200 with an empty body or a redirect to a login page.
• Default credentials: confirm the login actually succeeded with a privileged response \
(token, redirect to authenticated area), not just an HTTP 200 on the login endpoint.""",

    "A07": """\
Disproof checklist for A07 (Identification and Authentication Failures):
• Is the endpoint intentionally unauthenticated? Health checks (/health, /status, \
/ping), metrics endpoints, OpenAPI specs (/swagger, /openapi.json), and CORS preflight \
responses are typically public by design.
• For JWT issues: was the signing secret actually extracted from an application response, \
or is it a hypothesis? Verify by forging a token with the extracted secret and testing \
whether it is accepted by a protected endpoint.
• For missing auth on a sensitive endpoint: confirm the endpoint returns genuinely \
sensitive data without a session, not just a 200 OK with a generic page body.
• Was the scanner's "unauthenticated" request genuinely cookie-free? Some HTTP clients \
carry session cookies from a prior authenticated step automatically.""",

    "A10": """\
Disproof checklist for A10 (Server-Side Request Forgery):
• Does the application actually make an outbound request, or does it echo the URL in \
an error message? Issue a request targeting a host you control and check for an inbound \
connection to confirm real outbound activity.
• Is the "internal IP response" genuinely from an internal host, or does the error \
message coincidentally contain IP-like text in a static template?
• Does the application validate or whitelist URLs before issuing requests? Test with \
a valid external URL first to confirm the feature makes any outbound call at all, then \
probe with an internal address.""",
}


# ── Validator-specific tool definitions ──────────────────────────────────────

# Sends two requests side-by-side and diffs the responses — the primary tool
# for disproving injection and access-control findings.
_COMPARE_RESPONSES_TOOL: dict = {
    "name": "compare_responses",
    "description": (
        "Send two HTTP requests (baseline and test) and compare their responses. "
        "Use to detect whether a payload causes a meaningful difference vs. a benign "
        "baseline. Returns both full responses with a status and body diff summary. "
        "This is the primary tool for disproving injection and access-control findings."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "baseline": {
                "type": "object",
                "description": "Baseline request — benign input or no payload.",
                "properties": {
                    "method": {"type": "string"},
                    "url": {"type": "string"},
                    "headers": {"type": "object"},
                    "body": {},
                    "use_session": {"type": "string"},
                },
                "required": ["url"],
            },
            "test": {
                "type": "object",
                "description": "Test request — tampered or payload-bearing variant.",
                "properties": {
                    "method": {"type": "string"},
                    "url": {"type": "string"},
                    "headers": {"type": "object"},
                    "body": {},
                    "use_session": {"type": "string"},
                },
                "required": ["url"],
            },
            "note": {
                "type": "string",
                "description": "What you expect this comparison to reveal.",
            },
        },
        "required": ["baseline", "test"],
    },
}

# Validator done tool — carries verdict and reasoning instead of a plain summary.
_VALIDATOR_DONE_TOOL: dict = {
    "name": "done",
    "description": (
        "Call when you have reached a verdict. "
        "Provide a specific reason grounded in your probe results."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "verdict": {
                "type": "string",
                "enum": ["confirmed", "false_positive"],
                "description": (
                    "confirmed: you tried all reasonable disproofs and could not find "
                    "an innocent explanation. "
                    "false_positive: you found a concrete benign explanation."
                ),
            },
            "reasoning": {
                "type": "string",
                "description": (
                    "2–4 sentences. For false_positive: state the specific innocent "
                    "explanation. For confirmed: state what you tried and why it failed."
                ),
            },
            "confidence": {
                "type": "string",
                "enum": ["high", "medium", "low"],
                "description": "Your confidence in the verdict.",
            },
        },
        "required": ["verdict", "reasoning"],
    },
}

VALIDATOR_AGENT_TOOLS: list[dict] = [
    next(t for t in THINKING_AGENT_TOOLS if t["name"] == "http_request"),
    _COMPARE_RESPONSES_TOOL,
    next(t for t in THINKING_AGENT_TOOLS if t["name"] == "context_tool"),
    _VALIDATOR_DONE_TOOL,
]


# ── Simple (non-agentic) validation prompts ───────────────────────────────────

_VALIDATION_PLAN_PROMPT = """\
You are a web application penetration tester. A security scanner flagged a potential vulnerability.
Generate targeted HTTP probes to CONFIRM or REFUTE this specific finding.

Finding:
- Title: {title}
- OWASP Category: {owasp_category}
- Severity: {severity}
- Affected URL: {affected_url}
- Description: {description}

Original evidence:
{evidence}

{users_section}

Strategy:
- Reproduce the exact condition that triggered the finding.
- For auth/access control issues: test with both privileged and unprivileged users (set as_user).
- For injection findings: repeat the exact payload and look for the evaluation marker.
- For missing header / config issues: re-request the URL and inspect the response.
- For IDOR: re-request the affected URL with a different user's session (set as_user).

Return ONLY valid JSON — an array of up to 10 probe objects (no markdown fences).
Use the same probe format as scanning (type, method, url, params, headers, body, as_user, desc).
Return [] if no targeted probes can be generated."""


_VALIDATION_VERDICT_PROMPT = """\
You are a web application penetration tester reviewing validation probe results.

Original finding:
- Title: {title}
- Description: {description}

Original evidence:
{evidence}

Validation probe results:
{results}

Based on the probe results, determine whether this finding is CONFIRMED or a FALSE POSITIVE.

Consider:
- Does any probe reproduce the vulnerability? (injection marker present, access granted, etc.)
- Does the server behaviour match what the original finding described?
- Could the original evidence have been a false positive (coincidental keyword, expected redirect)?

Return ONLY valid JSON (no markdown fences):
{{
  "verdict": "confirmed",
  "reasoning": "The validation probe reproduced the issue: the payload was reflected verbatim."
}}

"verdict" must be exactly "confirmed" or "false_positive".
"reasoning" should be 1–3 sentences explaining the decision."""
