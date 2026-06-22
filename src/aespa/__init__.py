"""AESPA: LLM-based pentesting agent (site configuration module)."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("aespa")
except PackageNotFoundError:
    __version__ = "unknown"

from aespa.main import main

__all__ = ["main", "__version__"]
