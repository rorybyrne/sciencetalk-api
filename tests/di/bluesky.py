"""Mock Bluesky providers for testing."""

from dishka import Scope, provide

from talk.adapter.bluesky.auth import BlueskyOAuthClient, MockBlueskyOAuthClient
from talk.util.di.infrastructure.bluesky import BlueskyProvider


class MockBlueskyProvider(BlueskyProvider):
    """Mock Bluesky provider using mock OAuth client."""

    __is_mock__ = True

    @provide(scope=Scope.APP)
    def get_bluesky_oauth_client(self) -> BlueskyOAuthClient:
        """Provide mock Bluesky OAuth client."""
        return MockBlueskyOAuthClient()
