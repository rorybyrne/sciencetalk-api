"""Authentication domain service."""

from talk.domain.value.types import AuthProvider, OAuthProviderInfo

from .base import Service


class OAuthClient:
    """Generic OAuth client interface for all providers."""

    async def initiate_authorization(self, state: str) -> str:
        """Initiate OAuth authorization flow.

        Args:
            state: State parameter for CSRF protection

        Returns:
            Authorization URL to redirect user to
        """
        raise NotImplementedError

    async def complete_authorization(
        self, code: str, state: str, iss: str | None = None
    ) -> OAuthProviderInfo:
        """Complete OAuth authorization flow.

        Args:
            code: Authorization code from OAuth callback
            state: State parameter for verification
            iss: Issuer URL (optional, required by some providers like Bluesky)

        Returns:
            Provider user information
        """
        raise NotImplementedError


class AuthService(Service):
    """Domain service for multi-provider authentication operations.

    Coordinates authentication across multiple OAuth providers
    (Bluesky, ORCID, Twitter).
    """

    def __init__(self, oauth_clients: dict[AuthProvider, OAuthClient]) -> None:
        """Initialize auth service.

        Args:
            oauth_clients: Map of provider to OAuth client implementation
        """
        self.oauth_clients = oauth_clients

    async def initiate_login(self, provider: AuthProvider, state: str) -> str:
        """Initiate OAuth login flow for any provider.

        Args:
            provider: Authentication provider to use
            state: State parameter for CSRF protection

        Returns:
            Authorization URL to redirect user to

        Raises:
            ValueError: If provider not supported
        """
        client = self.oauth_clients.get(provider)
        if not client:
            raise ValueError(f"Unsupported provider: {provider}")

        return await client.initiate_authorization(state)

    async def complete_login(
        self, provider: AuthProvider, code: str, state: str, iss: str | None = None
    ) -> OAuthProviderInfo:
        """Complete OAuth login flow for any provider.

        Args:
            provider: Authentication provider used
            code: Authorization code from OAuth callback
            state: State parameter for verification
            iss: Issuer URL (optional, required by Bluesky, unused by other providers)

        Returns:
            User authentication information from provider

        Raises:
            ValueError: If provider not supported
        """
        client = self.oauth_clients.get(provider)
        if not client:
            raise ValueError(f"Unsupported provider: {provider}")

        return await client.complete_authorization(code, state, iss)
