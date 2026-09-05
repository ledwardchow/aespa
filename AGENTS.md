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

uv run pytest                        # full suite, in-memory SQLite; requires local ports
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

1. Make UI edits in the Vite JSX files within `frontend/src/`, such as `frontend/src/app/App.jsx` or files under `frontend/src/features/`.
2. Do not edit files directly in `src/aespa/web/`; these are generated build artifacts.
3. After completing UI changes, run `npm run build` inside `frontend/`. This rebuild places compiled assets in `src/aespa/web/` so they are served by `uv run aespa`.

Frontend refactoring notes:

- Do not trust Vite builds to catch undefined variables. Bundlers may ignore undefined variable references.
- After moving JSX, extracting components, or changing variable scopes, proactively verify that no undefined variables remain. Use `npx eslint` with `no-undef` enabled, or a custom AST script such as `find_free_vars.js`.
- Prefer true componentization. When breaking down massive components, move associated state, handlers, and `useEffect` logic into child components or specialized hooks. Do not only extract JSX and pass a giant props bag.
- Vite 8 uses `oxc` for transformations. Do not add ignored `esbuild` configuration blocks to `vite.config.js`; use the appropriate Rollup output options instead.
- `package.json` lives in `frontend/`, so run npm commands from that directory or with `--prefix frontend`.

### Frontend layout and visual QA

- Reusable tab bars depend on their parent layout. For example, Attack Surface and Coverage use `.activity-sub-tab-bar` with `.coverage-sub-tab-bar` inside a full-width wrapper. Do not copy only the child tab classes into a padded container.
- The Agent Settings page has padded content: its scroll area has 16px top padding and the content column has 16px left padding. A full-width inner tab bar must be a sibling above the overflowed scroll area, or live inside a wrapper that owns the full-bleed layout. Negative margins inside `.scroll-content` do not work because its `overflow-x: hidden` clips the bar. Otherwise dark gutters appear along the top or left edge.
- When changing a nested tab bar or panel, inspect the computed bounds of the bar and its parent after the build. Check the real route in a screenshot at desktop width and confirm that the bar reaches the same edges as its surrounding panel before finishing.

## Configuration

- Runtime config is env-only via `pydantic-settings`, prefix `AESPA_` (see `config.py`): `AESPA_DATABASE_URL`, `AESPA_HOST`, `AESPA_PORT`. Copy `.env.example` to `.env`.
- LLM provider config is not in env. It lives in the DB and is edited through the UI. `LLMProviderConfig` holds reusable connections, keys, and rate limits; `LLMConfig` is a runtime profile selecting a provider and model.
- Supported LLM provider formats include anthropic, openai, openai_compatible, openrouter, google, bedrock, azure_openai, and azure_foundry. The multi-provider client lives in `services/llm.py`.
- Provider model discovery: Endpoint `GET /api/llm/models` dynamically discovers models for SDK-backed providers (e.g. `factory_droid`, `github_copilot`) via provider clients (`droid_provider.discover_models()`, `copilot_provider.discover_models()`) while preserving `PROVIDER_DEFAULT_MODELS` as fallback choices.

## Sandbox Execution Notes

- Plan test permissions before running commands. The full backend suite includes tests that bind and connect to local ports in `tests/test_desktop_server.py` and `tests/test_main_startup.py`. These need loopback access even though tests make no external network or live LLM calls.
- When the sandbox restricts local ports, request the required access on the first invocation of the full suite or either of those test files. With `exec_command`, use `sandbox_permissions="require_escalated"` and explain that the tests open local loopback ports. Do not run them in the restricted sandbox first just to confirm the known failure.
- Apply the same rule to `npm run test:e2e`, direct Playwright browser tests, and Vite dev/preview servers. The browser test configuration starts a server on `127.0.0.1:5179`; both the server and browser test process need the appropriate access. An already-running server does not establish that a sandboxed test process can reach it.
- If access is unavailable or denied, run the remaining backend tests with `uv run pytest --ignore=tests/test_desktop_server.py --ignore=tests/test_main_startup.py` and report the omitted tests as unverified. Do not silently skip them or describe that result as a full-suite pass. Do not retry the same blocked command without a permission change.
- Tests that only use in-process FastAPI `TestClient`, and frontend lint, type checks, unit tests, and builds, do not need loopback access by default. Keep those commands sandboxed unless there is a separate known requirement.
- When inspecting Python virtual environments or installed packages under sandbox mode, `uv run` may attempt network fetches and `python` binaries managed by `pyenv` may trigger `dyld` file sandbox blocks on `~/.pyenv/versions/`. Prefer inspecting `.venv` package source files directly via `view_file`, `grep_search`, or lightweight string/JSON scripts (e.g. Node/Python tools without `pyenv` dynamic library linkage) before requesting sandbox bypass.

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

