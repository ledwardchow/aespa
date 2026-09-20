# AESPA extensions

AESPA extensions are trusted Python code loaded when the application starts. An extension contributes a supported capability through AESPA's registry. It does not add database migrations, API routes, or frontend JavaScript.

The first supported capability is a SAST source provider. Source providers resolve code into an immutable ZIP. AESPA validates and stores that ZIP, records its provenance, and passes it to the existing SAST scanner.

## Extension folder

AESPA loads one extension from each subdirectory of its extensions folders:

- Shipped extensions: `<repository>/extensions/` in a source checkout, or the bundled `extensions` directory in a desktop build
- User extensions in a packaged desktop app: the `extensions` folder in AESPA's application data directory
- User extension override: `AESPA_EXTENSIONS_DIR`

The Extensions page lists every discovered extension and shows load errors. Use its checkboxes to enable or disable an extension immediately. Adding or changing files in the extensions folder still requires an AESPA restart. Extension code has the same permissions as AESPA, so only install code you trust.

## Manifest

Each extension needs `extension.toml`:

```toml
id = "example.source"
name = "Example repository source"
version = "1.0.0"
aespa_api = "1"
entrypoint = "extension.py:create_extension"
capabilities = ["sast.source_provider"]
```

IDs must be unique. AESPA rejects duplicate extension and provider IDs. A failed extension does not stop the application or other extensions from loading.

## Registering a source provider

The entrypoint returns an object with a `register` method:

```python
from aespa.extensions import SourceProviderDescriptor, SourceProviderField


class ExampleProvider:
    descriptor = SourceProviderDescriptor(
        id="example.source",
        label="Example repository",
        description="Load source from the example service.",
        request_fields=[
            SourceProviderField(
                key="repository",
                label="Repository",
                required=True,
            )
        ],
    )

    async def check_availability(self, context):
        ...

    async def materialize(self, parameters, destination, context):
        ...


class Extension:
    def register(self, registry):
        registry.register_source_provider(ExampleProvider())


def create_extension():
    return Extension()
```

The provider returns `MaterializedSource` with a ZIP path, display name, source locator, requested revision, resolved immutable revision, and safe metadata. Credentials must not be placed in the result or logs.

`SourceProviderContext.run_process()` runs commands without a shell, disables interactive Git prompts, applies a timeout, and limits captured output. Its first argument must be an absolute executable path.

## Settings and request fields

A provider declares `settings_fields` for machine-level configuration and `request_fields` for each new scan. AESPA renders both from field metadata. Supported field types are `text`, `path`, `number`, `boolean`, and `select`.

Settings are stored by extension ID in `extension_setting`. Unknown saved values are kept when a newer extension schema no longer displays them. Extension settings must not contain credentials. Providers should use the operating system credential store or an authenticated local CLI.

## Bundled GitHub provider

The bundled `github.repository` provider accepts `owner/repository` or a `github.com` URL and an optional branch, tag, or commit.

It prefers an authenticated GitHub CLI and otherwise uses Git with the user's credential helper. AESPA does not read or store authentication tokens and does not change global Git settings. The provider creates a bare filtered clone, resolves the selected ref to a commit, and builds a tracked-file archive without a normal checkout. Submodules and Git LFS object contents are not included in the first version.

Repository preparation runs in the background. If AESPA stops during this step, the run is marked failed on the next start instead of repeating an authenticated network operation.
