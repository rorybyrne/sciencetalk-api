"""OAuth infrastructure provider for multi-provider authentication."""

from dishka import Scope, provide

from talk.adapter.bluesky.auth import BlueskyOAuthClient
from talk.adapter.twitter.client import TwitterOAuthClient
from talk.domain.service.auth_service import OAuthClient
from talk.domain.value import AuthProvider
from talk.util.di.base import ProviderBase


class OAuthAggregatorProvider(ProviderBase):
    """Provider that aggregates all OAuth clients into a dictionary."""

    scope = Scope.APP

    @provide(scope=Scope.APP)
    def get_oauth_clients(
        self,
        bluesky_oauth_client: BlueskyOAuthClient,
        twitter_oauth_client: TwitterOAuthClient,
    ) -> dict[AuthProvider, OAuthClient]:
        """Provide dictionary of all OAuth clients by provider.

        This allows the AuthService to support multiple authentication providers.

        Args:
            bluesky_oauth_client: Bluesky OAuth client (specific type)
            twitter_oauth_client: Twitter OAuth client (specific type)

        Returns:
            Dictionary mapping AuthProvider to OAuthClient
        """
        return {
            AuthProvider.BLUESKY: bluesky_oauth_client,
            AuthProvider.TWITTER: twitter_oauth_client,
        }
