# AESPA — Copilot Instructions

AESPA (AI-Enabled Security Pentesting Agent) is an LLM-driven automated web-app/API penetration testing tool. FastAPI backend + vanilla-JS SPA. Multi-agent scan engine: Test Lead → Specialist agents + Adversarial Validator + Reporting agent. Three scan surfaces: web app (Playwright crawl + agentic DAST), API (OpenAPI/Postman/source → OWASP API Top-10 matrix), and SAST-lite (agentic source analysis over an uploaded ZIP).

Deepest reference: `docs/architecture.md` (~1100 lines, kept current). Read it before non-trivial changes to the scan engine, agents, or data model.

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
```

Requires Python 3.12+ and `uv`. The frontend is a Vite + React application in `frontend/`.
**UI changes MUST be made in the Vite JSX files within the `frontend/src/` directory.** After making UI changes, you MUST run `cd frontend && npm run build`. This rebuild is critical so that the compiled assets (e.g. index.js / app.js) are placed in `src/aespa/web/` and available to be served when running the backend via `uv run aespa`.

## Architecture

Request flow: `main.py` → `api/*.py` (thin routers) → `services/*.py` (all logic) → SQLModel ORM (`models.py`) → SQLite. API I/O schemas in `schemas.py`, separate from ORM models.

**The central unit of work is a *run*.** Web `TestRun`: `created → crawling → crawled → scanning → scanned`. Parallel run types: `ApiTestRun`, `SastRun`. Each run owns all its artifacts.

Key service entry points:
- `services/crawler.py` — `start_crawl(run_id)`: multi-phase Playwright BFS, LLM-guided. Produces `CrawledPage` + `TargetIntelItem`.
- `services/scanner.py` — `start_thinking_scan(run_id)`: agentic DAST loop. Test Lead LLM picks actions, dispatches Specialists, deduplicates/reviews findings.
- `services/api_scanner.py` — `start_api_scan(api_run_id)`: same loop, no browser, tracks OWASP API Top-10 matrix (`ApiEndpointTest` cells).
- `services/sast_scanner.py` — agentic loop over extracted source ZIP (path-jailed file tools); emits `ScanLead`s.
- `services/validator.py` — adversarial validator (disprove-it mandate); cannot create findings.
- `services/alice.py` + `services/alice_tasks.py` — A.L.I.C.E., interactive pentest chat agent.
- `services/llm.py` — multi-provider LLM client (anthropic, openai, openai_compatible, openrouter, google, bedrock, azure_openai, azure_foundry).
- `services/events.py` — SSE/WebSocket event bus; all agents push `agent_status` events here.

Prompt templates for every agent live in `services/prompts/`.

**Concurrency:** everything is asyncio. Jobs run as background `asyncio.Task`s in module-level registries keyed by run_id. ALICE buffers all events for reconnecting clients to replay from any cursor.

## Configuration

- Runtime: env vars with `AESPA_` prefix via `pydantic-settings` (see `config.py`). Copy `.env.example` → `.env`.
- **LLM provider config is NOT in env** — stored in DB, edited via UI (LLM Settings). `LLMProviderConfig` = connection/keys/rate-limits; `LLMConfig` = runtime profile (provider + model).

## Database & Migrations

SQLite via SQLModel, single file `aespa.db` (gitignored). **No Alembic.** All migrations are hand-rolled in `db.py::_migrate()`, run on every startup.

Rules:
- New columns: `_ensure_column(engine, table, column, col_def)` — idempotent.
- New tables: `CREATE TABLE IF NOT EXISTS` inline in `_migrate()`.
- Making a column nullable on SQLite requires a full table rebuild — copy the `_ensure_*_nullable` helper pattern.
- All migration steps must be idempotent and best-effort (never block startup).

**When adding a field:** update SQLModel in `models.py` + add `_ensure_column(...)` in `_migrate()` + update `schemas.py` if it crosses the API boundary.

## Critical Gotcha: Run-ID Collision

`TestRun.id` and `ApiTestRun.id` come from independent autoincrement sequences and **collide in the same integer space**. Tables shared across both run kinds (`agent_log`, `scan_log`, `scanner_session`, `alice_chat_session`) carry a `run_kind` (`'web'`/`'api'`) column — **always filter on it**. `scan_finding` keys API findings on `api_test_run_id` (nullable `test_run_id`). Never assume a run_id alone identifies a row's kind.

## Conventions

- Routers stay thin; logic goes in `services/`.
- All files use `from __future__ import annotations`.
- Tests use `TestClient` with in-memory SQLite (see `tests/conftest.py`). No network, no live LLM calls — stub/mock everything.
- No auth by design (localhost-only). Don't add features assuming multi-user deployment.
- With every conversation turn that makes non-trivial changes or fixes a bug, update the version number in pyproject.toml. The version is `MAJOR.MINOR.DATE.REVISION` where DATE is `YYYYMMDD`. Leave MAJOR (first number) and MINOR (second number) alone. Set DATE to the current date. For REVISION (the last number): if DATE changed (the existing date is before today), reset REVISION to 1; if DATE is unchanged (already today), increment REVISION by 1. Examples: on a new day `0.5.20261224.7` → `0.5.20261225.1`; same day `0.5.20261225.5` → `0.5.20261225.6`.

## When interacting with Github

- use the gh command to interact with Github, as the repo will likely be on a different account than the authenticated Github Copilot session.
