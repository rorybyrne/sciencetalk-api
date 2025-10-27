"""Bluesky infrastructure providers."""

from dishka import Scope, provide

from talk.adapter.bluesky.auth import (
    ATProtocolOAuthClient,
    BlueskyAuthClient,
    MockBlueskyAuthClient,
)
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

        Uses real AT Protocol OAuth client when configured, otherwise mock.
        """
        if settings.auth.oauth_client_id and settings.auth.oauth_redirect_uri:
            return ATProtocolOAuthClient(
                client_id=settings.auth.oauth_client_id,
                redirect_uri=settings.auth.oauth_redirect_uri,
            )
        return MockBlueskyAuthClient()
