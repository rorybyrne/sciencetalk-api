"""Base classes for dependency injection providers."""

from typing import ClassVar, Literal

from dishka import Provider

Component = Literal["bluesky", "persistence"]


class ProviderBase(Provider):
    """Base for all DI providers with unified metadata.

    Attributes:
        __mock_component__: Component name (for mockable components, None for concrete providers)
        __is_mock__: Whether this is a mock implementation
    """

    __mock_component__: ClassVar[Component | None] = None
    __is_mock__: ClassVar[bool] = False
