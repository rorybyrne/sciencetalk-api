"""Core DI providers (non-mockable)."""

from dishka import Scope, provide

from talk.config import AuthSettings, Settings
from talk.util.di.base import ProviderBase


class ProdConfigProvider(ProviderBase):
    """Production config provider - concrete, no mocks needed.

    Settings are loaded from environment variables and .env file automatically.
    """

    @provide(scope=Scope.APP)
    def provide_settings(self) -> Settings:
        """Provide application settings from environment."""
        return Settings()

    @provide(scope=Scope.APP)
    def provide_auth_settings(self, settings: Settings) -> AuthSettings:
        """Provide auth settings."""
        return settings.auth
