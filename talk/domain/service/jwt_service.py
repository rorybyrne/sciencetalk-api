"""JWT token domain service."""

from talk.config import AuthSettings
from talk.util.jwt import create_token, verify_token, TokenPayload

from .base import Service


class JWTService(Service):
    """Domain service for JWT token operations."""

    def __init__(self, auth_settings: AuthSettings) -> None:
        """Initialize JWT service.

        Args:
            auth_settings: Authentication settings
        """
        self.auth_settings = auth_settings

    def create_token(self, user_id: str, did: str, handle: str) -> str:
        """Create JWT token for user.

        Args:
            user_id: User ID
            did: Bluesky DID
            handle: Bluesky handle

        Returns:
            JWT token string
        """
        return create_token(user_id, did, handle, self.auth_settings)

    def verify_token(self, token: str) -> TokenPayload:
        """Verify JWT token and extract payload.

        Args:
            token: JWT token string

        Returns:
            Token payload

        Raises:
            JWTError: If token is invalid or expired
        """
        return verify_token(token, self.auth_settings)
