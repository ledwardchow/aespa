"""Trusted, capability-based AESPA extension loading."""

from aespa.extensions.runtime import (
    ExtensionRegistry,
    ExtensionSecretStore,
    MaterializedSource,
    ProviderAvailability,
    SourceProviderContext,
    SourceProviderDescriptor,
    SourceProviderField,
    WebScanCandidate,
    WebScanContext,
    WebScanIssue,
    WebScanResult,
    get_extension_manager,
)

__all__ = [
    "ExtensionRegistry",
    "ExtensionSecretStore",
    "MaterializedSource",
    "ProviderAvailability",
    "SourceProviderContext",
    "SourceProviderDescriptor",
    "SourceProviderField",
    "WebScanCandidate",
    "WebScanContext",
    "WebScanIssue",
    "WebScanResult",
    "get_extension_manager",
]
