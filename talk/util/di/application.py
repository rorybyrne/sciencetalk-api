"""Application layer DI providers."""

from dishka import Provider, Scope


class ApplicationProvider(Provider):
    """Application use cases provider."""

    scope = Scope.APP
