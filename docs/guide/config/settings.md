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
| `AESPA_DATABASE_URL` | `sqlite:///./aespa.db` | Database connection string |
| `AESPA_HOST` | `127.0.0.1` | Server bind address |
| `AESPA_PORT` | `8000` | Server bind port |
| `AESPA_WEB_DIR` | `./src/aespa/web` | Compiled frontend directory |
| `AESPA_DATA_DIR` | `./aespa_data` | Uploaded files and temporary data |

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
  for cross-repository Application matching.
- **Python Sandbox**: Enables isolated `execute_python` runs and configures the
  Docker image, allowed agent roles, time and resource limits, output limits,
  request limits, and concurrency.

## External Integrations

- **Burp Suite Integration**: Connects to Burp Suite Professional's REST API.
  Configure the API URL, API key, named scan configuration, and vulnerability
  classes. **Test connection** checks the configured endpoint.
- **Upstream Proxy**: Sends scanner traffic, LLM traffic, or both through an
  HTTP or HTTPS proxy.

## System Settings

The **System Settings** page contains feature visibility, debug settings, browser
selection, database operations, and runtime information. Optional Reporting Lab,
Benchmark Lab, and Applications entries appear in the sidebar only when enabled.

The browser setting can use Playwright Chromium or installed stable Google Chrome.
It can also make normal crawl, scan, and ALICE browser sessions visible for
debugging. Guided login remains interactive regardless of this setting.
