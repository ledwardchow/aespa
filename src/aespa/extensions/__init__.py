"""Trusted, capability-based AESPA extension loading."""

from aespa.extensions.runtime import (
    ExtensionRegistry,
    MaterializedSource,
    ProviderAvailability,
    SourceProviderContext,
    SourceProviderDescriptor,
    SourceProviderField,
    get_extension_manager,
)

__all__ = [
    "ExtensionRegistry",
    "MaterializedSource",
    "ProviderAvailability",
    "SourceProviderContext",
    "SourceProviderDescriptor",
    "SourceProviderField",
    "get_extension_manager",
]
