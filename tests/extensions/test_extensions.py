from __future__ import annotations

import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import Column, Integer, MetaData, Table
from sqlmodel import Session

from aespa.db import get_engine
from aespa.extensions.runtime import (
    ExtensionManager,
    ExtensionRegistry,
    ProcessResult,
    ProviderAvailability,
)
from aespa.models import ExtensionSetting
from extensions.builtin.github_repository.provider import (
    GitHubRepositoryProvider,
    normalize_repository,
)


def test_extension_loader_supports_author_folders_in_both_roots(monkeypatch, tmp_path):
    bundled = tmp_path / "bundled"
    user = tmp_path / "user"

    def create_extension(directory: Path, extension_id: str) -> None:
        directory.mkdir(parents=True)
        (directory / "extension.toml").write_text(
            f'id = "{extension_id}"\naespa_api = "1"\n', encoding="utf-8"
        )
        (directory / "extension.py").write_text(
            "from .helper import Extension\n\n"
            "def create_extension():\n    return Extension()\n",
            encoding="utf-8",
        )
        (directory / "helper.py").write_text(
            "class Extension:\n    def register(self, registry):\n        pass\n",
            encoding="utf-8",
        )

    create_extension(bundled / "legacy", "legacy.extension")
    create_extension(bundled / "aespa" / "github", "aespa.github")
    create_extension(user / "acme" / "github", "acme.github")
    create_extension(user / "too" / "deep" / "hidden", "hidden.extension")
    monkeypatch.setattr("aespa.extensions.runtime.BUNDLED_EXTENSIONS_DIR", bundled)
    monkeypatch.setattr(
        "aespa.extensions.runtime.get_settings",
        lambda: SimpleNamespace(extensions_dir=user),
    )

    manager = ExtensionManager()
    manager.load_extensions()

    assert set(manager.extensions) == {
        "legacy.extension",
        "aespa.github",
        "acme.github",
    }
    assert all(record.status == "loaded" for record in manager.extensions.values())
    assert Path(manager.extensions["acme.github"].source) == user / "acme" / "github"
    assert manager.extensions["acme.github"].author is None


