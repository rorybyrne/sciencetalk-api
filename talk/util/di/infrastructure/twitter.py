"""Twitter infrastructure providers."""

from dishka import Scope, provide

from talk.adapter.twitter.client import (
    RealTwitterOAuthClient,
    TwitterOAuthClient,
)
from talk.config import Settings
from talk.util.di.base import ProviderBase


class TwitterProvider(ProviderBase):
    """Twitter component base."""

    __mock_component__ = "twitter"


class ProdTwitterProvider(TwitterProvider):
    """Production Twitter provider."""

    __is_mock__ = False

    @provide(scope=Scope.APP)
    def get_twitter_oauth_client(self, settings: Settings) -> TwitterOAuthClient:
        """Provide Twitter OAuth client.

        Returns:
            Twitter OAuth 2.0 client

        Raises:
            ValueError: If Twitter OAuth credentials are not configured
        """
        if not settings.auth.twitter.client_id:
            raise ValueError("Twitter OAuth client ID must be configured")
        if not settings.auth.twitter.client_secret:
            raise ValueError("Twitter OAuth client secret must be configured")

        return RealTwitterOAuthClient(
            client_id=settings.auth.twitter.client_id,
            client_secret=settings.auth.twitter.client_secret,
            redirect_uri=settings.auth.oauth_callback_url,
        )
