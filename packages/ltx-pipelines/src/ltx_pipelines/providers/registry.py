"""Model registry for discovering and instantiating providers.

The registry is the single entry point for getting providers:
    from ltx_pipelines.providers import get_provider, list_providers
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ltx_pipelines.providers.base import VideoGenerationProvider

logger = logging.getLogger(__name__)

# Global registry: provider_id → provider factory or instance
_registry: dict[str, type[VideoGenerationProvider] | VideoGenerationProvider] = {}


def register_provider(
    provider_id: str,
    provider: type[VideoGenerationProvider] | VideoGenerationProvider,
) -> None:
    """Register a provider class or instance.

    Args:
        provider_id: Unique identifier (e.g., 'veo', 'seedance').
        provider: A provider class (instantiated on first get) or instance.
    """
    if provider_id in _registry:
        logger.warning("Overwriting registered provider: %s", provider_id)
    _registry[provider_id] = provider
    logger.info("Registered provider: %s", provider_id)


def get_provider(provider_id: str) -> VideoGenerationProvider:
    """Get a provider instance by ID.

    If a class was registered, it will be instantiated (no-arg constructor).

    Args:
        provider_id: The provider identifier.

    Returns:
        An instantiated VideoGenerationProvider.

    Raises:
        KeyError: If provider_id is not registered.
    """
    if provider_id not in _registry:
        available = ", ".join(sorted(_registry.keys())) or "(none)"
        msg = f"Provider '{provider_id}' not found. Available providers: {available}"
        raise KeyError(msg)

    entry = _registry[provider_id]

    # If it's a class, instantiate it and cache the instance
    if isinstance(entry, type):
        logger.debug("Instantiating provider class for: %s", provider_id)
        instance = entry()
        _registry[provider_id] = instance
        return instance

    return entry


def list_providers() -> list[str]:
    """List all registered provider IDs.

    Returns:
        Sorted list of provider identifiers.
    """
    return sorted(_registry.keys())


def clear_registry() -> None:
    """Remove all registered providers. Useful for testing."""
    _registry.clear()
