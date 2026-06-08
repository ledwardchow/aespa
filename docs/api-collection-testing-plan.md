# Plan: API Collection Security Testing

Feature: a new top-level "API Collection" entity (parallel to Site) that ingests API
documentation in multiple formats, runs an LLM-driven readiness assessment ("can I fully
understand & test these APIs?"), itemises every API/endpoint, and drives the existing
thinking-scan + specialist engine against them — tracking OWASP API Security Top 10 (2023)
coverage per endpoint in a matrix.

## Progress tracker
- [x] **Slice 1 — Collections CRUD + "APIs" sidebar + list/create/detail UI** (2026-06-08)
- [x] **Slice 2 — File upload/storage + files manager UI** (2026-06-08)
- [x] **Slice 3 — Document parsing → endpoints populate (3a OpenAPI · 3b Postman · 3c creds · 3d freetext · 3e zip)** (2026-06-08)
- [ ] Slice 4 — Readiness assessment + prerequisites display
- [ ] Slice 5 — API test runs + Agents tab with A.L.I.C.E.
- [ ] Slice 6 — Scanner generalization → run scan, Findings + Traffic tabs
- [ ] Slice 7 — Work Program coverage matrix (track mode) + live updates
- [ ] Slice 8 — Enforce coverage mode

## Decisions (from user)
- OWASP set: **OWASP API Security Top 10 (2023)** (API1 BOLA ... API10 Unsafe Consumption of APIs).
- Placement: **new standalone top-level entity** parallel to `Site`.
- Doc formats v1: **OpenAPI/Swagger (yaml/json), Postman collection, free text/Confluence
  dump (LLM extraction), bearer/credentials file, zip of source code**.
- Engine: **reuse existing thinking-scan + specialist engine, generalize its inputs**
  (new `ApiEndpoint` model becomes an attack-surface unit alongside `CrawledPage`).
- Readiness: **LLM-driven structured gap analysis** (auth method known? creds present?
  sample/test data sufficient?) per-API and overall.
- Coverage mode: **user selects at scan start** — default "track coverage" (observability),
  optional "enforce coverage" (orchestrator drives scan to cover every endpoint x applicable
  category until covered or skipped-with-reason).

## Architecture findings (existing code to reuse / generalize)
- Scanner deeply coupled to `CrawledPage` + `TestRun`:
  - `services/scanner.py`: `start_thinking_scan` L3251, `_do_thinking_scan` ~L3298,
    selects in-scope `CrawledPage` rows at L3549-3551, L6435-6438, L6489-6491;
    creates synthetic `CrawledPage` at L1902-1911; post-scan review `_run_post_scan_llm_review` L3378.
  - `services/task_graph.py`: `build_recon_summary(run_id)` L31 builds attack-surface JSON from
    `CrawledPage` (trust_zones/entry_points/attack_classes) — this is the seam to generalize.
  - `models.ScanFinding.page_id` FK -> CrawledPage; `finding_source` enum; `validation_status` enum.
  - Specialists: `_SPECIALIST_DISPATCH_CLASSES` in scanner.py (incl. file_upload), `agent_dispatch` tool.
  - Sessions/auth: `services/scanner_sessions.py` `upsert_session`/`load_session_vault`;
    `ScannerSession` model (cookies_json, extra_headers_json, token_hint, label, kind).
    Bearer extraction `_extract_bearer_token_from_body` L382; JWT helpers L313/L350.
- Alice (`services/alice.py`, `alice_tasks.py`, prompts/alice.py) bound to a TestRun; reusable as-is.
- API/routing: routers registered in `main.py` L16-23; `Depends(get_session)`; SSE in
  `api/events.py` + `services/events.py` (`emit(run_id, {...})`, persists `scanner_phase`->scan_log).
- DB: SQLite via `db.py`; `init_db()` L33 + `_migrate(engine)` L40-138 adds columns/tables
  idempotently — NEW tables/columns must be added to `_migrate`.
- Frontend: `web/app.js` React18+HTM, hash router (routes table ~L125-145), `api` client
  object ~L15-122, SSE consumption; no build step. `python-multipart>=0.0.27` already present.
- No existing file-upload REST endpoint — must add multipart ingestion endpoint.

## Plan — incremental vertical slices

**Delivery principle:** each slice ships a small piece of backend **together with its UI**, so it
is runnable and testable in the browser before the next slice starts. No big-bang UI at the end.
Each slice ends with an explicit "**Test point**" the user performs manually. Common UI plumbing
(React18+HTM, hash router `app.js` ~L147-160, `api` client object ~L11-122, `tab-bar`/`tab-btn`
~L3500, nav items ~L1177-1200, `SitesList`/`SiteForm`/`SiteDetail`/`TestRunDetail`) is mirrored.

Shared OWASP category set is **OWASP API Security Top 10 (2023)** (see table below). Data-model
rows/columns are added **incrementally per slice** (only the tables/fields that slice needs),
each via an idempotent `db.py::_migrate` addition so existing DBs keep working.

---

### Slice 1 — API Collections CRUD + sidebar + list/create/detail UI ✅ DONE (2026-06-08)
Goal: user can create, view, edit, delete API collections under a new "APIs" sidebar entry.
- **Backend**
  - Model `ApiCollection` (id, name unique, base_url(s)/servers_json, description,
    scope_hosts_json, created_at, updated_at) + `_migrate` create-table.
  - Schemas `ApiCollectionCreate/Summary/Detail` (mirror Site schemas).
  - Router `api/api_collections.py`: `GET/POST /api/api-collections`,
    `GET/PUT/DELETE /api/api-collections/{id}`, `PUT .../scope-hosts`; register in `main.py`.
- **UI**
  - Sidebar "APIs" nav item directly **below "Sites"** (Targets section ~L1178) + `IconApis`.
  - Routes `#/apis`, `#/apis/new`, `#/apis/{id}/edit`, `#/apis/{id}`.
  - `ApiCollectionsList` (mirrors `SitesList`), `ApiCollectionForm` (mirrors `SiteForm`),
    `ApiCollectionDetail` (header + Edit/Delete; **Endpoints section empty-state**; placeholder
    for files/runs buttons wired in later slices).
  - `api.*` client methods: listApiCollections, getApiCollection, createApiCollection,
    updateApiCollection, deleteApiCollection, updateApiScopeHosts.
- **Test point:** open app → click "APIs" → create a collection → see it listed → open it
  (endpoints empty) → edit it → delete it.
- **Automated:** `tests/test_api_collections_api.py` (CRUD, mirror `test_sites_api.py`);
  extend `test_db_migration.py` for the new table.

**Implementation notes (as built):**
- `models.py`: `ApiCollection` table (`servers` + `scope_hosts` stored as JSON strings).
- `db.py::_migrate`: idempotent `CREATE TABLE IF NOT EXISTS api_collection` + unique name index
  (so old DBs gain the table without a full `create_all`).
- `schemas.py`: `ApiCollectionBase/Create/Update/Summary/Detail` (Summary carries
  `endpoint_count`/`document_count`, hard-coded 0 until Slices 2–3 populate them).
- `services/api_collections.py`: CRUD with `ApiCollectionNotFound` / `DuplicateApiCollectionName`.
- `api/api_collections.py`: router registered in `main.py` (after sites router).
- `web/app.js`: `IconApis`, sidebar item, routes, `onApis` active state, render switch,
  `ApiCollectionsList` / `ApiCollectionForm` / `ApiCollectionDetail`, and `api.*` methods.
- Tests: `tests/test_api_collections_api.py` — 14 tests (CRUD, dup-name 409, invalid-URL 422,
  scope-hosts, 404s, migration on old DB). Full suite green (324 passed). Live smoke test of the
  endpoints via real `init_db()`/`_migrate()` confirmed; dev-DB row cleaned up.

---

### Slice 2 — File upload, storage, files manager UI (no parsing yet) ✅ DONE (2026-06-08)
Goal: user can upload docs to a collection, see them listed, download and delete them.
- **Backend**
  - Model `ApiDocument` (id, collection_id FK, filename, doc_type, stored_path, size_bytes,
    status[uploaded|parsed|failed], error_message, created_at) + `_migrate`.
  - Store uploaded bytes on disk under a data dir; keep path. Validate size/type at boundary.
  - Routes: `POST /api/api-collections/{id}/documents` (multipart UploadFile, multi),
    `GET .../documents`, `GET .../documents/{doc_id}/download`, `DELETE .../documents/{doc_id}`.
  - `doc_type` is sniffed/declared at upload (openapi|swagger|postman|freetext|credentials|
    source_zip); parsing deferred to Slice 3 (status stays `uploaded`).
- **UI**
  - Route `#/apis/{id}/files` + `ApiFilesManager` (drag/drop + picker multi-upload; files table
    with type/size/status/date and per-row Download + Delete; back link).
  - "Manage Files" button added to `ApiCollectionDetail`.
  - `api.*`: listApiDocuments, uploadApiDocument (multipart), downloadApiDocument, deleteApiDocument.
- **Test point:** open a collection → Manage Files → upload a couple of files → download one →
  delete one → confirm list updates.
- **Automated:** extend `test_api_collections_api.py` with multipart upload/download/delete +
  safe-path storage assertions.

**Implementation notes (as built):**
- `config.py`: added `data_dir` setting (`AESPA_DATA_DIR`, default `<root>/aespa_data`); added
  `aespa_data/` to `.gitignore`.
- `models.py`: `ApiDocument` (collection_id FK, filename, doc_type, content_type, stored_path,
  size_bytes, status, error_message, created_at). Raw bytes on disk; only metadata in DB.
- `db.py::_migrate`: idempotent `CREATE TABLE IF NOT EXISTS api_document` + collection_id index.
- `schemas.py`: `ApiDocumentOut`.
- `services/api_documents.py`: storage + CRUD. Security: generated uuid filenames (user filename
  never used to build a path → no traversal), 25 MiB cap, empty-file rejection, best-effort
  `_sniff_doc_type` (openapi/swagger/postman/source_zip/credentials/freetext/unknown). Parsing is
  deferred to Slice 3, so `status` stays `uploaded`.
- `api/api_collections.py`: `POST/GET .../documents`, `GET .../documents/{id}/download`,
  `DELETE .../documents/{id}`; `document_count` now wired into the collection summary.
- `web/app.js`: `api.*` (listApiDocuments, uploadApiDocuments[FormData], downloadApiDocument,
  deleteApiDocument), `#/apis/{id}/files` route, `ApiFilesManager` (drag/drop + picker multi-
  upload, files table with type/size/status + Download/Delete, back breadcrumb), "Manage files"
  button on `ApiCollectionDetail`, `fmtBytes` helper.
- Tests: `tests/test_api_collections_api.py` grew to 24 (upload/list/download/delete, zip sniff,
  empty-file 400, 404s, document_count, generated-name/anti-traversal, on-disk cleanup, migration
  asserts `api_document`). Full suite green (334 passed). Live upload/download/delete smoke test
  with isolated `AESPA_DATA_DIR` confirmed.

---

### Slice 3 — Document parsing → endpoints populate (format by format)
Goal: uploading a spec populates the collection's endpoint list. Shipped in **sub-slices per
format** so each is independently testable; UI is the same endpoints table, growing in coverage.
- **Backend (new `services/api_docs.py`)** — `ingest_document(...)` dispatched by `doc_type`;
  dedupe endpoints by (method, normalized path); set `ApiDocument.status=parsed|failed`.
  - Model `ApiEndpoint` (id, collection_id FK, method, path, base_url, operation_id, summary,
    parameters_json, request_body_schema_json, response_schema_json, security_json,
    auth_required, tags_json, sample_request_json, source_doc_id FK, in_scope, created_at) +
    `_migrate`. (prereq_* fields added in Slice 4.)
  - Also `ApiCredential` table introduced here for the credentials parser
    (id, collection_id FK, scheme, name/header, value, label, scope, endpoint_id FK nullable).
  - **3a OpenAPI/Swagger** (yaml/json): walk `paths` → endpoints; capture `securitySchemes` →
    collection `auth_summary_json`; capture example values.
  - **3b Postman collection**: walk `item` tree → endpoints + example requests + auth + variables.
  - **3c Credentials/bearer file**: parse bearer/key:value/curl `-H`/`-b` (reuse crawler
    `parse_curl_command` pattern) → `ApiCredential` rows.
  - **3d Free text / Confluence**: LLM extraction prompt → normalized endpoint list + auth notes.
  - **3e Source zip**: safe-unzip (path-traversal / zip-bomb guards: cap entries, total size,
    reject absolute/`..`) → route-definition heuristics + optional LLM-assisted extraction.
  - Routes: trigger parse on upload (and a manual `POST .../documents/{doc_id}/parse` /
    `POST .../reparse`); `GET .../endpoints`; `PATCH .../endpoints/{eid}/scope`;
    `POST/GET/DELETE .../credentials`.
- **UI**
  - Fill the **Endpoints section** of `ApiCollectionDetail` (method, path, auth required, tags,
    source doc; scope toggle). Files table shows parse status/error per doc.
  - `api.*`: getApiEndpoints, setApiEndpointScope, listApiCredentials, addApiCredential,
    deleteApiCredential, reparseApiDocument.
- **Test point (per sub-slice):** upload an OpenAPI spec → endpoints appear; repeat for Postman,
  a credentials file (creds show up), a free-text doc, and a zip.
- **Automated:** `tests/test_api_docs.py` (per-format parse → expected endpoints; curl/bearer
  parsing; safe-unzip rejects traversal/bomb).

---

### Slice 4 — Readiness assessment + prerequisites display
Goal: user can see, per endpoint and overall, whether there's enough info / auth / test data.
- **Backend (new `services/api_readiness.py`)**
  - Add fields to `ApiEndpoint`: `prereq_can_test`, `prereq_can_test_auth`, `prereq_notes`
    (JSON missing-items) + `_migrate`; add `readiness_json` to `ApiCollection`.
  - `assess_readiness(collection_id)` (LLM-driven, structured): per endpoint + overall →
    auth_method_understood, has_credentials_for_auth, has_sufficient_test_data, missing_inputs[],
    blocking_gaps[], notes, confidence. Cross-checks `securitySchemes` vs `ApiCredential`s/samples.
    Persist to `readiness_json` + endpoint prereq fields; emit progress via events bus.
  - Routes: `POST .../readiness` (async), `GET .../readiness`.
- **UI**
  - "Parse / Refresh Readiness" action on `ApiCollectionDetail`; **understanding panel** (overall
    + per-API gaps, red/green, missing-items list). Endpoints table gains prereq indicators.
  - `api.*`: getApiReadiness, runApiReadiness.
- **Test point:** run readiness on a collection with/without creds → see gaps flip green/red and
  missing-items populate.
- **Automated:** `tests/test_api_readiness.py` (stub LLM → structured JSON; gaps when creds
  missing / no securityScheme / no sample data).

---

### Slice 5 — API test runs + Agents tab with A.L.I.C.E.
Goal: user can create a test run and chat with A.L.I.C.E. against the collection (no scan yet).
- **Backend**
  - Model `ApiTestRun` (id, collection_id FK, name, status, scan_mode, coverage_mode[track|
    enforce], llm_config_id FK, started_at/completed_at, recon_summary_json, token_usage_json,
    error_message) + `_migrate`. Decide backing-run binding (see Further considerations #1):
    recommended separate `ApiTestRun`, with a lightweight bridge exposing the run id that
    Alice/events/agent-log already key on.
  - Routes: `POST /api/api-collections/{id}/test-runs`, `GET .../test-runs`,
    `GET /api/api-test-runs/{id}`. Reuse existing alice/events/agent-log endpoints against the run
    id (add thin `api-test-runs/{id}/alice|events|agent-log` aliases if needed).
- **UI**
  - Routes `#/apis/{id}/runs/new` (`ApiTestRunForm`, mirrors `TestRunForm`) and
    `#/api-runs/{id}/{tab}` (`ApiTestRunDetail`, tab-bar). **Test Runs section** added to
    `ApiCollectionDetail`.
  - First tab **Agents** (`agents`): agent roster + live status feed (reuse `agent-log`/
    `scanner_phase` rendering) **and the A.L.I.C.E. chat panel** (reuse `aliceSession*` machinery
    + Alice API methods, bound to this run id).
  - `api.*`: listApiRuns, createApiRun, getApiRun (+ reuse alice/events methods on the run id).
- **Test point:** create a run → open it → Agents tab → chat with A.L.I.C.E., confirm streaming +
  agent status render.
- **Automated:** extend run-related API tests; smoke test alice alias endpoints.

---

### Slice 6 — Scanner generalization → run scan, Findings + Traffic tabs
Goal: user can start a real scan against the endpoints and see findings + traffic.
- **Backend**
  - `services/attack_surface.py`: `AttackSurfaceUnit` abstraction over `CrawledPage` **or**
    `ApiEndpoint` (id, kind, url, method, params, auth_required, zone, categories).
  - Generalize `task_graph.build_recon_summary` to accept units (CrawledPage path unchanged; add
    ApiEndpoint path → entry_points/attack_classes mapped to OWASP **API** categories).
  - Parameterize scanner selection queries (`scanner.py` L3549-3551, L6435-6491) to load endpoint
    units for an `ApiTestRun`; keep LLM loop/sessions/specialists/validator unchanged.
  - Map ingested `ApiCredential`s → `ScannerSession` (reuse `scanner_sessions.upsert_session`).
  - Extend `ScanFinding` with nullable `api_endpoint_id`, `api_test_run_id`, `owasp_api_category`
    + `_migrate`; finding writes set these for API runs.
  - Wrapper `services/api_scanner.py::start_api_test_run` invokes the generalized engine.
  - Routes: `POST/stop` scan against the run id; reuse findings/traffic/validate endpoints.
- **UI**
  - Add **Findings** and **Traffic Log** tabs to `ApiTestRunDetail` (reuse existing findings and
    traffic components, bound to the run id). Scan start control (scan_mode + LLM profile;
    coverage-mode toggle present but defaults to track — matrix UI lands in Slice 7).
  - `api.*`: reuse getFindings/getTraffic/validate methods on the run id.
- **Test point:** start a scan on a parsed collection → watch traffic populate → see findings
  attributed to endpoints → run validator.
- **Automated:** scanner generalization test (build_recon_summary + unit selection for ApiEndpoint
  without breaking the CrawledPage path; existing scanner tests stay green).

---

### Slice 7 — Work Program coverage matrix (track mode) + live updates
Goal: user sees the per-endpoint × OWASP API category matrix fill in live during a scan.
- **Backend**
  - Model `ApiEndpointTest` (id, api_test_run_id FK, endpoint_id FK, owasp_api_category[API1..10],
    status[not_started|in_progress|covered|skipped|finding], skip_reason, finding_ids_json,
    last_updated) + `_migrate`.
  - Seed matrix at scan start: each in-scope endpoint × applicable category (LLM/heuristic picks
    applicable categories) → `not_started`.
  - Track-mode updates: events subscriber/callback keyed by endpoint+category flips cells to
    in_progress/covered/finding as the scanner emits step/finding events.
  - Schema `ApiCoverageMatrixOut`; route `GET /api/api-test-runs/{id}/coverage`.
- **UI**
  - Add **Work Program** tab (`workprogram`) to `ApiTestRunDetail`: one row per endpoint; columns
    `Endpoint`, `Testable?` (prereq_can_test), `Auth Testable?` (prereq_can_test_auth), then one
    column per **API1..API10** colored by cell status; live via SSE; click cell → related findings;
    header legend + coverage_mode badge.
  - Add **Endpoints** tab (`endpoints`) with per-endpoint prerequisite indicators (from Slice 4).
  - `api.*`: getApiCoverageMatrix. Add matrix cell status colors in `styles.css`.
- **Test point:** start a scan → open Work Program → watch cells move not_started → in_progress →
  covered/finding; click a finding cell.
- **Automated:** coverage matrix endpoint shape test; matrix seeding/update unit test.

---

### Slice 8 — Enforce coverage mode
Goal: user can force the scanner to drive every applicable cell to covered/skipped.
- **Backend**
  - In `api_scanner.py`, **enforce mode** orchestrator loop: iterate remaining `not_started`
    cells, dispatch targeted directives (reuse `agent_dispatch`/specialist or focused thinking
    steps) until covered or marked skipped-with-reason (category N/A), respecting step/time budget.
- **UI**
  - Wire the **coverage-mode toggle** (track [default] / enforce) on the scan start control;
    surface enforce progress in the Work Program header.
- **Test point:** start a scan in enforce mode → confirm previously-uncovered cells get driven to
  covered or skipped-with-reason.
- **Automated:** enforce-loop unit test (drives cells, respects budget, records skip reasons).

## Relevant files
- `src/aespa/models.py` — add ApiCollection, ApiDocument, ApiEndpoint, ApiCredential, ApiTestRun,
  ApiEndpointTest; extend ScanFinding (api_endpoint_id, api_test_run_id, owasp_api_category).
- `src/aespa/db.py` — extend `_migrate` (L40-138) to create new tables + add columns idempotently.
- `src/aespa/schemas.py` — new request/response schemas (mirror Site/TestRun/ScanFinding schemas).
- `src/aespa/services/api_docs.py` (new) — ingestion/parsing per format; safe-unzip; curl parsing.
- `src/aespa/services/api_readiness.py` (new) — LLM structured gap analysis.
- `src/aespa/services/attack_surface.py` (new) — AttackSurfaceUnit builder for page/endpoint.
- `src/aespa/services/task_graph.py` — generalize `build_recon_summary` to accept units; API cats.
- `src/aespa/services/scanner.py` — parameterize CrawledPage selection (L3549-3551, L6435-6491),
  finding-write attribution for API runs; reuse loop/sessions/specialists/validator.
- `src/aespa/services/api_scanner.py` (new) — matrix seeding, coverage tracking/enforcement wrapper.
- `src/aespa/services/scanner_sessions.py` — reuse `upsert_session`/`load_session_vault` for ApiCredential.
- `src/aespa/api/api_collections.py` (new) — REST + multipart upload; register in `main.py` L16-23.
- `src/aespa/services/prompts/` — new prompts: freetext/source extraction, readiness assessment,
  per-endpoint applicable-category selection, API-aware test-lead context (OWASP API Top 10 refs).
- `src/aespa/web/app.js`, `styles.css`, `index.html` — routes, upload UI, readiness panel,
  coverage matrix table, run controls, api client methods.

## OWASP API Security Top 10 (2023) columns
API1 BOLA, API2 Broken Authentication, API3 BOPLA (object property level auth), API4 Unrestricted
Resource Consumption, API5 BFLA (function level auth), API6 Unrestricted Access to Sensitive
Business Flows, API7 SSRF, API8 Security Misconfiguration, API9 Improper Inventory Management,
API10 Unsafe Consumption of APIs.

## Verification
Each slice is verified manually (its **Test point**) **and** with automated tests before moving on;
the full `pytest` suite must stay green at every slice boundary (existing tests never regress).

- **Slice 1:** `tests/test_api_collections_api.py` (CRUD); `test_db_migration.py` new-table check.
  Manual: create/list/edit/delete a collection under "APIs".
- **Slice 2:** extend `test_api_collections_api.py` (multipart upload/download/delete + safe storage).
  Manual: upload/download/delete files.
- **Slice 3:** `tests/test_api_docs.py` (per-format parse -> expected endpoints; curl/bearer parsing;
  safe-unzip rejects traversal/bomb). Manual: upload each format, endpoints appear.
- **Slice 4:** `tests/test_api_readiness.py` (stub LLM -> structured JSON; gaps when creds/scheme/
  sample data missing). Manual: run readiness, see indicators flip.
- **Slice 5:** run-creation API tests + alice alias smoke test. Manual: create run, chat with A.L.I.C.E.
- **Slice 6:** scanner generalization test (build_recon_summary + unit selection for ApiEndpoint
  without breaking the CrawledPage path). Manual: run a scan, see findings + traffic.
- **Slice 7:** coverage matrix endpoint shape + matrix seeding/update unit test. Manual: watch the
  Work Program matrix fill live via SSE.
- **Slice 8:** enforce-loop unit test (drives cells, respects budget, records skip reasons). Manual:
  enforce-mode scan drives uncovered cells to covered/skipped.
- **Final:** full `pytest`; end-to-end manual pass across all slices.

## Scope boundaries
- Included: ingestion (5 formats), readiness assessment, endpoint itemisation, OWASP API Top 10
  per-endpoint coverage matrix, track + enforce modes, reuse of scanner/specialists/Alice/validator.
- Excluded (v1): GraphQL/gRPC-specific schemas; automatic OAuth2 token acquisition flows (creds are
  provided, not negotiated) — note as follow-up; non-HTTP protocols; report-PDF export changes.

## Further considerations
1. Backing run model: keep `ApiTestRun` as its own table vs reuse `TestRun` with a `target_kind`
   column. Recommend separate `ApiTestRun` for clean separation but allow scanner to operate on
   either via the attack-surface abstraction. (A: separate table [rec] / B: reuse TestRun+flag)
2. Secret storage for uploaded tokens/credentials files — store plaintext like existing
   `Credential.password` (local tool convention) but ensure redaction in events/logs/evidence.
3. Source-zip extraction depth — start with route-definition heuristics + LLM assist; deep taint
   analysis is out of scope for v1.
