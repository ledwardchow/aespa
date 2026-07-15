# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

AESPA (AI-Enabled Security Pentesting Agent) is an LLM-driven automated web-app/API penetration testing tool. It is a FastAPI backend + vanilla-JS SPA that drives multi-agent LLM scans (a Test Lead agent that spawns Specialist agents, an Adversarial Validator, and a Reporting agent) against a target. It covers three surfaces: **web app** scanning (crawl + agentic dynamic scan via Playwright), **API** scanning (parse OpenAPI/Postman/source specs → agentic scan, OWASP API Top-10 coverage matrix), and **SAST-lite** (agentic static analysis over an uploaded source ZIP that seeds leads into the dynamic scan).

The deepest reference for internals is `docs/architecture.md` (~1100 lines, kept current). Read it before non-trivial changes to the scan engine, agents, or data model.

## Commands

```bash
uv sync                              # install deps
uv run playwright install chromium   # one-time, required for web crawl/scan
uv run aespa                         # run the server → http://127.0.0.1:8000

uv run pytest                        # full test suite (~475 tests, all in-memory SQLite, no network)
uv run pytest tests/test_scanner_service.py            # one file
uv run pytest tests/test_scanner_service.py::test_name # one test
uv run pytest -k "validator and not api"               # by keyword

uv run ruff check .                  # lint (rules: E, F, I — isort enforced)
uv run ruff format .                 # format

cd frontend && npm run build         # build the Vite frontend

```

Requires Python 3.12+ and `uv`. The frontend is a Vite + React application located in `frontend/`. 

**When making UI changes:**
1. Make all UI edits in the Vite JSX files within the `frontend/src/` directory (e.g., `frontend/src/App.jsx`, `frontend/src/pages/`).
2. Do NOT edit files directly in `src/aespa/web/` (these are generated build artifacts).
3. After completing UI changes, you MUST run `npm run build` inside the `frontend/` directory. This rebuild is critical so that the compiled assets (e.g. index.js / app.js) are placed in `src/aespa/web/` and available to be served when running the backend via `uv run aespa`.

## Configuration

- Runtime config is env-only via `pydantic-settings`, prefix `AESPA_` (see `config.py`): `AESPA_DATABASE_URL`, `AESPA_HOST`, `AESPA_PORT`. Copy `.env.example` → `.env`.
- **LLM provider config is NOT in env** — it lives in the DB and is edited through the UI (LLM Settings). `LLMProviderConfig` holds reusable connections/keys/rate-limits; `LLMConfig` is a runtime profile selecting a provider + model. Supported formats: anthropic, openai, openai_compatible, openrouter, google, bedrock, azure_openai, azure_foundry*. The multi-provider client lives in `services/llm.py`.

## Architecture

Request flow: `main.py` (app factory, mounts routers + SPA) → `api/*.py` (thin FastAPI routers) → `services/*.py` (all real logic) → SQLModel ORM (`models.py`) → SQLite. API I/O schemas are in `schemas.py`, kept separate from ORM models.

**The central unit of work is a *run*.** A web `TestRun` progresses `created → crawling → crawled → scanning → scanned`. An `ApiTestRun` and a `SastRun` are parallel run types. Each run owns all its artifacts (pages, traffic, findings, coverage, logs).

Key service entry points:
- `services/crawler.py` — `start_crawl(run_id)`: multi-phase (unauth first, then one phase per credential), parallel Playwright workers, LLM-guided BFS. Produces `CrawledPage` + `TargetIntelItem` intelligence atoms.
- `services/scanner.py` — `start_thinking_scan(run_id)`: the agentic dynamic scan loop. Builds a recon summary, tracks the OWASP workprogram, then loops giving the Test Lead LLM a toolset to decide each action. Dispatches specialists and dedups/reviews findings here.
- `services/api_scanner.py` — `start_api_scan(api_run_id)`: same agentic loop without a browser, tracks the OWASP API Top-10 coverage matrix (`ApiEndpointTest` cells).
- `services/sast_scanner.py` — agentic loop over an extracted source ZIP (file tools path-jailed to the extraction root); emits `ScanLead`s.
- `services/validator.py` — adversarial validator agent with a disprove-it mandate; reduces false positives. Cannot create findings.
- `services/alice.py` + `services/alice_tasks.py` — A.L.I.C.E., the interactive user-directed pentest chat agent.

