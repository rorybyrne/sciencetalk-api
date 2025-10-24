"""Domain layer DI providers."""

from dishka import Provider, Scope


class DomainProvider(Provider):
    """Domain services provider."""

    scope = Scope.APP
