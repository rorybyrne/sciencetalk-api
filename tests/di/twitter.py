"""Mock Twitter providers for testing."""

from dishka import Scope, provide

from talk.adapter.twitter.client import MockTwitterOAuthClient, TwitterOAuthClient
from talk.util.di.infrastructure.twitter import TwitterProvider


class MockTwitterProvider(TwitterProvider):
    """Mock Twitter provider using mock OAuth client."""

    __is_mock__ = True

    @provide(scope=Scope.APP)
    def get_twitter_oauth_client(self) -> TwitterOAuthClient:
        """Provide mock Twitter OAuth client."""
        return MockTwitterOAuthClient()
