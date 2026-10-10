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
| `AESPA_WEB_DIR` | `./src/aespa/web` | Compiled frontend directory |
| `AESPA_DATA_DIR` | `./aespa_data` | Databases and uploaded files |

You can also set the data folder from **Console → Settings → Data Folder** in
source runs and the macOS and Windows desktop builds. Restart AESPA after
saving. The folder itself should contain `aespa.db`; AESPA creates a database
for an empty folder and uses existing data without replacing it. Desktop builds
save the choice in a writable application support settings file.

AESPA has no built-in user authentication and is designed to run on localhost.
When it is placed behind Cloudflare Access, it verifies the
`Cf-Access-Jwt-Assertion` header and displays the verified username.

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

## Upstream Proxy

Open **Settings > Global > Upstream Proxy** to send scanner traffic, LLM traffic,
or both through an HTTP or HTTPS proxy. Burp Suite settings are on the
**Extensions** page.

The same page accepts optional PEM CA bundle paths for LLM calls and scanner
HTTP requests. Enter paths on the computer running AESPA. When a path is set,
those requests check the server certificate against that bundle. The bundle
must contain all CA certificates needed for the destinations it will reach.
Benchmark Lab model comparisons use the LLM proxy and CA bundle settings.
Browser based tests still accept HTTPS certificate errors. CLI based LLM
providers use their own certificate settings.

## System Settings

The **System Settings** page contains feature visibility, debug settings, browser
selection, database operations, and runtime information. Optional Reporting Lab
and Systems entries appear in the sidebar only when enabled. Enable the optional
Benchmark Lab workflow from **Extensions**; its sidebar entry and
`/extension/aespa.benchmarking/` API are present only while it is enabled.

The browser setting can use Playwright Chromium or installed stable Google Chrome.
It can also make normal crawl, scan, and ALICE browser sessions visible for
debugging. Guided login remains interactive regardless of this setting.
