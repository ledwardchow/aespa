# AESPA extension API

This document describes the extension interface implemented by AESPA extension API `1`. The implementations in `src/aespa/extensions/runtime.py`, `src/aespa/services/sast_sources.py`, and `src/aespa/services/external_scans.py` define the behavior if this document and the code differ.

## What an extension can provide

An extension is trusted Python code loaded inside the AESPA process. API `1` supports:

| Capability | What the extension supplies | What AESPA handles |
| --- | --- | --- |
| `sast.source_provider` | A source provider that prepares a ZIP of code for a SAST run | Run creation, background preparation, archive validation, storage, and scan startup |
| `web.active_scanner` | A scanner that selects web scan candidates and returns issues | Target scope checks, scheduling, cancellation, activity events, and finding storage |

An extension may also register settings fields without either capability. Extensions do not add API routes, database tables, migrations, or frontend code through this interface. Extensions run with AESPA's process permissions, so only install code you trust.

## Folder and manifest

Place an extension in either of these layouts under a bundled or user extension root:

```text
extensions/<extension_name>/extension.toml
extensions/<author>/<extension_name>/extension.toml
```

AESPA checks exactly these two depths. It does not search deeper folders. Bundled extensions live in the repository's `extensions/` folder or its desktop bundle. User extensions live in AESPA's application data `extensions/` folder, unless `AESPA_EXTENSIONS_DIR` overrides that location. The two bundled implementations are `extensions/builtin/github_repository/` and `extensions/builtin/burp_suite/`.

Put the Python entrypoint and any files it imports inside the extension directory. AESPA loads the entrypoint as a package, so relative imports such as `from .provider import MyProvider` work. The entrypoint path must resolve to a file inside the extension directory. AESPA discovers added or changed files on its next start.

Example `extension.toml`:

```toml
id = "acme.repository"
name = "Acme repository"
author = "acme"
version = "1.0.0"
aespa_api = "1"
entrypoint = "extension.py:create_extension"
capabilities = ["sast.source_provider"]
secrets_namespace = "repository"
enabled_by_default = false
```

| Key | Rule |
| --- | --- |
| `id` | Required. Must be unique across all discovered extensions and match `^[a-z][a-z0-9_.-]{1,79}$`. This ID, not the folder path, keys saved settings and enabled state. |
| `aespa_api` | Required. Must be the string `"1"`. |
| `name` | Display name. Defaults to the ID. |
| `author` | Optional author name shown in the Extensions table and settings page. If the extension uses secrets, it is required and must match the ID pattern above. It does not have to match the author folder name. |
| `version` | Extension version shown in the UI. Defaults to `0.0.0`. |
| `entrypoint` | `file.py:callable` within the extension directory. Defaults to `extension.py:create_extension`. |
| `capabilities` | List of capabilities the extension offers. Declare `web.active_scanner` before registering a web scanner. Declare `sast.source_provider` for a source provider. |
| `secrets_namespace` | Required if any setting has type `secret`. Give a value matching the ID pattern above. AESPA prefixes it with `author`, so this example stores secrets in `acme.repository`. The full name must be unique across extensions. |
| `enabled_by_default` | Boolean. Defaults to `true`. A saved enable or disable choice takes precedence. |

The manifest ID and folder names can differ. Keep the ID, author, and secret namespace value stable when moving an extension so its saved settings and secrets remain available. Duplicate IDs or full secret namespaces produce a load error in the Extensions list. One failed extension does not stop the others.

If an extension is disabled, AESPA records its manifest but does not import its Python entrypoint or register its capabilities. Enabling or disabling it reloads the extension registry. Disabling a web scanner also cancels its active AESPA tasks.

## Entrypoint and registration

The entrypoint callable returns an object with `register(registry)`. Registration is synchronous. For example:

```python
from .provider import AcmeProvider


class AcmeExtension:
    def register(self, registry):
        registry.register_source_provider(AcmeProvider())


def create_extension():
    return AcmeExtension()
```

