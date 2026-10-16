"""Trusted, capability-based AESPA extension loading."""

from aespa.extensions.runtime import (
    ExtensionDataStore,
    ExtensionOpenAPI,
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
    "ExtensionOpenAPI",
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
