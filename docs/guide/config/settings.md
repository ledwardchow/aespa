# Configuration Settings

AESPA reads a small set of startup environment variables. Other settings are
stored in the database and edited through the application.

LLM connections, models, and scan profiles are covered in
[Setting up LLM providers](llm.md).

## Environment variables

Copy `.env.example` to `.env` if you need to change a startup setting. Every
variable is optional and uses the `AESPA_` prefix.

| Variable | Default | Purpose |
|---|---|---|
| `AESPA_DATABASE_URL` | `sqlite:///./aespa_data/aespa.db` | Database connection string |
| `AESPA_HOST` | `127.0.0.1` | Server bind address |
| `AESPA_PORT` | `8000` | Server bind port |
| `AESPA_AUTH_KEY_FILE` | Not set | Protected file containing the management authentication key, at least 32 characters |
| `AESPA_ALLOWED_HOSTS` | `[]` | Additional accepted hostnames as a JSON list. Localhost and loopback IPs are always accepted. |
| `AESPA_AUTH_COOKIE_SECURE` | `false` | Require HTTPS for browser cookies. HTTPS requests also set secure cookies automatically. |
| `AESPA_CLOUDFLARE_ACCESS_TEAM_DOMAIN` | Not set | Cloudflare Access team domain, such as `myteam.cloudflareaccess.com`. Set with `AESPA_CLOUDFLARE_ACCESS_AUD` to sign in through Cloudflare Access. |
| `AESPA_CLOUDFLARE_ACCESS_AUD` | Not set | Application Audience (AUD) tag of the Cloudflare Access application in front of AESPA. |
| `AESPA_INTEGRATION_PORT` | Not set | Optional second listener for the API extension. Disabled inside Docker. |
| `AESPA_INTEGRATION_HOST` | `127.0.0.1` | Bind address for the optional integration listener |
| `AESPA_WEB_DIR` | `./src/aespa/web` | Compiled frontend directory |
| `AESPA_DATA_DIR` | `./aespa_data` | Databases and uploaded files |

You can also set the data folder from **Console → Settings → Data Folder** in
source runs and the macOS and Windows desktop builds. Restart AESPA after
saving. The folder itself should contain `aespa.db`; AESPA creates a database
for an empty folder and uses existing data without replacing it. Desktop builds
save the choice in a writable application support settings file.

## Sign in to AESPA

The console shows an **Authentication key** beside the listening address.
Press tilde (`~`) or backtick to open an authenticated browser. The console's
**Settings > Authentication key** option also displays the key. Desktop apps sign in
automatically. If you open the address manually, enter the key on the sign-in
screen. In Docker, retrieve the key with `docker compose logs aespa` and open
the published host address and port.

Browsers remember authentication for 30 days at the same hostname and port.
The key and session verification state are saved in `auth.json` under the
data folder and survive restarts. Keep that file and console logs private.
Clearing browser cookies, using a different browser, or changing the key
requires another sign-in. To replace the generated key, stop AESPA, set
`AESPA_AUTH_KEY_FILE` to a protected file with a new key, and restart.

Open **Settings > Authentication key** to show or copy the key. It grants
access to AESPA settings and scan data. Other apps use the API extension's
tokens instead. See [AESPA API](../../api.md) for integration access and the
optional separate listener.

AESPA is designed to run on localhost. Behind an HTTPS reverse proxy,
configure `AESPA_ALLOWED_HOSTS` and set `AESPA_AUTH_COOKIE_SECURE=true`.
Cloudflare Access can still supply a verified display name through
`Cf-Access-Jwt-Assertion`. To let a Cloudflare Access login sign in to AESPA
without the key, set both `AESPA_CLOUDFLARE_ACCESS_TEAM_DOMAIN` and
`AESPA_CLOUDFLARE_ACCESS_AUD`. AESPA then accepts a browser whose Access token
is signed by that team and issued for that application. Anyone your Access
policy allows gets full access to AESPA, so keep the policy narrow. Requests
that do not come through Cloudflare Access still need the key.

## Agent Settings

The **Agent Settings** page is divided into these tabs:

- **Global**: Selects the request policy used by dynamic scans. The default is
  `aggressive`. Other choices are `passive`, `safe_active`, and `destructive`.
  This tab also configures HTTP methods and global HTTP headers. Multiple headers
  can be added. They apply to Playwright and HTTPX traffic, not LLM requests.
- **Crawler**: Controls JavaScript endpoint discovery, action suppression,
  interactive replay safety, access reconciliation, and crawler LLM concurrency.
- **Test Lead**: Controls deterministic checks, execution monitoring, full and
  Standard coverage completion, SAST policy and phase budgets, maximum text-only
  turns, scan steps, request pacing, body limits, allowed schemes, redirects,
  subdomains, browser locator enforcement, and destructive-action approval.
- **Specialist Agents**: Controls dispatch, concurrency, queue size, step budget,
  minimum priority, enabled vulnerability classes, and the optional Burp trigger.
- **Validator**: Controls adversarial validation, severity threshold, step budget,
  concurrency, inline validation, and concrete-disproof requirements.
- **Reporting**: Controls the finding write-up and final reporting stages.
- **Component Mapper**: Sets source, fact, path, confidence, and concurrency limits
  for cross-repository System matching.
- **Python Sandbox**: Enables isolated `execute_python` runs and configures the
  Docker image, allowed agent roles, time and resource limits, output limits,
  request limits, and concurrency.

## Connectivity

Open **Settings > Global > Connectivity** to send scanner traffic, LLM traffic,
or both through an HTTP or HTTPS proxy. Burp Suite settings are on the
**Extensions** page.

The same page accepts optional PEM CA bundle paths for application traffic and
testing traffic. Enter paths on the computer running AESPA. When a path is set,
those requests check the server certificate against that bundle. The bundle
must contain all CA certificates needed for the destinations it will reach.
Model lists, ChatGPT sign-in requests, Benchmark Lab model comparisons, and
result publishing use the LLM proxy and CA bundle settings. Session checks use
the testing proxy and CA bundle. Vulnerable-library list updates use the
testing CA bundle. CLI based LLM providers receive the LLM proxy and CA path
through environment variables, but each CLI decides how to use them.
Browser based tests still accept HTTPS certificate errors.

## System Settings

The **System Settings** page contains feature visibility, debug settings, browser
selection, database operations, and runtime information. Optional Reporting Lab
and Systems entries appear in the sidebar only when enabled. Enable the optional
Benchmark Lab workflow from **Extensions**; its sidebar entry and
`/extension/aespa.benchmarking/` API are present only while it is enabled.

The browser setting can use Playwright Chromium or installed stable Google Chrome.
It can also make normal crawl, scan, and ALICE browser sessions visible for
debugging. Guided login remains interactive regardless of this setting.
