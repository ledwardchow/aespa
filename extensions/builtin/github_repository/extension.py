"""GitHub repository source extension entrypoint."""

from .provider import GitHubRepositoryExtension


def create_extension() -> GitHubRepositoryExtension:
    return GitHubRepositoryExtension()