The registry supports `register_source_provider(provider)`, `register_web_active_scanner(scanner)`, and `register_settings_fields(fields, schema_version=1)`. `registry.secrets` provides the extension's declared secret namespace. A source provider or scanner can declare its own `settings_fields`; do not register the same key twice. Provider IDs must be unique among source providers, and scanner IDs among web scanners.

## Settings fields and secrets

Import field definitions from `aespa.extensions`:

```python
from aespa.extensions import SourceProviderField

SourceProviderField(
    key="api_url",
    label="API URL",
    type="text",
    required=True,
    placeholder="https://example.test/api",
    help="Address of the local integration service.",
    default="https://example.test/api",
)
```

`SourceProviderField` accepts `key`, `label`, `type`, `required`, `placeholder`, `help`, `default`, and `options`. `options` is a list of `{ "value": "...", "label": "..." }` objects for a `select` field. Supported types are `text`, `path`, `number`, `boolean`, `select`, and `secret`. Keys for fields registered directly with `register_settings_fields` must match the ID pattern. All settings keys in one extension must be distinct.

The Extensions UI uses field metadata to render controls. Non-secret settings are stored by extension ID and returned through `context.settings`. A field's `default` is display metadata; extension code should also supply a fallback when it reads an unset setting, for example `context.settings.get("enabled", True)`. `settings_schema_version` and `schema_version` are stored with settings, but API `1` does not run an extension settings migration. Unknown saved keys remain in storage but are not passed through `context.settings`.

Secret fields require `author` and `secrets_namespace` in the manifest. AESPA uses `<author>.<secrets_namespace>` as the full storage namespace and returns that name in the extension API. Read a secret with `context.secrets.get("api_key")`; `registry.secrets` offers the same namespace during registration. Both stores support `get`, `has`, `set`, and `delete`. Secret keys use the same ID pattern. The API returns only `has_secrets` flags, not secret values. A null secret update keeps its existing value; an empty string removes it. Stored secrets are in AESPA's local database without encryption at rest. Never include credentials in ordinary settings, request parameters, results, metadata, errors, or logs.

## SAST source provider contract

Register a provider with `registry.register_source_provider(provider)`. Its interface is:

```python
from aespa.extensions import (
    MaterializedSource,
    ProviderAvailability,
    SourceProviderDescriptor,
    SourceProviderField,
)


class AcmeProvider:
    descriptor = SourceProviderDescriptor(
        id="acme.repository",
        label="Acme repository",
        description="Prepare source from an Acme repository.",
        request_fields=[SourceProviderField("repository", "Repository", required=True)],
        settings_fields=[],
        settings_schema_version=1,
    )

    async def check_availability(self, context):
        return ProviderAvailability(True, "ready", "Repository source is ready.")

    async def materialize(self, parameters, destination, context):
        archive = destination / "source.zip"
        # Create archive from parameters and validate the requested repository.
        return MaterializedSource(
            archive_path=archive,
            display_name="acme-repository",
            locator="https://example.test/acme/repository",
            requested_ref=None,
            revision="immutable-revision-id",
            metadata={},
        )
```

`check_availability(context)` returns `ProviderAvailability(available, status, message, details={})`. AESPA calls it when listing providers, before creating a run, and again before preparation. Keep it quick. `request_fields` describe controls for each new SAST run; the provider must validate `parameters` itself.

`materialize(parameters, destination, context)` runs asynchronously and returns `MaterializedSource`. Write a ZIP file to `archive_path` under the supplied working directory. `display_name` becomes the saved filename; `locator`, `requested_ref`, `revision`, and JSON-compatible `metadata` become run provenance. AESPA extracts and repacks the archive as an immutable snapshot. It rejects missing or invalid archives, more than 10,000 entries, individual source files over 50 MiB, and total extracted or stored source over 250 MiB. Do not put credentials in the archive or provenance fields.

The context has `extension_id`, `settings`, and `secrets`. `find_executable(setting, names)` finds a configured executable or one on `PATH`. `run_process(argv, cwd=..., timeout=..., env=...)` runs a command without a shell and requires an absolute executable path in `argv[0]`. It disables interactive Git prompts, applies a 300 second default timeout, limits captured stdout and stderr to 128 KiB each, and monitors a supplied working directory against a 1 GiB default limit. Handle nonzero `ProcessResult.returncode` and cancellation in provider code.

