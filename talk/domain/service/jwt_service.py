"""JWT token domain service."""

import logfire

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
        with logfire.span("jwt_service.create_token", user_id=user_id, handle=handle):
            token = create_token(user_id, did, handle, self.auth_settings)
            logfire.info("JWT token created", user_id=user_id, handle=handle)
            return token

    def verify_token(self, token: str) -> TokenPayload:
        """Verify JWT token and extract payload.

        Args:
            token: JWT token string

        Returns:
            Token payload

        Raises:
            JWTError: If token is invalid or expired
        """
        with logfire.span("jwt_service.verify_token"):
            try:
                payload = verify_token(token, self.auth_settings)
                logfire.info(
                    "JWT token verified", user_id=payload.user_id, handle=payload.handle
                )
                return payload
            except Exception as e:
                logfire.error("JWT token verification failed", error=str(e))
                raise

    def get_user_id_from_token(self, token: str | None) -> str | None:
        """Extract user ID from JWT token without raising exceptions.

        This is a convenience method for API routes that need to optionally
        authenticate users without failing on invalid tokens.

        Args:
            token: JWT token string (optional)

        Returns:
            User ID if token is valid, None if token is missing or invalid
        """
        if not token:
            return None

        try:
            payload = self.verify_token(token)
            return payload.user_id
        except Exception as e:
            # Invalid or expired token, treat as unauthenticated
            logfire.debug(
                "JWT verification failed, treating as unauthenticated", error=str(e)
            )
            return None
