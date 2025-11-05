"""Twitter OAuth 2.0 client implementation.

Implements OAuth 2.0 with PKCE for Twitter authentication.
"""

import hashlib
import secrets
from base64 import urlsafe_b64encode
from urllib.parse import urlencode

import httpx
import logfire

from talk.domain.service.auth_service import OAuthClient
from talk.domain.value.types import AuthProvider, OAuthProviderInfo


class TwitterOAuthError(Exception):
    """Twitter OAuth error."""

    pass


class TwitterOAuthClient(OAuthClient):
    """Base class for Twitter OAuth clients.

    Provides type distinction for dependency injection.
    """

    pass


class RealTwitterOAuthClient(TwitterOAuthClient):
    """Twitter OAuth 2.0 client with PKCE support.

    Implements OAuth 2.0 Authorization Code Flow with PKCE as required by Twitter.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ) -> None:
        """Initialize Twitter OAuth client.

        Args:
            client_id: Twitter OAuth client ID
            client_secret: Twitter OAuth client secret
            redirect_uri: Callback URL registered with Twitter
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

        # OAuth endpoints
        self.authorize_url = "https://twitter.com/i/oauth2/authorize"
        self.token_url = "https://api.twitter.com/2/oauth2/token"
        self.user_info_url = "https://api.twitter.com/2/users/me"

        # Store PKCE verifiers per state (simple in-memory storage)
        # In production, use Redis or similar for distributed systems
        self._pkce_verifiers: dict[str, str] = {}

    def _generate_pkce_pair(self) -> tuple[str, str]:
        """Generate PKCE code verifier and challenge.

        Returns:
            Tuple of (verifier, challenge)
        """
        # Generate code verifier (43-128 characters)
        code_verifier = urlsafe_b64encode(secrets.token_bytes(32)).decode("utf-8")
        code_verifier = code_verifier.rstrip("=")  # Remove padding

        # Generate code challenge (SHA256 hash of verifier)
        challenge_bytes = hashlib.sha256(code_verifier.encode("utf-8")).digest()
        code_challenge = urlsafe_b64encode(challenge_bytes).decode("utf-8")
        code_challenge = code_challenge.rstrip("=")  # Remove padding

        return code_verifier, code_challenge

    async def initiate_authorization(self, state: str) -> str:
        """Initiate Twitter OAuth authorization flow.

        Args:
            state: State parameter for CSRF protection

        Returns:
            Authorization URL to redirect user to
        """
        # Generate PKCE pair
        code_verifier, code_challenge = self._generate_pkce_pair()

        # Store verifier for later token exchange
        self._pkce_verifiers[state] = code_verifier

        # Build authorization URL
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "tweet.read users.read offline.access",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        auth_url = f"{self.authorize_url}?{urlencode(params)}"

        logfire.info(
            "Twitter OAuth authorization initiated",
            state=state,
            redirect_uri=self.redirect_uri,
        )

        return auth_url

    async def complete_authorization(
        self, code: str, state: str, iss: str | None = None
    ) -> OAuthProviderInfo:
        """Complete Twitter OAuth authorization flow.

        Args:
            code: Authorization code from Twitter callback
            state: State parameter for verification
            iss: Issuer URL (unused by Twitter, accepted for interface compatibility)

        Returns:
            User information from Twitter

        Raises:
            TwitterOAuthError: If OAuth flow fails
        """
        _ = iss  # Unused by Twitter
        # Retrieve PKCE verifier
        code_verifier = self._pkce_verifiers.pop(state, None)
        if not code_verifier:
            raise TwitterOAuthError("Invalid state or PKCE verifier not found")

        # Exchange code for access token
        access_token = await self._exchange_code_for_token(code, code_verifier)

        # Get user info
        user_info = await self._get_user_info(access_token)

        # Use username without @ prefix for uniformity
        # Lowercase for provider_user_id to ensure case-insensitive matching
        username = user_info["username"]
        normalized_username = username.lower()

        logfire.info(
            "Twitter OAuth completed",
            username=username,
            user_id=user_info["id"],
        )

        return OAuthProviderInfo(
            provider=AuthProvider.TWITTER,
            provider_user_id=normalized_username,  # Lowercase for case-insensitive matching
            handle=username,  # Keep original case for display
            email=user_info.get("email"),  # May be None if not approved by Twitter
            display_name=user_info.get("name"),
            avatar_url=user_info.get("profile_image_url"),
            verified=user_info.get("verified", False),
        )

    async def _exchange_code_for_token(self, code: str, code_verifier: str) -> str:
        """Exchange authorization code for access token.

        Args:
            code: Authorization code from callback
            code_verifier: PKCE code verifier

        Returns:
            Access token

        Raises:
            TwitterOAuthError: If token exchange fails
        """
        data = {
            "code": code,
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "code_verifier": code_verifier,
        }

        # Use Basic Auth with client credentials
        auth = (self.client_id, self.client_secret)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.token_url,
                    data=data,
                    auth=auth,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=30.0,
                )

                if response.status_code != 200:
                    error_detail = response.text
                    logfire.error(
                        "Twitter token exchange failed",
                        status_code=response.status_code,
                        error=error_detail,
                    )
                    raise TwitterOAuthError(
                        f"Token exchange failed: {response.status_code}"
                    )

                result = response.json()
                return result["access_token"]

        except httpx.HTTPError as e:
            logfire.error("Twitter token exchange HTTP error", error=str(e))
            raise TwitterOAuthError(f"HTTP error during token exchange: {e}")

    async def _get_user_info(self, access_token: str) -> dict:
        """Get user information from Twitter API.

        Args:
            access_token: OAuth access token

        Returns:
            User information dictionary

        Raises:
            TwitterOAuthError: If API request fails
        """
        # Request user fields
        params = {"user.fields": "id,name,username,profile_image_url,verified"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.user_info_url,
                    params=params,
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=30.0,
                )

                if response.status_code != 200:
                    error_detail = response.text
                    logfire.error(
                        "Twitter user info request failed",
                        status_code=response.status_code,
                        error=error_detail,
                    )
                    raise TwitterOAuthError(
                        f"User info request failed: {response.status_code}"
                    )

                result = response.json()
                return result["data"]

        except httpx.HTTPError as e:
            logfire.error("Twitter user info HTTP error", error=str(e))
            raise TwitterOAuthError(f"HTTP error fetching user info: {e}")


class MockTwitterOAuthClient(TwitterOAuthClient):
    """Mock Twitter OAuth client for testing.

    Returns deterministic test data without making real API calls.
    """

    def __init__(self):
        """Initialize mock client without real OAuth configuration."""
        # Don't call super().__init__() - mock doesn't need real config
        pass

    async def initiate_authorization(self, state: str) -> str:
        """Return mock authorization URL.

        Args:
            state: State parameter for CSRF protection

        Returns:
            Mock authorization URL
        """
        return f"https://twitter.com/i/oauth2/authorize?state={state}&mock=true"

    async def complete_authorization(
        self, code: str, state: str, iss: str | None = None
    ) -> OAuthProviderInfo:
        """Return mock user information.

        Args:
            code: Authorization code (unused in mock)
            state: State parameter (unused in mock)
            iss: Issuer URL (unused in mock)

        Returns:
            Mock Twitter user information
        """
        return OAuthProviderInfo(
            provider=AuthProvider.TWITTER,
            provider_user_id="mocktwitter123",
            handle="mockuser",
            email="mock@twitter.com",
            display_name="Mock Twitter User",
            avatar_url="https://example.com/avatar.jpg",
            verified=False,
        )
