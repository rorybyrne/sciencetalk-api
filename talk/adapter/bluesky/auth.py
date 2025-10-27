"""Bluesky OAuth authentication adapter."""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Protocol

import httpx
from pydantic import BaseModel

from talk.adapter.bluesky.dpop import DPoPKeyPair, create_dpop_proof
from talk.adapter.bluesky.identity import (
    get_pds_endpoint,
    resolve_did_document,
    resolve_handle_to_did,
)
from talk.adapter.bluesky.metadata import discover_auth_server
from talk.adapter.bluesky.pkce import generate_pkce_pair
from talk.adapter.bluesky.session import InMemorySessionStore, OAuthSession
from talk.domain.value.types import BlueskyDID

logger = logging.getLogger(__name__)


class BlueskyUserInfo(BaseModel):
    """User information from Bluesky."""

    did: str
    handle: str
    display_name: str | None = None
    avatar_url: str | None = None


class BlueskyAuthClient(Protocol):
    """Protocol for Bluesky authentication client."""

    async def initiate_authorization(self, account_identifier: str) -> str:
        """Initiate OAuth authorization flow.

        Args:
            account_identifier: Bluesky handle or DID

        Returns:
            Authorization URL to redirect user to

        Raises:
            BlueskyAuthError: If initialization fails
        """
        ...

    async def complete_authorization(
        self, code: str, state: str, iss: str
    ) -> BlueskyUserInfo:
        """Complete OAuth authorization flow.

        Args:
            code: Authorization code from callback
            state: State parameter from callback
            iss: Issuer parameter from callback

        Returns:
            User information extracted from Bluesky

        Raises:
            BlueskyAuthError: If completion fails
        """
        ...


class BlueskyAuthError(Exception):
    """Bluesky authentication error."""

    pass


