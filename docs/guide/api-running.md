# Running API Scans

API scanning works on an **API collection** — a named container for the docs, endpoints, and credentials for one API. You set this up once, then start as many test runs against it as you like.

## 1. Create a collection
Go to **APIs → New API collection** and give it a name and base URL. If you already have an export from a previous AESPA setup, use **Import API** instead.

## 2. Add documentation
Open the collection's **Manage files** tab and upload one or more of:
- An **OpenAPI/Swagger** file (JSON or YAML)
- A **Postman collection** export
- A credentials/auth file (bearer token, `key: value` lines, or `curl -H`/`-b` flags)
- Free-text notes describing endpoints (parsed by an LLM)
- A source code ZIP (route-scanned heuristically, optionally LLM-assisted)

Each upload is parsed automatically into `ApiEndpoint` rows (and `ApiCredential` rows, for auth files). If a parse goes wrong, fix the file and click **Parse** again on that document — re-parsing replaces just that document's endpoints.

You can review/toggle which endpoints are in scope on the collection's **Endpoints** tab, and add/edit credentials on **Credentials**.

## 3. Check readiness (optional)
Click **Run readiness check** to have an LLM sanity-check the collection — it flags things like missing auth, unresolved servers, or endpoints with no usable schema, before you spend a scan run on them.

## 4. Start a test run
From the collection page, click **+ New test run**. Pick an LLM profile (or leave it on the global active one) and a **coverage mode**:
- **Track** — records OWASP API Top-10 coverage per endpoint but doesn't block on it
- **Enforce** — keeps the scan going until every in-scope endpoint has been covered

This spins up the same Test Lead / Specialist / Validator agent loop as a web scan, just without a browser — the Test Lead works through endpoints, dispatches Specialists on promising leads, and validates findings. Watch progress on the run's **Status** screen.

You can also drive a run conversationally with **A.L.I.C.E.** the same way as in a web run — see [Running Web Scans](web-running.md#using-alice).

## Working with findings
Findings, the coverage matrix, and the AI Review Issues cleanup work the same as for web scans — see [Working with Findings](web-running.md#working-with-findings).
