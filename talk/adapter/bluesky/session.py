"""OAuth session state management for AT Protocol authentication."""

from datetime import datetime, timezone
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from talk.adapter.bluesky.dpop import DPoPKeyPair


class OAuthSession(BaseModel):
    """OAuth session state for PKCE and DPoP management.

    OAuth flow spans multiple HTTP requests (authorization → callback),
    so we need to maintain state between them. This includes:
    - PKCE verifier (secret) for token exchange
    - DPoP keypair (secret) for proof signing
    - Server nonces for retry handling

    Sessions are temporary (15 min expiry) and don't need persistence
    since they only exist during the authentication flow.

    Attributes:
        state: Random state parameter for CSRF protection
        pkce_verifier: PKCE code verifier (secret, kept by client)
        pkce_challenge: PKCE code challenge (sent in authorization request)
        dpop_keypair: ES256 keypair for DPoP proof signing
        account_did: Expected DID for verification after token exchange
        auth_server_issuer: Authorization server issuer URL
        created_at: Session creation timestamp
        expires_at: Session expiration timestamp (15 minutes from creation)
        auth_server_nonce: Server nonce from auth server (updated during flow)
        pds_nonce: Server nonce from PDS (updated during flow)
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    state: str
    pkce_verifier: str
    pkce_challenge: str
    dpop_keypair: DPoPKeyPair
    account_did: str | None
    auth_server_issuer: str
    created_at: datetime
    expires_at: datetime
    auth_server_nonce: str | None = None
    pds_nonce: str | None = None


class OAuthSessionStore(Protocol):
    """Protocol for storing temporary OAuth sessions.

    Sessions are keyed by the random state parameter and expire
    after 15 minutes per AT Protocol specification.
    """

    async def save(self, state: str, session: OAuthSession) -> None:
        """Save session by state parameter.

        Args:
            state: Random state parameter from authorization request
            session: OAuth session to store
        """
        ...

    async def get(self, state: str) -> OAuthSession | None:
        """Retrieve session by state parameter.

        Args:
            state: Random state parameter from callback

        Returns:
            OAuth session if found and not expired, None otherwise
        """
        ...

    async def delete(self, state: str) -> None:
        """Delete session after completion or expiry.

        Args:
            state: Random state parameter
        """
        ...


class InMemorySessionStore:
    """In-memory OAuth session store.

    Sufficient for OAuth flow since sessions are temporary (15 min).
    Sessions don't need to survive server restarts - users can just
    restart the authentication flow if the server restarts.

    In production with multiple servers, consider:
    - Sticky sessions (route user to same server)
    - Redis for shared session storage
    - Database-backed sessions

    Attributes:
        _sessions: Dict mapping state → OAuthSession
    """

    def __init__(self) -> None:
        """Initialize empty session store."""
        self._sessions: dict[str, OAuthSession] = {}

    async def save(self, state: str, session: OAuthSession) -> None:
        """Save session by state parameter."""
        self._sessions[state] = session

    async def get(self, state: str) -> OAuthSession | None:
        """Retrieve session by state parameter.

        Automatically deletes expired sessions.
        """
        session = self._sessions.get(state)

        # Check expiry and clean up if expired
        if session and session.expires_at < datetime.now(timezone.utc):
            await self.delete(state)
            return None

        return session

    async def delete(self, state: str) -> None:
        """Delete session by state parameter."""
        self._sessions.pop(state, None)
