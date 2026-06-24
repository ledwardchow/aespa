# Configuration Settings

AESPA has two kinds of configuration: a handful of **startup environment variables** (read once, on launch) and everything else, which lives in the database and is edited through the **Settings** screens in the UI. LLM provider/model setup has its own page — see [Setting up LLM providers](llm.md). This page covers the rest.

## Environment variables
Copy `.env.example` to `.env` and adjust as needed — all are optional, prefixed `AESPA_`:

| Variable | Default | Purpose |
|---|---|---|
| `AESPA_DATABASE_URL` | `sqlite:///./aespa.db` | SQLite connection string |
| `AESPA_HOST` | `127.0.0.1` | Bind address for the server |
| `AESPA_PORT` | `8000` | Bind port |

If you front AESPA with a Cloudflare Access reverse proxy, the app automatically verifies the `Cf-Access-Jwt-Assertion` header against Cloudflare's JWKS and shows the authenticated username — no extra config needed. There's no built-in auth otherwise; AESPA is designed to run on localhost.

## Agent Settings (Scanner / Specialist Agents / Validator)
**Scanner** tab — `ScannerPolicy`, applies to the dynamic web/API scan:
- **Scan mode**: `passive` (inspect only, no probes), `safe_active` (default — bounded non-destructive probes for XSS/injection/IDOR/auth), `aggressive` (broader fuzzing, higher-risk payloads), or `destructive`
- **Allowed HTTP methods per mode**, **max probes per page**, **max scan steps**, **request timeout**, **min delay between requests**, **max request/response body size**
- **Allowed schemes** (http/https), **blocked headers** (e.g. `host`, `cookie` — never overridden by probes), **follow redirects**, **allow subdomains**
- **Require approval for destructive actions** — pauses the scan for manual confirmation before anything state-changing

**Specialist Agents** tab — `SpecialistAgentConfig`: enable/disable specialist dispatch, max concurrent specialists, max steps per specialist, minimum lead priority to dispatch on, and a per-vulnerability-class toggle (IDOR, auth bypass, SQLi, XSS, business logic, SSRF, path traversal, CORS, crypto, config, file upload).

**Validator** tab — `ValidatorConfig`: enable/disable the adversarial validator, max steps, minimum finding severity it runs on, whether it auto-validates inline, and whether it requires a concrete disproof (vs. just "couldn't reproduce") before downgrading a finding.

## External Integrations (Burp Suite / Upstream Proxy)
**Burp Suite Integration** tab: enable Burp Suite Professional's REST API to run active scans alongside AESPA's own probing. Requires Burp running with the REST API enabled (Burp → Settings → Suite → REST API). Configure the API URL (default `http://127.0.0.1:1337`), API key, and named scan configuration, plus which vulnerability classes Burp should scan for (SQLi, XSS, command injection, path traversal, SSRF, XXE, SSTI). **Test connection** verifies reachability before you rely on it.

**Upstream Proxy** tab: route the scanner's and/or the LLM client's traffic through an upstream HTTP(S) proxy (e.g. Burp's own proxy, for traffic inspection) — set the proxy URL and toggle which traffic flows through it independently.

## Debug page
- **Global Extra HTTP Header** — injects one extra header into every scanner/crawler request (Playwright + HTTPX), not LLM calls. Leave the header name blank to disable. Useful for WAF bypass tokens or environment markers.
- **Specialist Agent** — toggle to force a specialist agent to fire alongside every Burp active scan, for debugging dispatch behavior.
- **Reporting Lab** — captures reporting-agent LLM messages from real scans into a separate SQLite file (not the main DB) and optionally shows a replay lab in the sidebar, for debugging report write-ups.
