"""Mock Bluesky providers for testing."""

from dishka import Scope, provide

from talk.adapter.bluesky.auth import BlueskyAuthClient, MockBlueskyAuthClient
from talk.util.di.infrastructure.bluesky import BlueskyProvider


class MockBlueskyProvider(BlueskyProvider):
    """Mock Bluesky provider using mock auth client."""

    __is_mock__ = True

    @provide(scope=Scope.APP)
    def get_bluesky_auth_client(self) -> BlueskyAuthClient:
        """Provide mock Bluesky authentication client."""
        return MockBlueskyAuthClient()
