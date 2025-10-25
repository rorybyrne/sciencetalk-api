"""Bluesky OAuth authentication adapter."""

from typing import Protocol

from pydantic import BaseModel


class BlueskyUserInfo(BaseModel):
    """User information from Bluesky."""

    did: str
    handle: str
    display_name: str | None = None
    avatar_url: str | None = None


class BlueskyAuthClient(Protocol):
    """Protocol for Bluesky authentication client."""

    def get_authorization_url(self) -> str:
        """Get the OAuth authorization URL to redirect users to.

        Returns:
            Authorization URL
        """
        ...

    async def exchange_code_for_token(self, code: str) -> str:
        """Exchange authorization code for access token.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            Access token

        Raises:
            BlueskyAuthError: If token exchange fails
        """
        ...

    async def get_user_info(self, access_token: str) -> BlueskyUserInfo:
        """Get user information using access token.

        Args:
            access_token: Access token from OAuth

        Returns:
            User information (DID, handle, display name, avatar)

        Raises:
            BlueskyAuthError: If fetching user info fails
        """
        ...


class BlueskyAuthError(Exception):
    """Bluesky authentication error."""

    pass


# TODO: Implement real Bluesky OAuth client
# For now, we'll create a mock implementation for development
class MockBlueskyAuthClient:
    """Mock Bluesky authentication client for development."""

    def get_authorization_url(self) -> str:
        """Get mock authorization URL."""
        return "https://bsky.app/oauth/authorize?mock=true"

    async def exchange_code_for_token(self, code: str) -> str:
        """Exchange mock code for mock token."""
        if code == "invalid":
            raise BlueskyAuthError("Invalid authorization code")
        return f"mock_token_{code}"

    async def get_user_info(self, access_token: str) -> BlueskyUserInfo:
        """Get mock user info."""
        # Extract user from token for testing
        return BlueskyUserInfo(
            did="did:plc:mock123",
            handle="user.bsky.social",
            display_name="Test User",
            avatar_url="https://example.com/avatar.jpg",
        )
