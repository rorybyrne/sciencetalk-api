"""Authentication domain service."""

from talk.adapter.bluesky.auth import BlueskyAuthClient
from talk.domain.value.types import UserAuthInfo

from .base import Service


class AuthService(Service):
    """Domain service for authentication operations.

    Wraps the AT Protocol OAuth client to provide domain-level
    authentication operations.
    """

    def __init__(self, bluesky_client: BlueskyAuthClient) -> None:
        """Initialize auth service.

        Args:
            bluesky_client: Bluesky authentication client
        """
        self.bluesky_client = bluesky_client

    async def initiate_login(self, account: str) -> str:
        """Initiate OAuth login flow.

        Args:
            account: Bluesky handle (e.g., "alice.bsky.social") or DID

        Returns:
            Authorization URL to redirect user to

        Raises:
            BlueskyAuthError: If initialization fails
        """
        return await self.bluesky_client.initiate_authorization(account)

    async def complete_login(self, code: str, state: str, iss: str) -> UserAuthInfo:
        """Complete OAuth login flow.

        Args:
            code: Authorization code from OAuth callback
            state: State parameter for session verification
            iss: Issuer parameter for verification

        Returns:
            User authentication information

        Raises:
            BlueskyAuthError: If completion fails
        """
        user_info = await self.bluesky_client.complete_authorization(code, state, iss)

        return UserAuthInfo(
            did=user_info.did,
            handle=user_info.handle,
            display_name=user_info.display_name,
            avatar_url=user_info.avatar_url,
        )
