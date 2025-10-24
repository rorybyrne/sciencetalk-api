"""Adapter DI providers."""

from dishka import Provider, Scope


class AdapterProvider(Provider):
    """Adapter Provider."""

    scope = Scope.APP