## Web active scanner contract

Declare `web.active_scanner` in the manifest and call `registry.register_web_active_scanner(scanner)`. The scanner must provide `id`, `label`, `description`, `settings_fields`, `settings_schema_version`, and these methods:

```python
from aespa.extensions import ProviderAvailability, WebScanCandidate, WebScanResult


class AcmeScanner:
    id = "acme.scanner"
    label = "Acme scanner"
    description = "Run targeted checks with Acme."
    settings_fields = []
    settings_schema_version = 1

    def candidate_from_finding(self, finding, settings):
        # Return None when this finding does not need a scan.
        return WebScanCandidate(
            url=finding["affected_url"],
            title=finding["title"],
            vulnerability_class="SQL Injection",
            finding_id=finding.get("id"),
            page_id=finding.get("page_id"),
        )

    def candidate_from_investigation(self, tool_input, note, settings):
        return None

    async def check_availability(self, context):
        return ProviderAvailability(True, "configured", "Scanner is configured.")

    async def scan(self, candidate, context):
        task_id = "external-task-id"
        context.on_started(task_id)
        # Run or poll the external scanner here.
        return WebScanResult(task_id=task_id, issues=[])
```

Candidate selection is synchronous. AESPA passes finding data or an HTTP investigation note and the saved settings to the selection methods. Return `None` to skip a candidate. `WebScanCandidate` also accepts `specialist_attack_class` if a specialist agent should run alongside the external scanner. AESPA checks the candidate URL against the web run's scope and suppresses another scan for the same run, scanner ID, vulnerability class, and URL.

`scan(candidate, context)` is asynchronous. `WebScanContext` includes `extension_id`, `settings`, `secrets`, captured `cookies`, `extra_headers`, and `on_started(task_id)`. Treat cookies and headers as sensitive. Call `on_started` after the external task starts, then return `WebScanResult(task_id, issues)`. Each `WebScanIssue` requires `title`, `affected_url`, and `severity`; it can include `description`, `recommendation`, `confidence`, `request_evidence`, `response_evidence`, and `owasp_category` (default `A03`). AESPA discards out-of-scope issues, skips an existing finding with the same URL and title, and persists the rest. Evidence is stored with the finding.

AESPA calls `check_availability(context)` when listing the extension. A scanner may also implement `check_connection(context)` for the Settings page's Check connection action. Keep the normal availability check cheap; use `check_connection` for a live network probe. AESPA cancels the scan coroutine when the run stops or the extension is disabled. Let `asyncio.CancelledError` propagate and clean up any external task if your scanner needs to.

## Bundled implementations

The `aespa.githubrepository` source provider accepts `owner/repository` or a `github.com` URL with an optional branch, tag, or commit. It prefers an authenticated GitHub CLI and otherwise uses Git with the user's credential helper. It creates a bare filtered clone, resolves the selected ref to a commit, and archives tracked files without a normal checkout. It does not include Git submodules or Git LFS object contents. Repository preparation runs in the background. If AESPA stops during preparation, the run is marked failed on the next start instead of repeating the authenticated operation.

The `aespa.burpsuite` web scanner is disabled by default. It uses the Burp Suite Professional REST API, takes its API key from the `aespa.burpsuite` secret namespace, and selects candidates by vulnerability class. AESPA migrates saved Burp connection details, scan choices, and API keys to this extension during database upgrade. Its code is in `extensions/builtin/burp_suite/`.

## Testing and packaging

- Test discovery from the intended folder depth, registration, disabled behavior, settings and secret handling, and each capability's failure and cancellation paths.
- Stub external services in tests. AESPA's tests do not require live LLM calls or live third-party scanners.
- Keep runtime assets inside the extension directory. Desktop builds copy the bundled `extensions/` tree, including author folders. Additional Python dependencies or dynamically imported packages may need changes to AESPA's desktop packaging scripts.
- See `extensions/builtin/github_repository/` and `extensions/builtin/burp_suite/` for working implementations.
