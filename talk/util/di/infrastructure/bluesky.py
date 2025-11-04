"""Bluesky infrastructure providers."""

from dishka import Scope, provide

from talk.adapter.bluesky.auth import (
    BlueskyOAuthClient,
    RealBlueskyOAuthClient,
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
    def get_bluesky_oauth_client(self, settings: Settings) -> BlueskyOAuthClient:
        """Provide Bluesky OAuth client.

        The client_id is constructed from the base_url as per AT Protocol spec:
        {base_url}/.well-known/oauth-client-metadata

        Returns:
            Bluesky OAuth client
        """
        # Construct client_id from base_url (AT Protocol requirement)
        client_id = f"{settings.api.base_url}/.well-known/oauth-client-metadata"

        return RealBlueskyOAuthClient(
            client_id=client_id,
            redirect_uri=settings.auth.bluesky_callback_url,
        )