**Multi-agent model** (all emit `agent_status` SSE events, all appear in the Agents UI panel): Test Lead (one continuous session) → spawns Specialist agents (narrow mission, `asyncio.Task`, cannot recursively dispatch) on high-confidence leads, and the Adversarial Validator after each finding is written. Reporting agent does a post-scan pre-screen. Prompt templates for every agent live in `services/prompts/`.

**Concurrency:** everything is asyncio. Crawl/scan/SAST jobs run as background `asyncio.Task`s tracked in module-level registries keyed by run_id (e.g. `_specialist_tasks`, `_sast_tasks`, ALICE's `_registry`) so they survive HTTP disconnects and can be stopped. ALICE buffers all emitted events so a reconnecting client can replay from any cursor.

**Real-time UI:** the SPA gets live updates over a WebSocket/SSE event stream emitted by `services/events.py` (`api/events.py` router). Background agents push status; the frontend (`web/app.js`) renders the Agents/Findings/Traffic/Task-graph panels.

## Database & migrations (important)

SQLite via SQLModel, single file `aespa.db` (gitignored, ~480MB locally — do not read or commit it). **There is no Alembic.** All schema evolution is hand-rolled in `db.py::_migrate()`, run on every startup:
- New columns are added idempotently via `_ensure_column(engine, table, column, col_def)`.
- New tables are `CREATE TABLE IF NOT EXISTS` blocks inline in `_migrate()`.
- Changing a constraint (e.g. making a column nullable) on SQLite requires a full table rebuild — see the `_ensure_*_nullable` helpers as the pattern to copy.
- All migration steps must be **idempotent and best-effort** (wrapped to never block startup).

When adding a field: update the SQLModel in `models.py`, add a matching `_ensure_column(...)` line in `_migrate()`, and update `schemas.py` if it crosses the API boundary.

**Run-id collision gotcha:** web `TestRun.id` and `ApiTestRun.id` come from independent autoincrement sequences and *collide in the same integer space*. Tables shared across both run kinds (`agent_log`, `scan_log`, `scanner_session`, `alice_chat_session`) carry a `run_kind` (`'web'`/`'api'`) column you MUST filter on, and `scan_finding` keys API findings on `api_test_run_id` (nullable `test_run_id`). Never assume a run_id alone identifies a row's kind. See memory `aespa-run-id-collision`.

## Conventions

- Routers stay thin; put logic in `services/`. Tests target the service layer and the API via `TestClient` (`tests/conftest.py` spins up a fresh in-memory DB per test with a dependency-overridden session).
- All files use `from __future__ import annotations`.
- No external network or live LLM calls in tests — LLM clients are stubbed/mocked.
- This app intentionally has **no auth** and is localhost-only by design; the optional Cloudflare-Access JWT verification in `main.py` is only for users who front it with a reverse proxy. Don't add features assuming a trusted multi-user deployment.
- With every conversation turn that makes non-trivial changes or fixes a bug, update the version number in pyproject.toml. The version is `MAJOR.MINOR.DATE.REVISION` where DATE is `YYYYMMDD`. Leave MAJOR (first number) and MINOR (second number) alone. Set DATE to the current date. For REVISION (the last number): if DATE changed (the existing date is before today), reset REVISION to 1; if DATE is unchanged (already today), increment REVISION by 1. Examples: on a new day `0.5.20261224.7` → `0.5.20261225.1`; same day `0.5.20261225.5` → `0.5.20261225.6`.