SQLite via SQLModel, single file `aespa.db` (gitignored; never commit it). Do not inspect it by default, but read-only inspection is allowed when the user explicitly asks to diagnose a local run; use SQLite read-only mode and avoid exposing stored secrets. Schema evolution is managed via **Alembic**.

Migration workflow for schema changes:

1. Update the SQLModel definition in `models.py`.
2. Generate an Alembic revision script via autogenerate:
   ```bash
   uv run alembic revision --autogenerate -m "describe_change"
   ```
3. Inspect and verify the generated script in `alembic/versions/`.
4. Update `schemas.py` if the change crosses the API boundary.
5. `init_db()` in `db.py` automatically runs `command.upgrade(cfg, "head")` on startup. Legacy databases lacking an `alembic_version` table are automatically stamped with the baseline revision.

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

## Desktop Launchers & PyInstaller Builds

When adding new runtime dependencies, backend frameworks, data assets, or modifying desktop launchers (`src/aespa/desktop.py`, `src/aespa/desktop_win.py`) and PyInstaller scripts (`build_mac.sh`, `build_win.ps1`, `AESPA.spec`):

1. **Dynamic Runtime Assets & Migration Configs**: Any runtime configuration files, database migration directories (e.g. `alembic.ini`, `alembic/`), static assets, templates, or non-Python files read by the app must be explicitly bundled in PyInstaller scripts (`build_mac.sh`, `build_win.ps1`, `AESPA.spec`) via `--add-data`. All backend path resolvers (e.g. `_get_alembic_config` in `src/aespa/db.py`) must check `sys.frozen` / `sys._MEIPASS` when frozen before falling back to repo-relative paths (`Path(__file__).resolve().parents[...]`).
2. **Framework & Dynamic Import Collection**: Any third-party package loaded via dynamic string imports, reflection, plugin systems, or ASGI/WSGI servers (e.g. `alembic`, `uvicorn`, `playwright`, `webview`) must be explicitly bundled using `--collect-all <package>` or `--collect-submodules <package>`. In desktop launcher scripts (`desktop.py`, `desktop_win.py`), avoid string-based target resolution (e.g. `"aespa.main:app"`) and pass explicit module/object references (e.g. `uvicorn.Config(app, ...)`).
3. **Fail-Fast Thread & Port Verification**: Background server threads (`_serve()`) must trap startup exceptions into a shared variable, and port polling functions (`_wait_port()`) must re-raise thread errors immediately or raise `TimeoutError` on deadline. Never allow `_wait_port()` to return cleanly when backend startup fails, as launching webviews on dead ports causes silent white screens.

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

## Changelog Writing

Automatically add or update entries under `## Unreleased` in `CHANGELOG.md` when implementing changes. Do not wait for a separate request to write release notes.

Group entries under these headings, in this order:

- `### New features`: New capabilities or workflows users can access.
- `### Updates`: Improvements to existing features or changes to their behaviour.
- `### Fixes`: Corrections to broken or incorrect behaviour.
- `### Housekeeping`: Refactoring, dependency updates, build and release maintenance, tests, and documentation.

Omit empty categories. Place each change in the category that best describes it. Split entries that combine unrelated changes or changes belonging to different categories, and avoid repeating the same change across categories.

When updating `CHANGELOG.md`, write for users rather than implementation specialists:

- Use clear, professional release-note language consistent with the surrounding changelog entries.
- Lead with what changed and what it means for the user.
- Prefer familiar product terms over internal architecture, provider-protocol, or code-level terminology.
- Keep technical detail only when it helps users understand behaviour, compatibility, configuration, or risk.
- Avoid casual phrasing, promotional language, and repetitive sentence patterns that make the entry sound machine-generated.
- Do not include source file paths or internal function and class names unless they are genuinely useful to the intended reader.
- Preserve existing changelog text unless the user explicitly asks for it to be revised.
