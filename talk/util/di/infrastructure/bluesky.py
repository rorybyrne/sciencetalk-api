"""Bluesky infrastructure providers."""

from dishka import Scope, provide

from talk.adapter.bluesky.auth import BlueskyAuthClient, MockBlueskyAuthClient
from talk.config import Settings
from talk.util.di.base import ProviderBase


class BlueskyProvider(ProviderBase):
    """Bluesky component base."""

    __mock_component__ = "bluesky"


class ProdBlueskyProvider(BlueskyProvider):
    """Production Bluesky provider."""

    __is_mock__ = False

    @provide(scope=Scope.APP)
    def get_bluesky_auth_client(self, settings: Settings) -> BlueskyAuthClient:
        """Provide Bluesky authentication client.

        Returns mock implementation for now. Replace with real implementation
        when OAuth credentials are configured.
        """
        # TODO: Check settings and return real client when configured
        # if settings.auth.bluesky_client_id:
        #     return RealBlueskyAuthClient(...)
        return MockBlueskyAuthClient()
