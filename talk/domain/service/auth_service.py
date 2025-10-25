"""Authentication domain service."""

from talk.adapter.bluesky.auth import BlueskyAuthClient
from talk.domain.value.types import UserAuthInfo

from .base import Service


class AuthService(Service):
    """Domain service for authentication operations."""

    def __init__(self, bluesky_client: BlueskyAuthClient) -> None:
        """Initialize auth service.

        Args:
            bluesky_client: Bluesky authentication client
        """
        self.bluesky_client = bluesky_client

    def get_oauth_url(self) -> str:
        """Get OAuth authorization URL.

        Returns:
            Authorization URL for user to visit
        """
        return self.bluesky_client.get_authorization_url()

    async def authenticate_with_code(self, code: str) -> UserAuthInfo:
        """Authenticate user with OAuth code.

        Args:
            code: OAuth authorization code

        Returns:
            User authentication information

        Raises:
            BlueskyAuthError: If authentication fails
        """
        access_token = await self.bluesky_client.exchange_code_for_token(code)
        user_info = await self.bluesky_client.get_user_info(access_token)

        return UserAuthInfo(
            did=user_info.did,
            handle=user_info.handle,
            display_name=user_info.display_name,
            avatar_url=user_info.avatar_url,
        )
