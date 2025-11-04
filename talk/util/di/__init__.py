"""Dependency injection module."""

from typing import Type

from talk.util.di.application import ProdApplicationProvider
from talk.util.di.base import Component, ProviderBase
from talk.util.di.core import ProdConfigProvider
from talk.util.di.domain import ProdDomainProvider
from talk.util.di.infrastructure import (
    BlueskyProvider,
    OAuthAggregatorProvider,
    PersistenceProvider,
    ProdBlueskyProvider,
    ProdPersistenceProvider,
    ProdTwitterProvider,
    TwitterProvider,
)

# Single list - all providers treated uniformly
PROVIDERS: list[Type[ProviderBase]] = [
    # Core providers (not mockable)
    ProdConfigProvider,
    ProdDomainProvider,
    ProdApplicationProvider,
    # Infrastructure components (mockable)
    BlueskyProvider,
    TwitterProvider,
    PersistenceProvider,
    # OAuth aggregator (combines all OAuth clients)
    OAuthAggregatorProvider,
]


def get_provider(
    base: Type[ProviderBase], use_mock: bool = False
) -> Type[ProviderBase]:
    """Get appropriate provider class.

    Automatically determines if provider is mockable by checking for subclasses.

    - No subclasses: Concrete provider, use directly
    - Has subclasses: Mockable component, select by __is_mock__ flag

    Args:
        base: Provider base class
        use_mock: Whether to use mock implementation

    Returns:
        Provider class (not instantiated)

    Raises:
        ValueError: If requested implementation not found
    """
    subclasses = base.__subclasses__()

    if not subclasses:
        # Concrete provider - no implementations, use as-is
        return base

    # Has subclasses - it's a mockable component
    # Find implementation by __is_mock__ flag
    impl = next(
        (c for c in subclasses if getattr(c, "__is_mock__", False) == use_mock),
        None,
    )

    if not impl:
        kind = "mock" if use_mock else "production"
        component_name = getattr(base, "__mock_component__", base.__name__)
        raise ValueError(f"No {kind} implementation for {component_name}")

    return impl


__all__ = [
    "Component",
    "ProviderBase",
    "PROVIDERS",
    "get_provider",
    # Core providers
    "ProdConfigProvider",
    "ProdDomainProvider",
    "ProdApplicationProvider",
    # Infrastructure base classes
    "BlueskyProvider",
    "OAuthAggregatorProvider",
    "PersistenceProvider",
    "TwitterProvider",
    # Infrastructure implementations
    "ProdBlueskyProvider",
    "ProdPersistenceProvider",
    "ProdTwitterProvider",
]
