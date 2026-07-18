# AGENTS.md

This file provides guidance to Codex and other agentic coding tools when working in this repository.

## What This Is

AESPA (AI-Enabled Security Pentesting Agent) is an LLM-driven automated web-app/API penetration testing tool. It is a FastAPI backend plus a Vite/React frontend that drives multi-agent LLM scans against a target.

AESPA covers three surfaces:

- Web app scanning: crawl plus agentic dynamic scan via Playwright.
- API scanning: parse OpenAPI/Postman/source specs, run an agentic scan, and track OWASP API Top-10 coverage.
- SAST-lite: agentic static analysis over an uploaded source ZIP that seeds leads into the dynamic scan.

The deepest reference for internals is `docs/architecture.md` and it should be read before non-trivial changes to the scan engine, agents, or data model.

## Commands

```bash
uv sync                              # install deps
uv run playwright install chromium   # one-time, required for web crawl/scan
uv run aespa                         # run the server -> http://127.0.0.1:8000

uv run pytest                        # full test suite, in-memory SQLite, no network
uv run pytest tests/test_scanner_service.py            # one file
uv run pytest tests/test_scanner_service.py::test_name # one test
uv run pytest -k "validator and not api"               # by keyword

uv run ruff check .                  # lint (rules: E, F, I; isort enforced)
uv run ruff format .                 # format

cd frontend && npm run build         # build the Vite frontend
```

Requires Python 3.12+ and `uv`.

## Frontend

The frontend is a Vite + React application located in `frontend/`.

When making UI changes:

1. Make UI edits in the Vite JSX files within `frontend/src/`, such as `frontend/src/App.jsx` or files under `frontend/src/pages/`.
2. Do not edit files directly in `src/aespa/web/`; these are generated build artifacts.
3. After completing UI changes, run `npm run build` inside `frontend/`. This rebuild places compiled assets in `src/aespa/web/` so they are served by `uv run aespa`.

Frontend refactoring notes:

- Do not trust Vite builds to catch undefined variables. Bundlers may ignore undefined variable references.
- After moving JSX, extracting components, or changing variable scopes, proactively verify that no undefined variables remain. Use `npx eslint` with `no-undef` enabled, or a custom AST script such as `find_free_vars.js`.
- Prefer true componentization. When breaking down massive components, move associated state, handlers, and `useEffect` logic into child components or specialized hooks. Do not only extract JSX and pass a giant props bag.
- Vite 8 uses `oxc` for transformations. Do not add ignored `esbuild` configuration blocks to `vite.config.js`; use the appropriate Rollup output options instead.
- `package.json` lives in `frontend/`, so run npm commands from that directory or with `--prefix frontend`.

## Configuration

- Runtime config is env-only via `pydantic-settings`, prefix `AESPA_` (see `config.py`): `AESPA_DATABASE_URL`, `AESPA_HOST`, `AESPA_PORT`. Copy `.env.example` to `.env`.
- LLM provider config is not in env. It lives in the DB and is edited through the UI. `LLMProviderConfig` holds reusable connections, keys, and rate limits; `LLMConfig` is a runtime profile selecting a provider and model.
- Supported LLM provider formats include anthropic, openai, openai_compatible, openrouter, google, bedrock, azure_openai, and azure_foundry. The multi-provider client lives in `services/llm.py`.

## Architecture

Request flow:

`main.py` app factory -> `api/*.py` thin FastAPI routers -> `services/*.py` real logic -> SQLModel ORM in `models.py` -> SQLite.

API I/O schemas are in `schemas.py`, separate from ORM models.

The central unit of work is a run:

- A web `TestRun` progresses `created -> crawling -> crawled -> scanning -> scanned`.
- `ApiTestRun` and `SastRun` are parallel run types.
- Each run owns its artifacts: pages, traffic, findings, coverage, logs, and related scan data.

Key service entry points:

