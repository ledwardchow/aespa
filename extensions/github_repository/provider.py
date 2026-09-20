"""Materialize GitHub repositories with the user's existing CLI credentials."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from aespa.extensions import (
    ExtensionRegistry,
    MaterializedSource,
    ProviderAvailability,
    SourceProviderContext,
    SourceProviderDescriptor,
    SourceProviderField,
)

_OWNER_REPO_RE = re.compile(
    r"^(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,98}[A-Za-z0-9])?)/"
    r"(?P<repo>[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,98}[A-Za-z0-9])?)$"
)
_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/@{}+-]{0,254}$")
_COMMON_GIT = [
    "git",
    "/usr/bin/git",
    "/opt/homebrew/bin/git",
    "/usr/local/bin/git",
    r"C:\Program Files\Git\cmd\git.exe",
]
_COMMON_GH = [
    "gh",
    "/opt/homebrew/bin/gh",
    "/usr/local/bin/gh",
    r"C:\Program Files\GitHub CLI\gh.exe",
]


def normalize_repository(value: str) -> tuple[str, str]:
    raw = value.strip()
    if raw.startswith("git@github.com:"):
        raw = raw.removeprefix("git@github.com:")
    elif "://" in raw:
        parsed = urlparse(raw)
        if parsed.scheme not in {"http", "https", "ssh"}:
            raise ValueError("Repository URL must use HTTPS or SSH")
        if (parsed.hostname or "").lower() != "github.com":
            raise ValueError("This provider only accepts github.com repositories")
        raw = parsed.path.lstrip("/")
    raw = raw.removesuffix(".git").strip("/")
    match = _OWNER_REPO_RE.fullmatch(raw)
    if match is None or raw.startswith("-") or "/-" in raw:
        raise ValueError("Repository must use owner/repository or a github.com URL")
    slug = f"{match.group('owner')}/{match.group('repo')}"
    return slug, f"https://github.com/{slug}"


class GitHubRepositoryProvider:
    descriptor = SourceProviderDescriptor(
        id="github.repository",
        label="GitHub repository",
        description=(
            "Create an immutable SAST snapshot from a public or private GitHub repository."
        ),
        request_fields=[
            SourceProviderField(
                key="repository",
                label="Repository",
                required=True,
                placeholder="owner/repository",
                help=(
                    "Use owner/repository or a github.com URL. Private repositories "
                    "use your existing CLI login."
                ),
            ),
            SourceProviderField(
                key="ref",
                label="Branch, tag, or commit",
                placeholder="Default branch",
                help="Leave blank to scan the repository default branch.",
            ),
        ],
        settings_fields=[
            SourceProviderField(
                key="gh_executable",
                label="GitHub CLI",
                type="path",
                placeholder="Automatically detected",
                help="Optional path to the gh executable.",
            ),
            SourceProviderField(
                key="git_executable",
                label="Git",
                type="path",
                placeholder="Automatically detected",
                help="Optional path to the git executable.",
            ),
        ],
    )

    def _git(self, context: SourceProviderContext) -> str | None:
        return context.find_executable("git_executable", _COMMON_GIT)

    def _gh(self, context: SourceProviderContext) -> str | None:
        return context.find_executable("gh_executable", _COMMON_GH)

    async def _gh_authenticated(
        self, context: SourceProviderContext, gh: str | None
    ) -> bool:
        if gh is None:
            return False
        result = await context.run_process(
            [gh, "auth", "status", "--hostname", "github.com"], timeout=10
        )
        return result.returncode == 0

    async def check_availability(
        self, context: SourceProviderContext
    ) -> ProviderAvailability:
        git = self._git(context)
        gh = self._gh(context)
        authenticated = await self._gh_authenticated(context, gh)
        if git is None:
            return ProviderAvailability(
                available=False,
                status="unavailable",
                message="Git was not found. Configure its executable path.",
                details={"git": None, "gh": gh, "authenticated": authenticated},
            )
        message = (
            "GitHub CLI is authenticated. Public and private repositories are available."
            if authenticated
            else (
                "Git is available. Public repositories and repositories available through "
                "your Git credential helper can be used."
            )
        )
        return ProviderAvailability(
            available=True,
            status="ready" if authenticated else "limited",
            message=message,
            details={"git": git, "gh": gh, "authenticated": authenticated},
        )

    async def materialize(
        self,
        parameters: dict[str, Any],
        destination: Path,
        context: SourceProviderContext,
    ) -> MaterializedSource:
        repository = parameters.get("repository")
        if not isinstance(repository, str) or not repository.strip():
            raise ValueError("Repository is required")
        slug, canonical_url = normalize_repository(repository)
        requested_ref = parameters.get("ref")
        if requested_ref is not None:
            if not isinstance(requested_ref, str):
                raise ValueError("Git ref must be text")
            requested_ref = requested_ref.strip() or None
        if requested_ref and (
            not _REF_RE.fullmatch(requested_ref) or requested_ref.startswith("-")
        ):
            raise ValueError("Git ref contains unsupported characters")

        git = self._git(context)
        if git is None:
            raise RuntimeError(
                "Git was not found. Configure the Git extension setting."
            )
        gh = self._gh(context)
        authenticated = await self._gh_authenticated(context, gh)
        repository_dir = destination / "repository.git"
        if authenticated and gh:
            clone = await context.run_process(
                [
                    gh,
                    "repo",
                    "clone",
                    slug,
                    str(repository_dir),
                    "--",
                    "--bare",
                    "--filter=blob:none",
                ],
                cwd=destination,
                timeout=600,
            )
        else:
            clone = await context.run_process(
                [
                    git,
                    "clone",
                    "--bare",
                    "--filter=blob:none",
                    canonical_url,
                    str(repository_dir),
                ],
                cwd=destination,
                timeout=600,
            )
        if clone.returncode != 0:
            detail = clone.stderr or clone.stdout or "Git clone failed"
            raise RuntimeError(detail)

        ref = requested_ref or "HEAD"
        resolved = await context.run_process(
            [
                git,
                "--git-dir",
                str(repository_dir),
                "rev-parse",
                "--verify",
                "--end-of-options",
                f"{ref}^{{commit}}",
            ],
            cwd=destination,
            timeout=30,
        )
        if resolved.returncode != 0:
            raise ValueError(f"Git ref {ref!r} was not found in the repository")
        revision = resolved.stdout.splitlines()[-1].strip()
        if not re.fullmatch(r"[0-9a-fA-F]{40,64}", revision):
            raise RuntimeError("Git returned an invalid commit identifier")

        archive_path = destination / "source.zip"
        archived = await context.run_process(
            [
                git,
                "--git-dir",
                str(repository_dir),
                "archive",
                "--format=zip",
                f"--output={archive_path}",
                revision,
            ],
            cwd=destination,
            timeout=600,
        )
        if archived.returncode != 0 or not archive_path.is_file():
            detail = (
                archived.stderr or archived.stdout or "Could not build source archive"
            )
            raise RuntimeError(detail)

        return MaterializedSource(
            archive_path=archive_path,
            display_name=f"{slug}@{revision[:8]}",
            locator=canonical_url,
            requested_ref=requested_ref,
            revision=revision.lower(),
            metadata={
                "repository": slug,
                "authentication": "github_cli" if authenticated else "git_credentials",
                "submodules_included": False,
                "git_lfs_objects_included": False,
            },
        )


class GitHubRepositoryExtension:
    def register(self, registry: ExtensionRegistry) -> None:
        registry.register_source_provider(GitHubRepositoryProvider())
