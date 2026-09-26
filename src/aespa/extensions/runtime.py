"""Extension registry and loader.

Extensions are trusted Python code. AESPA owns API routes, background tasks,
storage, and scan lifecycle for every registered capability.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import logging
import os
import re
import shutil
import sys
import tomllib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, Protocol

from fastapi import APIRouter, FastAPI
from sqlalchemy import Engine, event
from sqlmodel import Session, SQLModel
from sqlmodel import create_engine as create_sqlmodel_engine

from aespa.config import BUNDLED_EXTENSIONS_DIR, get_settings
from aespa.db import get_engine
from aespa.models import ExtensionSecret, ExtensionSetting

log = logging.getLogger(__name__)
_UTC = timezone.utc
_ID_RE = re.compile(r"^[a-z][a-z0-9_.-]{1,79}$")
_OUTPUT_LIMIT = 128 * 1024
_DEFAULT_WORKSPACE_LIMIT = 1024 * 1024 * 1024
_DATA_NAMESPACE_RE = re.compile(r"^[a-z][a-z0-9_]{1,62}$")


@dataclass(frozen=True)
class SourceProviderField:
    key: str
    label: str
    type: str = "text"
    required: bool = False
    placeholder: str | None = None
    help: str | None = None
    default: Any = None
    options: list[dict[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class SourceProviderDescriptor:
    id: str
    label: str
    description: str
    request_fields: list[SourceProviderField]
    settings_fields: list[SourceProviderField] = field(default_factory=list)
    settings_schema_version: int = 1


@dataclass(frozen=True)
class ProviderAvailability:
    available: bool
    status: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MaterializedSource:
    archive_path: Path
    display_name: str
    locator: str
    requested_ref: str | None
    revision: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProcessResult:
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class WebScanCandidate:
    url: str
    title: str
    vulnerability_class: str
    finding_id: int | None = None
    page_id: int | None = None
    specialist_attack_class: str | None = None


@dataclass(frozen=True)
class WebScanIssue:
    title: str
    affected_url: str
    severity: str
    description: str = ""
    recommendation: str = ""
    confidence: str = "unknown"
    request_evidence: str = ""
    response_evidence: str = ""
    owasp_category: str = "A03"


@dataclass(frozen=True)
class WebScanResult:
    task_id: str
    issues: list[WebScanIssue]


class WebActiveScanner(Protocol):
    id: str
    label: str
    description: str
    settings_fields: list[SourceProviderField]
    settings_schema_version: int

    def candidate_from_finding(
        self, finding: dict[str, Any], settings: dict[str, Any]
    ) -> WebScanCandidate | None: ...

    def candidate_from_investigation(
        self, tool_input: dict[str, Any], note: str, settings: dict[str, Any]
    ) -> WebScanCandidate | None: ...

    async def check_availability(
        self, context: SourceProviderContext
    ) -> ProviderAvailability: ...

    async def scan(
        self, candidate: WebScanCandidate, context: WebScanContext
    ) -> WebScanResult: ...


class SourceProvider(Protocol):
    descriptor: SourceProviderDescriptor

    async def check_availability(
        self, context: SourceProviderContext
    ) -> ProviderAvailability: ...

    async def materialize(
        self,
        parameters: dict[str, Any],
        destination: Path,
        context: SourceProviderContext,
    ) -> MaterializedSource: ...


class SourceProviderContext:
    """Bounded process and settings access for source providers."""

    def __init__(
        self,
        extension_id: str,
        settings: dict[str, Any],
        secrets: ExtensionSecretStore | None = None,
    ):
        self.extension_id = extension_id
        self.settings = settings
        self.secrets = secrets

    def find_executable(self, setting: str, names: list[str]) -> str | None:
        configured = str(self.settings.get(setting) or "").strip()
        if configured:
            path = Path(configured).expanduser()
            return str(path) if path.is_file() else None
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        return None

    async def run_process(
        self,
        argv: list[str],
        *,
        cwd: Path | None = None,
        timeout: float = 300,
        env: dict[str, str] | None = None,
        max_workspace_bytes: int = _DEFAULT_WORKSPACE_LIMIT,
    ) -> ProcessResult:
        if not argv or not os.path.isabs(argv[0]):
            raise ValueError(
                "Extension subprocesses require an absolute executable path"
            )
        process_env = os.environ.copy()
        process_env.update(
            {
                "GIT_TERMINAL_PROMPT": "0",
                "GH_PROMPT_DISABLED": "1",
                "GCM_INTERACTIVE": "Never",
                "GIT_LFS_SKIP_SMUDGE": "1",
            }
        )
        if env:
            process_env.update(env)
        proc = await asyncio.create_subprocess_exec(
            *argv,
            cwd=str(cwd) if cwd else None,
            env=process_env,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=sys.platform != "win32",
        )

        async def monitor_workspace() -> None:
            if cwd is None:
                await asyncio.Future()
            while True:
                await asyncio.sleep(0.5)

                def directory_size() -> int:
                    total = 0
                    for path in cwd.rglob("*"):
                        try:
                            if path.is_file() and not path.is_symlink():
                                total += path.stat().st_size
                        except OSError:
                            continue
                    return total

                if await asyncio.to_thread(directory_size) > max_workspace_bytes:
                    raise RuntimeError(
                        "Extension workspace exceeded the 1 GiB preparation limit"
                    )

        communication = asyncio.create_task(
            asyncio.wait_for(proc.communicate(), timeout=timeout)
        )
        monitor = asyncio.create_task(monitor_workspace())
        try:
            done, _pending = await asyncio.wait(
                {communication, monitor}, return_when=asyncio.FIRST_COMPLETED
            )
            if monitor in done:
                await monitor
                raise RuntimeError("Extension workspace monitor stopped unexpectedly")
            stdout, stderr = await communication
        except asyncio.CancelledError:
            proc.kill()
            await proc.wait()
            raise
        except TimeoutError:
            proc.kill()
            await proc.wait()
            raise RuntimeError(
                f"Command timed out after {int(timeout)} seconds"
            ) from None
        except Exception:
            proc.kill()
            await proc.wait()
            raise
        finally:
            communication.cancel()
            monitor.cancel()
            await asyncio.gather(communication, monitor, return_exceptions=True)
        return ProcessResult(
            returncode=proc.returncode or 0,
            stdout=stdout[-_OUTPUT_LIMIT:].decode("utf-8", errors="replace").strip(),
            stderr=stderr[-_OUTPUT_LIMIT:].decode("utf-8", errors="replace").strip(),
        )


class WebScanContext(SourceProviderContext):
    def __init__(
        self,
        extension_id: str,
        settings: dict[str, Any],
        secrets: ExtensionSecretStore | None,
        *,
        cookies: dict[str, str],
        extra_headers: dict[str, str],
        on_started,
    ):
        super().__init__(extension_id, settings, secrets)
        self.cookies = cookies
        self.extra_headers = extra_headers
        self.on_started = on_started


@dataclass
class ExtensionRecord:
    id: str
    name: str
    version: str
    aespa_api: str
    capabilities: list[str]
    source: str
    author: str | None = None
    secrets_namespace: str | None = None
    data_namespace: str | None = None
    enabled: bool = True
    status: str = "loaded"
    error: str | None = None
    settings_fields: list[SourceProviderField] = field(default_factory=list)
    settings_schema_version: int = 1


@dataclass(frozen=True)
class RegisteredSourceProvider:
    extension_id: str
    provider: SourceProvider


@dataclass(frozen=True)
class RegisteredWebScanner:
    extension_id: str
    scanner: WebActiveScanner


@dataclass(frozen=True)
class RegisteredApiApp:
    extension_id: str
    app: FastAPI


class ExtensionDataStore:
    """An extension's isolated SQLite database.

    Extensions must prefix every table with their manifest ``data_namespace``.
    The database file is retained while an extension is disabled so enabling it
    again restores the extension exactly where it left off.
    """

    def __init__(self, extension_id: str, namespace: str, path: Path):
        self.extension_id = extension_id
        self.namespace = namespace
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.engine: Engine = create_sqlmodel_engine(
            f"sqlite:///{path}",
            connect_args={"check_same_thread": False, "timeout": 30},
        )

        @event.listens_for(self.engine, "connect")
        def _configure(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA busy_timeout=30000")
            finally:
                cursor.close()

    @property
    def table_prefix(self) -> str:
        return f"{self.namespace}_"

    def create_all(self, metadata=None) -> None:
        metadata = metadata or SQLModel.metadata
        tables = list(metadata.tables.values())
        invalid = sorted(
            table.name
            for table in tables
            if not table.name.startswith(self.table_prefix)
        )
        if invalid:
            raise ValueError(
                f"Extension tables must start with {self.table_prefix!r}: "
                + ", ".join(invalid)
            )
        metadata.create_all(self.engine)

    def session(self) -> Session:
        return Session(self.engine)

    def dispose(self) -> None:
        self.engine.dispose()


class ExtensionSecretStore:
    """Read and write only the namespace assigned to an extension."""

    def __init__(self, namespace: str):
        if not _ID_RE.fullmatch(namespace):
            raise ValueError("Invalid extension secrets namespace")
        self._namespace = namespace

    def get(self, key: str) -> str | None:
        self._check_key(key)
        with Session(get_engine()) as session:
            row = session.get(ExtensionSecret, (self._namespace, key))
            return row.value if row else None

    def has(self, key: str) -> bool:
        return self.get(key) is not None

    def set(self, key: str, value: str) -> None:
        self._check_key(key)
        if not isinstance(value, str) or not value:
            raise ValueError("Extension secret must be non-empty text")
        with Session(get_engine()) as session:
            row = session.get(
                ExtensionSecret, (self._namespace, key)
            ) or ExtensionSecret(namespace=self._namespace, key=key, value=value)
            row.value = value
            row.updated_at = datetime.now(_UTC)
            session.add(row)
            session.commit()

    def delete(self, key: str) -> None:
        self._check_key(key)
        with Session(get_engine()) as session:
            row = session.get(ExtensionSecret, (self._namespace, key))
            if row:
                session.delete(row)
                session.commit()

    @staticmethod
    def _check_key(key: str) -> None:
        if not isinstance(key, str) or not _ID_RE.fullmatch(key):
            raise ValueError("Invalid extension secret key")


class ExtensionRegistry:
    def __init__(self, manager: ExtensionManager, extension_id: str):
        self._manager = manager
        self._extension_id = extension_id

    def register_source_provider(self, provider: SourceProvider) -> None:
        self._manager._register_source_provider(self._extension_id, provider)

    def register_web_active_scanner(self, scanner: WebActiveScanner) -> None:
        self._manager._register_web_active_scanner(self._extension_id, scanner)

    def register_api_router(self, router: APIRouter) -> None:
        """Expose routes below ``/extension/<extension-id>/``."""
        self._manager._register_api_router(self._extension_id, router)

    def data_store(self, metadata=None) -> ExtensionDataStore:
        """Return isolated storage and create the extension's validated tables."""
        store = self._manager.data_store_for(self._extension_id)
        if metadata is not None:
            store.create_all(metadata)
        return store

    @property
    def secrets(self) -> ExtensionSecretStore:
        """Secret store bound to this extension's declared namespace."""
        return self._manager.secret_store_for(self._extension_id)

    def register_settings_fields(
        self, fields: list[SourceProviderField], *, schema_version: int = 1
    ) -> None:
        """Declare settings for an extension without a source provider."""
        self._manager._register_settings_fields(
            self._extension_id, fields, schema_version=schema_version
        )