class ATProtocolOAuthClient:
    """Real AT Protocol OAuth client implementation.

    Implements the full OAuth flow with PKCE, DPoP, and PAR as required
    by AT Protocol specification.
    """

    def __init__(
        self,
        client_id: str,
        redirect_uri: str,
        session_store: InMemorySessionStore | None = None,
    ):
        """Initialize AT Protocol OAuth client.

        Args:
            client_id: OAuth client ID (metadata URL)
            redirect_uri: OAuth callback URL
            session_store: Session store for OAuth state (creates new if None)
        """
        self._client_id = client_id
        self._redirect_uri = redirect_uri
        self._session_store = session_store or InMemorySessionStore()

    async def initiate_authorization(self, account_identifier: str) -> str:
        """Initiate OAuth authorization flow.

        This method:
        1. Resolves handle to DID and PDS endpoint
        2. Discovers authorization server metadata
        3. Generates PKCE and DPoP credentials
        4. Makes Pushed Authorization Request (PAR)
        5. Creates temporary session
        6. Returns authorization URL

        Args:
            account_identifier: Bluesky handle (e.g., "alice.bsky.social") or DID

        Returns:
            Authorization URL to redirect user to

        Raises:
            BlueskyAuthError: If initialization fails at any step
        """
        try:
            logger.info(f"OAuth login initiated for account: {account_identifier}")

            # Step 1: Resolve account to DID
            if account_identifier.startswith("did:"):
                did = BlueskyDID(account_identifier)
            else:
                did = await resolve_handle_to_did(account_identifier)

            logger.info(f"Resolved to DID: {did}")

            # Step 2: Resolve DID to PDS endpoint
            did_document = await resolve_did_document(did)
            pds_url = get_pds_endpoint(did_document)

            logger.info(f"Using PDS: {pds_url}")

            # Step 3: Discover authorization server metadata
            auth_metadata = await discover_auth_server(pds_url)

            logger.info(f"Using auth server: {auth_metadata.issuer}")

            # Step 4: Generate PKCE pair and DPoP keypair
            pkce_verifier, pkce_challenge = generate_pkce_pair()
            dpop_keypair = DPoPKeyPair()

            # Step 5: Generate random state parameter
            state = secrets.token_urlsafe(32)

            # Step 6: Make Pushed Authorization Request
            request_uri, dpop_nonce = await self._make_par_request(
                par_endpoint=auth_metadata.pushed_authorization_request_endpoint,
                pkce_challenge=pkce_challenge,
                dpop_keypair=dpop_keypair,
                login_hint=str(did),
                state=state,
            )

            # Step 7: Create and save OAuth session
            session = OAuthSession(
                state=state,
                pkce_verifier=pkce_verifier,
                pkce_challenge=pkce_challenge,
                dpop_keypair=dpop_keypair,
                account_did=str(did),
                auth_server_issuer=auth_metadata.issuer,
                auth_server_nonce=dpop_nonce,  # Save nonce from PAR for token exchange
                created_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
            )
            await self._session_store.save(state, session)

            # Step 8: Build authorization URL
            auth_url = (
                f"{auth_metadata.authorization_endpoint}"
                f"?client_id={self._client_id}"
                f"&request_uri={request_uri}"
            )

            logger.info(f"Generated authorization URL for {did}")
            return auth_url

        except BlueskyAuthError as e:
            logger.error(
                f"OAuth initiation failed for {account_identifier}: {str(e)}",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"OAuth initiation failed for {account_identifier}: {str(e)}",
                exc_info=True,
            )
            raise BlueskyAuthError(f"Failed to initiate authorization: {e}") from e

    async def complete_authorization(
        self, code: str, state: str, iss: str
    ) -> BlueskyUserInfo:
        """Complete OAuth authorization flow.

        This method:
        1. Retrieves OAuth session by state
        2. Verifies issuer matches expected
        3. Exchanges code for access token (with DPoP)
        4. Fetches user profile (with DPoP + ath)
        5. Verifies DID matches expected
        6. Deletes session and discards tokens
        7. Returns user info

        Args:
            code: Authorization code from OAuth callback
            state: State parameter for session lookup
            iss: Issuer URL to verify

        Returns:
            User information (DID, handle, display name, avatar)

        Raises:
            BlueskyAuthError: If completion fails or verification fails
        """
        try:
            logger.info(f"OAuth callback received from issuer: {iss}")

            # Step 1: Retrieve OAuth session
            session = await self._session_store.get(state)
            if not session:
                logger.warning(f"OAuth callback with invalid/expired state: {state}")
                raise BlueskyAuthError("Invalid or expired OAuth session")

            # Step 2: Verify issuer
            if iss != session.auth_server_issuer:
                logger.error(
                    f"Issuer mismatch: expected {session.auth_server_issuer}, got {iss}"
                )
                raise BlueskyAuthError(
                    f"Issuer mismatch: expected {session.auth_server_issuer}, got {iss}"
                )

            # Step 3: Discover auth server metadata (for token endpoint)
            auth_metadata = await discover_auth_server(iss)

            # Step 4: Exchange code for access token
            access_token = await self._exchange_code_for_token(
                token_endpoint=auth_metadata.token_endpoint,
                code=code,
                session=session,
            )

            if not session.account_did:
                raise BlueskyAuthError("Missing account DID in session")

            # Step 5: Resolve DID to PDS endpoint for profile fetch
            did = BlueskyDID(session.account_did)
            did_document = await resolve_did_document(did)
            pds_url = get_pds_endpoint(did_document)

            # Step 6: Fetch user profile
            user_info = await self._get_user_profile(
                pds_url=pds_url,
                access_token=access_token,
                dpop_keypair=session.dpop_keypair,
                pds_nonce=session.pds_nonce,
            )

            # Step 7: CRITICAL - Verify DID matches expected account
            if user_info.did != session.account_did:
                raise BlueskyAuthError(
                    f"DID mismatch: expected {session.account_did}, got {user_info.did}"
                )

            # Step 8: Clean up session (tokens discarded automatically)
            await self._session_store.delete(state)

            logger.info(
                f"OAuth login successful for {user_info.handle} (DID: {user_info.did})"
            )
            return user_info

        except BlueskyAuthError as e:
            logger.error(f"OAuth callback failed: {str(e)}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"OAuth callback failed: {str(e)}", exc_info=True)
            raise BlueskyAuthError(f"Failed to complete authorization: {e}") from e

    async def _make_par_request(
        self,
        par_endpoint: str,
        pkce_challenge: str,
        dpop_keypair: DPoPKeyPair,
        login_hint: str,
        state: str,
        nonce: str | None = None,
    ) -> tuple[str, str | None]:
        """Make Pushed Authorization Request (PAR).

        Args:
            par_endpoint: PAR endpoint URL
            pkce_challenge: PKCE code challenge
            dpop_keypair: DPoP keypair for proof
            login_hint: DID to hint to auth server
            state: State parameter
            nonce: Server nonce (for retry)

        Returns:
            Tuple of (request_uri token, DPoP nonce from server)

        Raises:
            BlueskyAuthError: If PAR request fails
        """
        logger.debug(
            f"Making PAR request to {par_endpoint} (nonce={'present' if nonce else 'none'})"
        )

        # Create DPoP proof for PAR request
        dpop_proof = create_dpop_proof(
            http_method="POST",
            http_url=par_endpoint,
            keypair=dpop_keypair,
            nonce=nonce,
        )

        # Prepare PAR request
        headers = {
            "DPoP": dpop_proof.serialize(),
            "Content-Type": "application/x-www-form-urlencoded",
        }

        data = {
            "client_id": self._client_id,
            "response_type": "code",
            "code_challenge": pkce_challenge,
            "code_challenge_method": "S256",
            "redirect_uri": self._redirect_uri,
            "scope": "atproto",
            "state": state,
            "login_hint": login_hint,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(par_endpoint, headers=headers, data=data)

            logger.debug(f"PAR response status: {response.status_code}")

            # Handle DPoP nonce requirement (can be 400 or 401)
            if response.status_code in [400, 401]:
                try:
                    error_data = response.json()
                    if error_data.get("error") == "use_dpop_nonce":
                        # Get nonce from response header
                        new_nonce = response.headers.get("DPoP-Nonce")
                        if not new_nonce:
                            logger.error(
                                f"Server requires nonce but didn't provide DPoP-Nonce header. "
                                f"Status: {response.status_code}, Headers: {dict(response.headers)}"
                            )
                            raise BlueskyAuthError(
                                f"Missing DPoP-Nonce in {response.status_code} response"
                            )

                        logger.info("Retrying PAR request with DPoP nonce")
                        return await self._make_par_request(
                            par_endpoint=par_endpoint,
                            pkce_challenge=pkce_challenge,
                            dpop_keypair=dpop_keypair,
                            login_hint=login_hint,
                            state=state,
                            nonce=new_nonce,
                        )
                except ValueError:
                    # Response isn't JSON, fall through to error handling below
                    pass

            # Log error details before raising
            if response.status_code >= 400:
                try:
                    error_body = response.json()
                    logger.error(
                        f"PAR request failed (status {response.status_code}): {error_body}"
                    )
                except Exception:
                    logger.error(
                        f"PAR request failed (status {response.status_code}): {response.text}"
                    )

            response.raise_for_status()

            # Validate DPoP-Nonce header is present (required by spec)
            dpop_nonce = response.headers.get("DPoP-Nonce")
            if not dpop_nonce:
                logger.error(
                    "PAR response missing required DPoP-Nonce header "
                    f"(headers: {dict(response.headers)})"
                )
                raise BlueskyAuthError(
                    "PAR response missing required DPoP-Nonce header"
                )

            result = response.json()

            # Extract request_uri from response
            request_uri = result.get("request_uri")
            if not request_uri:
                raise BlueskyAuthError("Missing request_uri in PAR response")

            logger.debug("PAR successful: request_uri obtained, nonce received")

            return request_uri, dpop_nonce

    async def _exchange_code_for_token(
        self,
        token_endpoint: str,
        code: str,
        session: OAuthSession,
    ) -> str:
        """Exchange authorization code for access token.

        Args:
            token_endpoint: Token endpoint URL
            code: Authorization code
            session: OAuth session with PKCE and DPoP (includes nonce from PAR)

        Returns:
            Access token

        Raises:
            BlueskyAuthError: If token exchange fails
        """
        logger.debug(
            f"Exchanging code for token (nonce={'present' if session.auth_server_nonce else 'none'})"
        )

        # Create DPoP proof for token request (using nonce from PAR)
        dpop_proof = create_dpop_proof(
            http_method="POST",
            http_url=token_endpoint,
            keypair=session.dpop_keypair,
            nonce=session.auth_server_nonce,
        )

        headers = {
            "DPoP": dpop_proof.serialize(),
            "Content-Type": "application/x-www-form-urlencoded",
        }

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self._redirect_uri,
            "client_id": self._client_id,
            "code_verifier": session.pkce_verifier,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(token_endpoint, headers=headers, data=data)

            logger.debug(f"Token exchange response status: {response.status_code}")

            # Log error details before raising
            if response.status_code >= 400:
                try:
                    error_body = response.json()
                    logger.error(
                        f"Token exchange failed (status {response.status_code}): {error_body}"
                    )
                except Exception:
                    logger.error(
                        f"Token exchange failed (status {response.status_code}): {response.text}"
                    )

            response.raise_for_status()

            # Validate DPoP-Nonce header is present (required by spec)
            dpop_nonce = response.headers.get("DPoP-Nonce")
            if not dpop_nonce:
                logger.error(
                    "Token response missing required DPoP-Nonce header "
                    f"(headers: {dict(response.headers)})"
                )
                raise BlueskyAuthError(
                    "Token response missing required DPoP-Nonce header"
                )

            # Update session with new nonce for future requests
            session.auth_server_nonce = dpop_nonce
            logger.debug("Updated session with new DPoP nonce")

            result = response.json()

            # Validate required token response fields
            access_token = result.get("access_token")
            if not access_token:
                raise BlueskyAuthError("Missing access_token in token response")

            # Validate scope field is present (required by spec)
            scope = result.get("scope")
            if not scope:
                logger.error(f"Token response missing scope field: {result}")
                raise BlueskyAuthError("Token response missing required scope field")

            # Verify scope includes atproto
            scopes = scope.split()
            if "atproto" not in scopes:
                logger.error(f"Token response scope missing 'atproto': {scope}")
                raise BlueskyAuthError("Token response scope missing 'atproto'")

            # Extract sub (DID) for verification
            sub = result.get("sub")
            if sub and sub != session.account_did:
                raise BlueskyAuthError(
                    f"Token sub mismatch: expected {session.account_did}, got {sub}"
                )

            logger.debug(f"Token exchange successful, scope: {scope}")
            return access_token

    async def _get_user_profile(
        self,
        pds_url: str,
        access_token: str,
        dpop_keypair: DPoPKeyPair,
        pds_nonce: str | None,
    ) -> BlueskyUserInfo:
        """Fetch user profile from PDS.

        Args:
            pds_url: PDS endpoint URL
            access_token: Access token from auth server
            dpop_keypair: DPoP keypair for proof
            pds_nonce: PDS nonce (if available)

        Returns:
            User information

        Raises:
            BlueskyAuthError: If profile fetch fails
        """
        profile_url = f"{pds_url}/xrpc/com.atproto.server.getSession"

        # Create DPoP proof with ath (access token hash)
        dpop_proof = create_dpop_proof(
            http_method="GET",
            http_url=profile_url,
            keypair=dpop_keypair,
            nonce=pds_nonce,
            access_token=access_token,
        )

        headers = {
            "DPoP": dpop_proof.serialize(),
            "Authorization": f"DPoP {access_token}",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(profile_url, headers=headers)

            # Log error details before raising
            if response.status_code >= 400:
                try:
                    error_body = response.json()
                    logger.error(
                        f"Profile fetch failed (status {response.status_code}): {error_body}"
                    )
                except Exception:
                    logger.error(
                        f"Profile fetch failed (status {response.status_code}): {response.text}"
                    )

            response.raise_for_status()

            # Note: DPoP-Nonce validation is optional for PDS requests
            # The PDS may or may not return a nonce depending on its configuration
            if "DPoP-Nonce" in response.headers:
                logger.debug("PDS returned DPoP-Nonce header")

            result = response.json()

            # Extract user info from response
            return BlueskyUserInfo(
                did=result.get("did", ""),
                handle=result.get("handle", ""),
                display_name=result.get("displayName"),
                avatar_url=result.get("avatar"),
            )


# Mock implementation for testing
class MockBlueskyAuthClient:
    """Mock Bluesky authentication client for development."""

    async def initiate_authorization(self, account_identifier: str) -> str:
        """Get mock authorization URL."""
        return (
            f"https://bsky.app/oauth/authorize?mock=true&account={account_identifier}"
        )

    async def complete_authorization(
        self, code: str, state: str, iss: str
    ) -> BlueskyUserInfo:
        """Complete mock authorization."""
        _ = (state, iss)  # satisfy pyright
        if code == "invalid":
            raise BlueskyAuthError("Invalid authorization code")

        return BlueskyUserInfo(
            did="did:plc:mock123",
            handle="user.bsky.social",
            display_name="Test User",
            avatar_url="https://example.com/avatar.jpg",
        )
