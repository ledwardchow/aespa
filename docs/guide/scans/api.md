# API Scanning - Screen Walkthrough

This guide describes the screens and workflow for setting up and running API scans in AESPA.

## API Collections Landing Page

Navigate to **APIs** in the main navigation bar to access the API Collections screen:

![API setup screen](../images/apisetup.png)

This page lists all created API collections. Each collection represents a container for an API's documentation files, endpoints, credentials, and scan history.

- **New API collection**: Opens a modal to create a collection with a name, base URL, and optional description.
- **Import API**: Imports a previously exported AESPA API collection JSON file.
- **Export**: Generates a downloadable JSON file containing the collection's endpoints, credentials, documentation, and scan history.

Clicking a collection row opens the collection management view.

---

## Collection Management

Inside a collection, the interface provides four tabs:

### 1. Manage Files

The **Manage files** tab handles documentation upload and ingestion:

![Parsed API spec screen](../images/apispecparsed.png)

You can upload:
- **OpenAPI / Swagger specs**: JSON or YAML files detailing API endpoints, methods, parameters, and schemas.
- **Postman collections**: Exported Postman JSON files.
- **Credentials and auth files**: Plain text or JSON files containing tokens, API keys, or curl header definitions.
- **Unstructured documentation**: Markdown, text files, or notes containing endpoint paths or descriptions.
- **Source code ZIP**: Source code archives for automated route discovery.

Each uploaded document is parsed automatically by an LLM parser into `ApiEndpoint` and `ApiCredential` records. If a document changes, re-uploading or clicking **Parse** updates the endpoints associated with that file.

### 2. Endpoints

The **Endpoints** tab lists all parsed API endpoints:
- Filter endpoints by method (GET, POST, PUT, DELETE, etc.) or search by path.
- Toggle individual endpoints **in scope** or **out of scope**.
- Inspect parsed parameter schemas, request body shapes, and expected response codes.

### 3. Credentials

The **Credentials** tab manages authentication headers and tokens for the API:
- Add, edit, or remove authentication keys, bearer tokens, or basic auth headers.
- Assign credentials to specific roles (e.g. `admin`, `user`, `read-only`) for authorization testing.

### 4. Test Runs

The **Test Runs** tab lists all scan runs performed against this collection.

Click **+ New test run** to start a scan:
- Select an **LLM Profile** (or use the active default profile).
- Select a **Coverage mode**:
  - **Track**: Records OWASP API Top-10 coverage as endpoints are tested without forcing full coverage before completion.
  - **Enforce**: Continues the scan until every in-scope endpoint has been tested against applicable OWASP API checks.

---

## Run Status and Scan Progression

When a test run starts, AESPA displays the run status view:

![API Scan Findings](../images/apifindings.png)

During an API scan:
- The **Test Lead** agent navigates the endpoint inventory and issues targeted HTTP requests.
- **Specialist Agents** dispatch automatically on identified attack leads (e.g. BOLA/IDOR, BFLA, injection).
- The **Adversarial Validator** tests reported vulnerabilities to disprove false positives.

### OWASP API Top-10 Coverage

The **OWASP Coverage** tab displays the live matrix of API endpoint coverage across the OWASP API Top-10 categories:

![OWASP Coverage for API Scanning](../images/apiworkprogram.png)

Each cell shows whether an endpoint has been tested for a specific vulnerability class (BOLA, Broken Auth, Mass Assignment, etc.) and highlights identified findings.

---

## Working with API Findings

The **Findings** tab displays all security issues identified during the scan:
- View severity ratings, affected endpoints, CVSS scores, and reproduction evidence.
- Click **AI Review Issues** to prompt A.L.I.C.E. to deduplicate findings and re-verify severity ratings.
- Interact with **A.L.I.C.E.** in the run panel for interactive testing, custom probe requests, or manual review of specific endpoints.
