from __future__ import annotations

import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from aespa.extensions.runtime import (
    ExtensionManager,
    ProcessResult,
    ProviderAvailability,
)
from extensions.github_repository.provider import (
    GitHubRepositoryProvider,
    normalize_repository,
)


def test_extension_loader_discovers_multiple_extensions(monkeypatch, tmp_path):
    extension_dir = tmp_path / "extensions"
    example = extension_dir / "example_source"
    example.mkdir(parents=True)
    (example / "extension.toml").write_text(
        """
id = "example.source"
name = "Example source"
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

    assert set(manager.extensions) == {"github.repository", "example.source"}
    assert set(manager.source_providers) == {"github.repository", "example.source"}
    github_source = Path(manager.extensions["github.repository"].source)
    assert (
        github_source
        == Path(__file__).resolve().parents[2] / "extensions" / "github_repository"
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
    extension_id = "github.repository"
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
        item for item in response.json() if item["id"] == "github.repository"
    )
    assert extension["enabled"] is True
    assert {field["key"] for field in extension["settings_fields"]} == {
        "gh_executable",
        "git_executable",
    }

    updated = client.patch(
        "/api/extensions/github.repository/settings",
        json={"settings": {"git_executable": "/usr/bin/git"}},
    )
    assert updated.status_code == 200
    assert updated.json()["settings"] == {"git_executable": "/usr/bin/git"}

    disabled = client.put(
        "/api/extensions/github.repository/enabled", json={"enabled": False}
    )
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False
    assert disabled.json()["status"] == "disabled"
    assert disabled.json()["source_providers"] == []
    assert all(
        provider["extension_id"] != "github.repository"
        for provider in client.get("/api/extensions/source-providers").json()
    )

    enabled = client.put(
        "/api/extensions/github.repository/enabled", json={"enabled": True}
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
            "provider_id": "github.repository",
            "parameters": {"repository": "acme/payments", "ref": "main"},
            "analysis_mode": "light",
            "start_scan": True,
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "preparing"
    assert body["source_provider"] == "github.repository"
    assert body["source_requested_ref"] == "main"
    assert started == [
        (
            body["id"],
            "github.repository",
            {"repository": "acme/payments", "ref": "main"},
            True,
        )
    ]