- `services/crawler.py`: `start_crawl(run_id)` runs multi-phase Playwright crawling and produces `CrawledPage` plus `TargetIntelItem` intelligence atoms.
- `services/scanner.py`: `start_thinking_scan(run_id)` runs the agentic dynamic scan loop, builds recon context, tracks the OWASP workprogram, dispatches specialists, and deduplicates/reviews findings.
- `services/api_scanner.py`: `start_api_scan(api_run_id)` runs the agentic API scan and tracks OWASP API Top-10 coverage matrix cells in `ApiEndpointTest`.
- `services/sast_scanner.py`: runs the agentic loop over an extracted source ZIP, with file tools path-jailed to the extraction root, and emits `ScanLead`s.
- `services/validator.py`: adversarial validator agent with a disprove-it mandate. It reduces false positives and cannot create findings.
- `services/alice.py` and `services/alice_tasks.py`: A.L.I.C.E., the interactive user-directed pentest chat agent.
- `services/events.py`: SSE/WebSocket event bus for live agent status and UI updates.

Prompt templates for agents live in `services/prompts/`.

## Concurrency

Everything is asyncio. Crawl, scan, SAST, and ALICE jobs run as background `asyncio.Task`s tracked in module-level registries keyed by run ID so they survive HTTP disconnects and can be stopped. ALICE buffers emitted events so reconnecting clients can replay from a cursor.

## Database And Migrations

SQLite via SQLModel, single file `aespa.db` (gitignored; never commit it). Do not inspect it by default, but read-only inspection is allowed when the user explicitly asks to diagnose a local run; use SQLite read-only mode and avoid exposing stored secrets. There is no Alembic. All schema evolution is hand-rolled in `db.py::_migrate()`, run on every startup.

Migration rules:

- New columns are added idempotently via `_ensure_column(engine, table, column, col_def)`.
- New tables use `CREATE TABLE IF NOT EXISTS` blocks inline in `_migrate()`.
- Changing a constraint, such as making a column nullable, on SQLite requires a full table rebuild. Copy the `_ensure_*_nullable` helper pattern.
- All migration steps must be idempotent and best-effort, wrapped so they never block startup.

When adding a field, update the SQLModel in `models.py`, add a matching `_ensure_column(...)` line in `_migrate()`, and update `schemas.py` if it crosses the API boundary.

## Critical Gotcha: Run-ID Collision

Web `TestRun.id` and `ApiTestRun.id` come from independent autoincrement sequences and collide in the same integer space.

Tables shared across both run kinds, such as `agent_log`, `scan_log`, `scanner_session`, and `alice_chat_session`, carry a `run_kind` column (`web` or `api`) that must be filtered on. `scan_finding` keys API findings on `api_test_run_id` with nullable `test_run_id`. Never assume a run ID alone identifies a row's kind.

## Conventions

- Routers stay thin; put logic in `services/`.
- Tests target the service layer and the API through `TestClient`.
- `tests/conftest.py` spins up a fresh in-memory DB per test with a dependency-overridden session.
- All files use `from __future__ import annotations`.
- No external network or live LLM calls in tests. Stub or mock LLM clients.
- The app intentionally has no auth and is localhost-only by design. Optional Cloudflare Access JWT verification in `main.py` is only for users who front it with a reverse proxy. Do not add features assuming a trusted multi-user deployment.
- When interacting with GitHub, use the `gh` command, because the repo may be on a different account than the authenticated GitHub Copilot session.

## Versioning

With every conversation turn that makes non-trivial code changes or fixes a bug, update the version number in `pyproject.toml`. Do not update the version number for documentation-only changes or non-substantive edits where source code logic and dependencies were untouched.

The version format is `MAJOR.MINOR.DATE.REVISION`, where `DATE` is `YYYYMMDD`.

- Leave `MAJOR` and `MINOR` unchanged.
- Set `DATE` to the current date.
- If the existing date is before today, reset `REVISION` to `1`.
- If the existing date is already today, increment `REVISION` by `1`.

Examples:

- New day: `0.5.20261224.7` -> `0.5.20261225.1`
- Same day: `0.5.20261225.5` -> `0.5.20261225.6`