def test_extension_loader_discovers_multiple_extensions(monkeypatch, tmp_path):
    extension_dir = tmp_path / "extensions"
    example = extension_dir / "example_source"
    example.mkdir(parents=True)
    (example / "extension.toml").write_text(
        """
id = "example.source"
name = "Example source"
author = "Example Co"
version = "1.2.3"
aespa_api = "1"
entrypoint = "extension.py:create_extension"
capabilities = ["sast.source_provider"]
""".strip(),
        encoding="utf-8",
    )
    (example / "extension.py").write_text(
        """
from aespa.extensions import SourceProviderDescriptor

class Provider:
    descriptor = SourceProviderDescriptor(
        id="example.source", label="Example", description="Example provider", request_fields=[]
    )

class Extension:
    def register(self, registry):
        registry.register_source_provider(Provider())

def create_extension():
    return Extension()
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "aespa.extensions.runtime.get_settings",
        lambda: SimpleNamespace(extensions_dir=extension_dir),
    )

    manager = ExtensionManager()
    manager.load_extensions()

    assert set(manager.extensions) == {
        "aespa.burpsuite",
        "aespa.githubrepository",
        "aespa.sast-benchmarking",
        "example.source",
    }
    assert set(manager.source_providers) == {"aespa.githubrepository", "example.source"}
    assert manager.extensions["aespa.sast-benchmarking"].status == "disabled"
    assert manager.extensions["example.source"].author == "Example Co"
    github_source = Path(manager.extensions["aespa.githubrepository"].source)
    assert (
        github_source
        == Path(__file__).resolve().parents[2]
        / "extensions"
        / "builtin"
        / "github_repository"
    )

    manager.set_enabled("example.source", False)
    assert manager.extensions["example.source"].status == "disabled"
    assert "example.source" not in manager.source_providers

    (example / "extension.py").write_text(
        "raise RuntimeError('disabled code should not be imported')\n",
        encoding="utf-8",
    )
    manager.load_extensions()
    assert manager.extensions["example.source"].status == "disabled"


def test_extension_api_routes_and_data_are_removed_cleanly_when_disabled(
    client, monkeypatch, tmp_path
):
    from aespa.config import BUNDLED_EXTENSIONS_DIR
    from aespa.extensions import get_extension_manager

    manager = get_extension_manager()
    monkeypatch.setattr(
        "aespa.extensions.runtime.get_settings",
        lambda: SimpleNamespace(
            extensions_dir=tmp_path / "user-extensions",
            data_dir=tmp_path / "data",
        ),
    )
    manager.load_extensions()

    enabled = client.put(
        "/api/extensions/aespa.sast-benchmarking/enabled",
        json={"enabled": True},
    )
    assert enabled.status_code == 200
    assert enabled.json()["api_prefix"] == "/extension/aespa.sast-benchmarking"
    assert client.get("/extension/aespa.sast-benchmarking/datasets").json() == []
    assert (tmp_path / "data" / "extensions" / "aespa.sast-benchmarking.db").is_file()

    disabled = client.put(
        "/api/extensions/aespa.sast-benchmarking/enabled",
        json={"enabled": False},
    )
    assert disabled.status_code == 200
    assert client.get("/extension/aespa.sast-benchmarking/datasets").status_code == 404
    assert client.get("/api/health").status_code == 200
    assert BUNDLED_EXTENSIONS_DIR.is_dir()


def test_extension_data_store_rejects_tables_outside_its_namespace(
    monkeypatch, tmp_path
):
    manager = ExtensionManager()
    manager.extensions["example.data"] = SimpleNamespace(
        enabled=True,
        status="loaded",
        data_namespace="example_data",
    )
    monkeypatch.setattr(
        "aespa.extensions.runtime.get_settings",
        lambda: SimpleNamespace(data_dir=tmp_path),
    )
    metadata = MetaData()
    Table("somebody_elses_table", metadata, Column("id", Integer, primary_key=True))

    with pytest.raises(ValueError, match="example_data_"):
        manager.data_store_for("example.data").create_all(metadata)


def test_extension_secrets_are_namespaced_and_not_returned_by_api(
    client, monkeypatch, tmp_path
):
    extension_dir = tmp_path / "extensions"
    for extension_id, author in (
        ("example.first", "first"),
        ("example.second", "second"),
    ):
        directory = extension_dir / extension_id
        directory.mkdir(parents=True)
        (directory / "extension.toml").write_text(
            f'''id = "{extension_id}"
name = "{extension_id}"
author = "{author}"
version = "1.0.0"
aespa_api = "1"
secrets_namespace = "shared"
entrypoint = "extension.py:create_extension"
capabilities = []
''',
            encoding="utf-8",
        )
        (directory / "extension.py").write_text(
            """from aespa.extensions import SourceProviderField

class Extension:
    def register(self, registry):
        registry.register_settings_fields([
            SourceProviderField(key="api_key", label="API key", type="secret")
        ])

def create_extension():
    return Extension()
""",
            encoding="utf-8",
        )
    monkeypatch.setattr(
        "aespa.extensions.runtime.get_settings",
        lambda: SimpleNamespace(extensions_dir=extension_dir),
    )
    manager = ExtensionManager()
    manager.load_extensions()
    monkeypatch.setattr("aespa.api.extensions.get_extension_manager", lambda: manager)

    response = client.patch(
        "/api/extensions/example.first/settings",
        json={"settings": {"api_key": "first-secret"}},
    )
    assert response.status_code == 200
    assert response.json()["settings"] == {}
    assert response.json()["has_secrets"] == {"api_key": True}
    assert response.json()["secrets_namespace"] == "first.shared"
    assert "first-secret" not in response.text
    assert manager.context_for("example.first").secrets.get("api_key") == "first-secret"
    assert manager.context_for("example.second").secrets.get("api_key") is None
    assert manager.extensions["example.second"].secrets_namespace == "second.shared"
    assert ExtensionRegistry(manager, "example.first").secrets.has("api_key")
    with Session(get_engine()) as session:
        assert (
            "first-secret"
            not in session.get(ExtensionSetting, "example.first").settings_json
        )
    manager.load_extensions()
    assert manager.context_for("example.first").secrets.get("api_key") == "first-secret"

    kept = client.patch(
        "/api/extensions/example.first/settings",
        json={"settings": {"api_key": None}},
    )
    assert kept.status_code == 200
    assert kept.json()["has_secrets"] == {"api_key": True}

    removed = client.patch(
        "/api/extensions/example.first/settings",
        json={"settings": {"api_key": ""}},
    )
    assert removed.status_code == 200
    assert removed.json()["has_secrets"] == {"api_key": False}
    assert manager.context_for("example.first").secrets.get("api_key") is None


def test_extension_rejects_duplicate_secrets_namespace(monkeypatch, tmp_path):
    extension_dir = tmp_path / "extensions"
    for name in ("first", "second"):
        directory = extension_dir / name
        directory.mkdir(parents=True)
        (directory / "extension.toml").write_text(
            f"""id = "example.{name}"
aespa_api = "1"
author = "example"
secrets_namespace = "shared"
""",
            encoding="utf-8",
        )
        (directory / "extension.py").write_text(
            "def create_extension():\n    return type('Extension', (), {'register': lambda self, registry: None})()\n",
            encoding="utf-8",
        )
    monkeypatch.setattr(
        "aespa.extensions.runtime.get_settings",
        lambda: SimpleNamespace(extensions_dir=extension_dir),
    )
    manager = ExtensionManager()
    manager.load_extensions()
    assert manager.extensions["example.first"].status == "loaded"
    assert manager.extensions["example.second"].status == "failed"
    assert "already registered" in manager.extensions["example.second"].error


def test_extension_secret_namespace_requires_author(monkeypatch, tmp_path):
    extension_dir = tmp_path / "extensions"
    directory = extension_dir / "example"
    directory.mkdir(parents=True)
    (directory / "extension.toml").write_text(
        'id = "example.secret"\naespa_api = "1"\nsecrets_namespace = "secret"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "aespa.extensions.runtime.get_settings",
        lambda: SimpleNamespace(extensions_dir=extension_dir),
    )
    manager = ExtensionManager()
    manager.load_extensions()
    assert manager.extensions["example.secret"].status == "failed"
    assert "requires an author" in manager.extensions["example.secret"].error


def test_github_repository_normalization_rejects_other_hosts():
    assert normalize_repository("https://github.com/acme/payments.git") == (
        "acme/payments",
        "https://github.com/acme/payments",
    )
    assert (
        normalize_repository("git@github.com:acme/payments.git")[0] == "acme/payments"
    )

    with pytest.raises(ValueError, match="github.com"):
        normalize_repository("https://gitlab.com/acme/payments")


class _FakeContext:
    extension_id = "aespa.githubrepository"
    settings = {}

    def __init__(self):
        self.commands: list[list[str]] = []

    def find_executable(self, setting, names):
        return "/usr/local/bin/gh" if setting == "gh_executable" else "/usr/bin/git"

    async def run_process(self, argv, **kwargs):
        self.commands.append(argv)
        if argv[1:3] == ["auth", "status"]:
            return ProcessResult(0, "", "")
        if "rev-parse" in argv:
            return ProcessResult(0, "a" * 40, "")
        output = next(
            (
                item.removeprefix("--output=")
                for item in argv
                if item.startswith("--output=")
            ),
            None,
        )
        if output:
            with zipfile.ZipFile(output, "w") as archive:
                archive.writestr("src/app.py", "print('ok')")
        return ProcessResult(0, "", "")


@pytest.mark.anyio
async def test_github_provider_uses_gh_auth_and_freezes_resolved_commit(tmp_path):
    context = _FakeContext()
    provider = GitHubRepositoryProvider()

    result = await provider.materialize(
        {"repository": "acme/payments", "ref": "release/1"}, tmp_path, context
    )

    assert result.locator == "https://github.com/acme/payments"
    assert result.requested_ref == "release/1"
    assert result.revision == "a" * 40
    assert result.archive_path.is_file()
    assert any(command[1:3] == ["repo", "clone"] for command in context.commands)
    assert any("archive" in command for command in context.commands)


def test_extensions_api_lists_and_updates_dynamic_settings(client, monkeypatch):
    async def available(self, context):
        return ProviderAvailability(True, "ready", "Ready", {"authenticated": True})

    monkeypatch.setattr(GitHubRepositoryProvider, "check_availability", available)

    response = client.get("/api/extensions")
    assert response.status_code == 200
    extension = next(
        item for item in response.json() if item["id"] == "aespa.githubrepository"
    )
    assert extension["enabled"] is True
    assert extension["author"] == "aespa"
    assert {field["key"] for field in extension["settings_fields"]} == {
        "gh_executable",
        "git_executable",
    }

    updated = client.patch(
        "/api/extensions/aespa.githubrepository/settings",
        json={"settings": {"git_executable": "/usr/bin/git"}},
    )
    assert updated.status_code == 200
    assert updated.json()["settings"] == {"git_executable": "/usr/bin/git"}

    disabled = client.put(
        "/api/extensions/aespa.githubrepository/enabled", json={"enabled": False}
    )
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False
    assert disabled.json()["status"] == "disabled"
    assert disabled.json()["source_providers"] == []
    assert all(
        provider["extension_id"] != "aespa.githubrepository"
        for provider in client.get("/api/extensions/source-providers").json()
    )

    enabled = client.put(
        "/api/extensions/aespa.githubrepository/enabled", json={"enabled": True}
    )
    assert enabled.status_code == 200
    assert enabled.json()["enabled"] is True
    assert enabled.json()["status"] == "loaded"


def test_create_sast_run_from_extension_starts_preparation(client, monkeypatch):
    async def available(self, context):
        return ProviderAvailability(True, "ready", "Ready")

    started = []
    monkeypatch.setattr(GitHubRepositoryProvider, "check_availability", available)
    monkeypatch.setattr(
        "aespa.services.sast_sources.start_source_preparation",
        lambda run_id, provider_id, parameters, auto_start: started.append(
            (run_id, provider_id, parameters, auto_start)
        ),
    )

    response = client.post(
        "/api/sast-runs/from-source",
        json={
            "provider_id": "aespa.githubrepository",
            "parameters": {"repository": "acme/payments", "ref": "main"},
            "analysis_mode": "light",
            "start_scan": True,
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "preparing"
    assert body["source_provider"] == "aespa.githubrepository"
    assert body["source_requested_ref"] == "main"
    assert started == [
        (
            body["id"],
            "aespa.githubrepository",
            {"repository": "acme/payments", "ref": "main"},
            True,
        )
    ]
