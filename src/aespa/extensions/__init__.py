"""Trusted, capability-based AESPA extension loading."""

from aespa.extensions.runtime import (
    ExtensionDataStore,
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
from aespa.services.extension_llm_catalog import (
    ExtensionLLMCatalog,
    ExtensionLLMModel,
    ExtensionLLMProfile,
    ExtensionLLMProvider,
    ExtensionLLMSnapshot,
)

__all__ = [
    "ExtensionLLMCatalog",
    "ExtensionLLMModel",
    "ExtensionLLMProfile",
    "ExtensionLLMProvider",
    "ExtensionLLMSnapshot",
    "ExtensionRegistry",
    "ExtensionDataStore",
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