class ExtensionManager:
    def __init__(self) -> None:
        self.extensions: dict[str, ExtensionRecord] = {}
        self.source_providers: dict[str, RegisteredSourceProvider] = {}
        self.web_scanners: dict[str, RegisteredWebScanner] = {}
        self.api_apps: dict[str, RegisteredApiApp] = {}
        self.data_stores: dict[str, ExtensionDataStore] = {}
        self._loaded = False

    def ensure_loaded(self) -> None:
        if not self._loaded:
            self.load_extensions()

    def load_extensions(self) -> None:
        for store in self.data_stores.values():
            store.dispose()
        self.extensions.clear()
        self.source_providers.clear()
        self.web_scanners.clear()
        self.api_apps.clear()
        self.data_stores.clear()
        extension_dir = get_settings().extensions_dir
        extension_dir.mkdir(parents=True, exist_ok=True)
        roots = [BUNDLED_EXTENSIONS_DIR, extension_dir]
        visited: set[Path] = set()
        for root in roots:
            resolved_root = root.resolve()
            if resolved_root in visited or not root.is_dir():
                continue
            visited.add(resolved_root)
            for directory in sorted(root.iterdir(), key=lambda item: item.name):
                if not directory.is_dir():
                    continue
                if (directory / "extension.toml").is_file():
                    self._load_directory(directory)
                    continue
                for child in sorted(directory.iterdir(), key=lambda item: item.name):
                    if child.is_dir() and (child / "extension.toml").is_file():
                        self._load_directory(child)
        self._loaded = True

    def _load_directory(self, directory: Path) -> None:
        try:
            manifest = tomllib.loads(
                (directory / "extension.toml").read_text(encoding="utf-8")
            )
            extension_id = str(manifest.get("id") or "")
            if not _ID_RE.fullmatch(extension_id):
                raise ValueError("manifest id is invalid")
            default_enabled = manifest.get("enabled_by_default", True)
            if not isinstance(default_enabled, bool):
                raise ValueError("enabled_by_default must be true or false")
            author = manifest.get("author")
            if author is not None:
                if not isinstance(author, str) or not author.strip():
                    raise ValueError("author must be non-empty text")
                author = author.strip()
            namespace_value = manifest.get("secrets_namespace")
            if namespace_value is not None:
                if not isinstance(namespace_value, str) or not _ID_RE.fullmatch(
                    namespace_value
                ):
                    raise ValueError("secrets_namespace is invalid")
                if not author or not _ID_RE.fullmatch(author):
                    raise ValueError(
                        "a secrets namespace requires an author matching the extension ID pattern"
                    )
            data_namespace = manifest.get("data_namespace")
            if data_namespace is not None and (
                not isinstance(data_namespace, str)
                or not _DATA_NAMESPACE_RE.fullmatch(data_namespace)
            ):
                raise ValueError("data_namespace is invalid")
            record = ExtensionRecord(
                id=extension_id,
                name=str(manifest.get("name") or extension_id),
                version=str(manifest.get("version") or "0.0.0"),
                aespa_api=str(manifest.get("aespa_api") or ""),
                capabilities=[str(value) for value in manifest.get("capabilities", [])],
                source=str(directory),
                author=author,
                secrets_namespace=(
                    f"{author}.{namespace_value}"
                    if namespace_value is not None
                    else None
                ),
                data_namespace=data_namespace,
                enabled=self.is_enabled(extension_id, default_enabled),
            )
            if record.aespa_api != "1":
                raise ValueError(
                    f"extension API {record.aespa_api!r} is not supported; expected '1'"
                )
            if extension_id in self.extensions:
                raise ValueError(f"extension id {extension_id!r} is already registered")
            if record.secrets_namespace is not None:
                if not _ID_RE.fullmatch(record.secrets_namespace):
                    raise ValueError("qualified secrets namespace is too long")
                if any(
                    item.secrets_namespace == record.secrets_namespace
                    for item in self.extensions.values()
                ):
                    raise ValueError(
                        f"secrets namespace {record.secrets_namespace!r} is already registered"
                    )
            if not record.enabled:
                record.status = "disabled"
                self.extensions[record.id] = record
                return
            entrypoint = str(
                manifest.get("entrypoint") or "extension.py:create_extension"
            )
            file_name, separator, attribute = entrypoint.partition(":")
            if not separator or not file_name or not attribute:
                raise ValueError("entrypoint must use file.py:function syntax")
            entry_path = (directory / file_name).resolve()
            if (
                not entry_path.is_relative_to(directory.resolve())
                or not entry_path.is_file()
            ):
                raise ValueError(
                    "entrypoint must be a file inside the extension directory"
                )
            module = self._load_module(extension_id, directory, entry_path)
            factory = getattr(module, attribute, None)
            if not callable(factory):
                raise ValueError(f"entrypoint callable {attribute!r} was not found")
            self._activate(record, factory)
        except Exception as exc:  # noqa: BLE001 - one extension must not stop AESPA
            extension_id = locals().get("extension_id") or directory.name
            record_id = str(extension_id)
            if record_id in self.extensions:
                record_id = f"load-error.{directory.name}"
                suffix = 2
                while record_id in self.extensions:
                    record_id = f"load-error.{directory.name}.{suffix}"
                    suffix += 1
            failed_record = locals().get("record")
            if (
                isinstance(failed_record, ExtensionRecord)
                and failed_record.id == record_id
            ):
                failed_record.status = "failed"
                failed_record.error = str(exc)
                self.extensions[record_id] = failed_record
            else:
                self.extensions[record_id] = ExtensionRecord(
                    id=record_id,
                    name=str(extension_id),
                    version="unknown",
                    aespa_api="unknown",
                    capabilities=[],
                    source=str(directory),
                    status="failed",
                    error=str(exc),
                )
            log.exception("Could not load extension from %s", directory)

    def _load_module(
        self, extension_id: str, directory: Path, entry_path: Path
    ) -> ModuleType:
        module_name = "aespa_external_" + re.sub(r"[^a-zA-Z0-9_]", "_", extension_id)
        spec = importlib.util.spec_from_file_location(
            module_name,
            entry_path,
            submodule_search_locations=[str(directory)],
        )
        if spec is None or spec.loader is None:
            raise ValueError("could not create the extension module")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    def _activate(self, record: ExtensionRecord, factory) -> None:
        if record.id in self.extensions:
            raise ValueError(f"extension id {record.id!r} is already registered")
        self.extensions[record.id] = record
        try:
            extension = factory()
            extension.register(ExtensionRegistry(self, record.id))
            providers = [
                item.provider.descriptor
                for item in self.source_providers.values()
                if item.extension_id == record.id
            ]
            scanners = [
                item.scanner
                for item in self.web_scanners.values()
                if item.extension_id == record.id
            ]
            record.settings_fields = [
                *record.settings_fields,
                *(
                    field
                    for capability in [*providers, *scanners]
                    for field in capability.settings_fields
                ),
            ]
            keys = [item.key for item in record.settings_fields]
            if len(keys) != len(set(keys)):
                raise ValueError("Extension setting keys must be unique")
            record.settings_schema_version = max(
                [record.settings_schema_version]
                + [
                    capability.settings_schema_version
                    for capability in [*providers, *scanners]
                ]
            )
        except Exception as exc:
            record.status = "failed"
            record.error = str(exc)
            for provider_id, registered in list(self.source_providers.items()):
                if registered.extension_id == record.id:
                    self.source_providers.pop(provider_id, None)
            for scanner_id, registered in list(self.web_scanners.items()):
                if registered.extension_id == record.id:
                    self.web_scanners.pop(scanner_id, None)
            self.api_apps.pop(record.id, None)
            store = self.data_stores.pop(record.id, None)
            if store is not None:
                store.dispose()
            log.exception("Could not activate extension %s", record.id)

    def _register_source_provider(
        self, extension_id: str, provider: SourceProvider
    ) -> None:
        descriptor = provider.descriptor
        if not _ID_RE.fullmatch(descriptor.id):
            raise ValueError(f"provider id {descriptor.id!r} is invalid")
        if descriptor.id in self.source_providers:
            raise ValueError(
                f"source provider id {descriptor.id!r} is already registered"
            )
        if any(field.type == "secret" for field in descriptor.settings_fields):
            if not self.extensions[extension_id].secrets_namespace:
                raise ValueError(
                    "secret settings require secrets_namespace in extension.toml"
                )
        self.source_providers[descriptor.id] = RegisteredSourceProvider(
            extension_id=extension_id, provider=provider
        )

    def _register_web_active_scanner(
        self, extension_id: str, scanner: WebActiveScanner
    ) -> None:
        if "web.active_scanner" not in self.extensions[extension_id].capabilities:
            raise ValueError("web.active_scanner is missing from extension.toml")
        if not _ID_RE.fullmatch(scanner.id) or scanner.id in self.web_scanners:
            raise ValueError(f"Invalid or duplicate web scanner id {scanner.id!r}")
        if any(field.type == "secret" for field in scanner.settings_fields):
            if not self.extensions[extension_id].secrets_namespace:
                raise ValueError(
                    "secret settings require secrets_namespace in extension.toml"
                )
        self.web_scanners[scanner.id] = RegisteredWebScanner(extension_id, scanner)

    def _register_api_router(self, extension_id: str, router: APIRouter) -> None:
        record = self.extensions[extension_id]
        if "api.routes" not in record.capabilities:
            raise ValueError("api.routes is missing from extension.toml")
        if extension_id in self.api_apps:
            raise ValueError("An extension may register only one API router")
        for route in router.routes:
            if not str(getattr(route, "path", "")).startswith("/"):
                raise ValueError("Extension API route paths must start with /")
        app = FastAPI(
            title=f"{record.name} extension API",
            docs_url=None,
            redoc_url=None,
            openapi_url=None,
        )
        app.include_router(router)
        self.api_apps[extension_id] = RegisteredApiApp(extension_id, app)

    def data_store_for(self, extension_id: str) -> ExtensionDataStore:
        record = self.extensions.get(extension_id)
        if record is None:
            raise KeyError(extension_id)
        if not record.enabled or record.status != "loaded":
            raise ValueError("Extension is not enabled")
        if not record.data_namespace:
            raise ValueError("Extension has no data_namespace")
        store = self.data_stores.get(extension_id)
        if store is None:
            safe_id = re.sub(r"[^a-zA-Z0-9_.-]", "_", extension_id)
            path = get_settings().data_dir / "extensions" / f"{safe_id}.db"
            store = ExtensionDataStore(extension_id, record.data_namespace, path)
            self.data_stores[extension_id] = store
        return store

    def api_app_for(self, extension_id: str) -> FastAPI | None:
        registered = self.api_apps.get(extension_id)
        return registered.app if registered else None

    def _register_settings_fields(
        self,
        extension_id: str,
        fields: list[SourceProviderField],
        *,
        schema_version: int,
    ) -> None:
        record = self.extensions[extension_id]
        if schema_version < 1:
            raise ValueError("Settings schema version must be positive")
        if (
            any(field.type == "secret" for field in fields)
            and not record.secrets_namespace
        ):
            raise ValueError(
                "secret settings require secrets_namespace in extension.toml"
            )
        existing = {field.key for field in record.settings_fields}
        for setting_field in fields:
            if not _ID_RE.fullmatch(setting_field.key) or setting_field.key in existing:
                raise ValueError(
                    f"Invalid or duplicate extension setting {setting_field.key!r}"
                )
            existing.add(setting_field.key)
        record.settings_fields.extend(fields)
        record.settings_schema_version = max(
            record.settings_schema_version, schema_version
        )

    def _stored_settings(self, extension_id: str) -> dict[str, Any]:
        with Session(get_engine()) as session:
            row = session.get(ExtensionSetting, extension_id)
            if row is None:
                return {}
            try:
                value = json.loads(row.settings_json or "{}")
            except (TypeError, ValueError):
                return {}
            return value if isinstance(value, dict) else {}

    def is_enabled(self, extension_id: str, default: bool = True) -> bool:
        with Session(get_engine()) as session:
            row = session.get(ExtensionSetting, extension_id)
            return default if row is None else row.enabled

    def set_enabled(self, extension_id: str, enabled: bool) -> None:
        if extension_id not in self.extensions:
            raise KeyError(extension_id)
        if not enabled:
            from aespa.services import external_scans

            external_scans.cancel_extension(extension_id)
        with Session(get_engine()) as session:
            row = session.get(ExtensionSetting, extension_id) or ExtensionSetting(
                extension_id=extension_id
            )
            row.enabled = enabled
            row.updated_at = datetime.now(_UTC)
            session.add(row)
            session.commit()
        self.load_extensions()

    def get_settings(self, extension_id: str) -> dict[str, Any]:
        stored = self._stored_settings(extension_id)
        record = self.extensions.get(extension_id)
        if record is None:
            return {}
        allowed = {
            field.key for field in record.settings_fields if field.type != "secret"
        }
        return {key: value for key, value in stored.items() if key in allowed}

    def secret_store_for(self, extension_id: str) -> ExtensionSecretStore:
        record = self.extensions.get(extension_id)
        if record is None:
            raise KeyError(extension_id)
        if not record.enabled or record.status != "loaded":
            raise ValueError("Extension is not enabled")
        if not record.secrets_namespace:
            raise ValueError("Extension has no secrets namespace")
        return ExtensionSecretStore(record.secrets_namespace)

    def save_settings(
        self, extension_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        record = self.extensions.get(extension_id)
        if record is None:
            raise KeyError(extension_id)
        fields = {field.key: field for field in record.settings_fields}
        unknown = sorted(set(values) - set(fields))
        if unknown:
            raise ValueError(f"Unknown extension setting(s): {', '.join(unknown)}")
        clean: dict[str, Any] = {}
        secret_updates: dict[str, str | None] = {}
        for key, value in values.items():
            descriptor = fields[key]
            if descriptor.type == "secret":
                if value is not None and not isinstance(value, str):
                    raise ValueError(f"{descriptor.label} must be text or null")
                secret_updates[key] = value.strip() if isinstance(value, str) else None
            elif descriptor.type in {"text", "path", "select"}:
                if value is not None and not isinstance(value, str):
                    raise ValueError(f"{descriptor.label} must be text")
                clean[key] = value.strip() if isinstance(value, str) else value
            elif descriptor.type == "boolean":
                if not isinstance(value, bool):
                    raise ValueError(f"{descriptor.label} must be true or false")
                clean[key] = value
            elif descriptor.type == "number":
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    raise ValueError(f"{descriptor.label} must be a number")
                clean[key] = value
            else:
                raise ValueError(
                    f"Unsupported extension setting type: {descriptor.type}"
                )
        if secret_updates and (
            not record.secrets_namespace
            or not record.enabled
            or record.status != "loaded"
        ):
            raise ValueError("Extension secrets are unavailable")
        with Session(get_engine()) as session:
            row = session.get(ExtensionSetting, extension_id) or ExtensionSetting(
                extension_id=extension_id
            )
            try:
                stored = json.loads(row.settings_json or "{}")
            except (TypeError, ValueError):
                stored = {}
            if not isinstance(stored, dict):
                stored = {}
            stored.update(clean)
            row.schema_version = record.settings_schema_version
            row.settings_json = json.dumps(stored, ensure_ascii=False)
            row.updated_at = datetime.now(_UTC)
            session.add(row)
            for key, value in secret_updates.items():
                if value is None:
                    continue
                secret_row = session.get(
                    ExtensionSecret, (record.secrets_namespace, key)
                )
                if value:
                    secret_row = secret_row or ExtensionSecret(
                        namespace=record.secrets_namespace, key=key, value=value
                    )
                    secret_row.value = value
                    secret_row.updated_at = datetime.now(_UTC)
                    session.add(secret_row)
                elif secret_row:
                    session.delete(secret_row)
            session.commit()
        return self.get_settings(extension_id)

    def context_for(self, extension_id: str) -> SourceProviderContext:
        record = self.extensions.get(extension_id)
        secrets = (
            self.secret_store_for(extension_id)
            if record
            and record.secrets_namespace
            and record.enabled
            and record.status == "loaded"
            else None
        )
        return SourceProviderContext(
            extension_id, self.get_settings(extension_id), secrets
        )

    def extension_dict(self, record: ExtensionRecord) -> dict[str, Any]:
        return {
            "id": record.id,
            "name": record.name,
            "author": record.author,
            "version": record.version,
            "aespa_api": record.aespa_api,
            "capabilities": record.capabilities,
            "source": record.source,
            "secrets_namespace": record.secrets_namespace,
            "data_namespace": record.data_namespace,
            "api_prefix": (
                f"/extension/{record.id}"
                if record.id in self.api_apps and record.status == "loaded"
                else None
            ),
            "enabled": record.enabled,
            "status": record.status,
            "error": record.error,
            "settings_schema_version": record.settings_schema_version,
            "settings_fields": [asdict(item) for item in record.settings_fields],
            "settings": self.get_settings(record.id),
            "has_secrets": (
                {
                    field.key: self.secret_store_for(record.id).has(field.key)
                    for field in record.settings_fields
                    if field.type == "secret"
                }
                if record.enabled
                and record.status == "loaded"
                and record.secrets_namespace
                else {}
            ),
        }


_manager = ExtensionManager()


def get_extension_manager() -> ExtensionManager:
    return _manager
