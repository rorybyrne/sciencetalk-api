"""Unit tests for AT Protocol OAuth client."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from talk.adapter.bluesky.auth import (
    ATProtocolOAuthClient,
    BlueskyAuthError,
    BlueskyUserInfo,
)
from talk.adapter.bluesky.dpop import DPoPKeyPair
from talk.adapter.bluesky.session import InMemorySessionStore, OAuthSession
from talk.domain.value.types import BlueskyDID


class TestATProtocolOAuthClient:
    """Tests for ATProtocolOAuthClient."""

    @pytest.fixture
    def session_store(self):
        """Create in-memory session store."""
        return InMemorySessionStore()

    @pytest.fixture
    def oauth_client(self, session_store):
        """Create OAuth client with test configuration."""
        return ATProtocolOAuthClient(
            client_id="https://talk.example.com/.well-known/oauth-client-metadata",
            redirect_uri="https://talk.example.com/auth/callback",
            session_store=session_store,
        )

    @pytest.fixture
    def mock_session(self):
        """Create mock OAuth session."""
        return OAuthSession(
            state="test_state_123",
            pkce_verifier="test_verifier",
            pkce_challenge="test_challenge",
            dpop_keypair=DPoPKeyPair(),
            account_did="did:plc:abc123",
            auth_server_issuer="https://bsky.social",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        )


class TestInitiateAuthorization(TestATProtocolOAuthClient):
    """Tests for initiate_authorization method."""

    @pytest.mark.asyncio
    async def test_resolves_handle_and_initiates_flow(self, oauth_client):
        """Should resolve handle to DID and initiate OAuth flow."""
        # Mock all external calls
        with (
            patch(
                "talk.adapter.bluesky.auth.resolve_handle_to_did"
            ) as mock_resolve_handle,
            patch("talk.adapter.bluesky.auth.resolve_did_document") as mock_resolve_did,
            patch("talk.adapter.bluesky.auth.get_pds_endpoint") as mock_get_pds,
            patch(
                "talk.adapter.bluesky.auth.discover_auth_server"
            ) as mock_discover_auth,
        ):
            # Setup mocks
            mock_resolve_handle.return_value = BlueskyDID("did:plc:abc123")

            mock_did_doc = MagicMock()
            mock_resolve_did.return_value = mock_did_doc

            mock_get_pds.return_value = "https://bsky.social"

            mock_auth_metadata = MagicMock()
            mock_auth_metadata.pushed_authorization_request_endpoint = (
                "https://bsky.social/oauth/par"
            )
            mock_auth_metadata.authorization_endpoint = (
                "https://bsky.social/oauth/authorize"
            )
            mock_auth_metadata.issuer = "https://bsky.social"
            mock_discover_auth.return_value = mock_auth_metadata

            # Mock PAR request
            with patch.object(
                oauth_client, "_make_par_request", new_callable=AsyncMock
            ) as mock_par:
                mock_par.return_value = (
                    "urn:ietf:params:oauth:request_uri:abc123",
                    "test_nonce",
                )

                # Execute
                auth_url = await oauth_client.initiate_authorization(
                    "alice.bsky.social"
                )

                # Verify handle resolution
                mock_resolve_handle.assert_called_once_with("alice.bsky.social")

                # Verify DID document resolution
                mock_resolve_did.assert_called_once()

                # Verify PDS endpoint extraction
                mock_get_pds.assert_called_once_with(mock_did_doc)

                # Verify auth server discovery
                mock_discover_auth.assert_called_once_with("https://bsky.social")

                # Verify PAR request was made
                mock_par.assert_called_once()

                # Verify authorization URL format
                assert "https://bsky.social/oauth/authorize" in auth_url
                assert "client_id=" in auth_url
                assert "request_uri=" in auth_url

    @pytest.mark.asyncio
    async def test_accepts_did_directly(self, oauth_client):
        """Should accept DID without handle resolution."""
        with (
            patch("talk.adapter.bluesky.auth.resolve_did_document") as mock_resolve_did,
            patch("talk.adapter.bluesky.auth.get_pds_endpoint") as mock_get_pds,
            patch(
                "talk.adapter.bluesky.auth.discover_auth_server"
            ) as mock_discover_auth,
        ):
            mock_did_doc = MagicMock()
            mock_resolve_did.return_value = mock_did_doc
            mock_get_pds.return_value = "https://bsky.social"

            mock_auth_metadata = MagicMock()
            mock_auth_metadata.pushed_authorization_request_endpoint = (
                "https://bsky.social/oauth/par"
            )
            mock_auth_metadata.authorization_endpoint = (
                "https://bsky.social/oauth/authorize"
            )
            mock_auth_metadata.issuer = "https://bsky.social"
            mock_discover_auth.return_value = mock_auth_metadata

            with patch.object(
                oauth_client, "_make_par_request", new_callable=AsyncMock
            ) as mock_par:
                mock_par.return_value = (
                    "urn:ietf:params:oauth:request_uri:abc123",
                    "test_nonce",
                )

                await oauth_client.initiate_authorization("did:plc:abc123")

                # Should resolve DID document directly
                mock_resolve_did.assert_called_once()
                called_did = mock_resolve_did.call_args[0][0]
                assert str(called_did) == "did:plc:abc123"

    @pytest.mark.asyncio
    async def test_saves_session_state(self, oauth_client, session_store):
        """Should save OAuth session with all necessary state."""
        with (
            patch(
                "talk.adapter.bluesky.auth.resolve_handle_to_did"
            ) as mock_resolve_handle,
            patch("talk.adapter.bluesky.auth.resolve_did_document") as mock_resolve_did,
            patch("talk.adapter.bluesky.auth.get_pds_endpoint") as mock_get_pds,
            patch(
                "talk.adapter.bluesky.auth.discover_auth_server"
            ) as mock_discover_auth,
        ):
            mock_resolve_handle.return_value = BlueskyDID("did:plc:abc123")
            mock_did_doc = MagicMock()
            mock_resolve_did.return_value = mock_did_doc
            mock_get_pds.return_value = "https://bsky.social"

            mock_auth_metadata = MagicMock()
            mock_auth_metadata.pushed_authorization_request_endpoint = (
                "https://bsky.social/oauth/par"
            )
            mock_auth_metadata.authorization_endpoint = (
                "https://bsky.social/oauth/authorize"
            )
            mock_auth_metadata.issuer = "https://bsky.social"
            mock_discover_auth.return_value = mock_auth_metadata

            with patch.object(
                oauth_client, "_make_par_request", new_callable=AsyncMock
            ) as mock_par:
                mock_par.return_value = (
                    "urn:ietf:params:oauth:request_uri:abc123",
                    "test_nonce",
                )

                await oauth_client.initiate_authorization("alice.bsky.social")

                # Verify session was saved
                # Extract state from URL (simple approach - in real tests we'd mock better)
                sessions = session_store._sessions
                assert len(sessions) == 1

                # Get the saved session
                session = list(sessions.values())[0]
                assert session.account_did == "did:plc:abc123"
                assert session.auth_server_issuer == "https://bsky.social"
                assert session.pkce_verifier
                assert session.pkce_challenge
                assert session.dpop_keypair


class TestCompleteAuthorization(TestATProtocolOAuthClient):
    """Tests for complete_authorization method."""

    @pytest.mark.asyncio
    async def test_completes_flow_successfully(
        self, oauth_client, session_store, mock_session
    ):
        """Should complete OAuth flow and return user info."""
        # Save session
        await session_store.save(mock_session.state, mock_session)

        with (
            patch(
                "talk.adapter.bluesky.auth.discover_auth_server"
            ) as mock_discover_auth,
            patch("talk.adapter.bluesky.auth.resolve_did_document") as mock_resolve_did,
            patch("talk.adapter.bluesky.auth.get_pds_endpoint") as mock_get_pds,
        ):
            # Mock auth server discovery
            mock_auth_metadata = MagicMock()
            mock_auth_metadata.token_endpoint = "https://bsky.social/oauth/token"
            mock_discover_auth.return_value = mock_auth_metadata

            # Mock DID document resolution
            mock_did_doc = MagicMock()
            mock_resolve_did.return_value = mock_did_doc
            mock_get_pds.return_value = "https://bsky.social"

            # Mock internal methods
            with (
                patch.object(
                    oauth_client,
                    "_exchange_code_for_token",
                    new_callable=AsyncMock,
                ) as mock_exchange,
                patch.object(
                    oauth_client, "_get_user_profile", new_callable=AsyncMock
                ) as mock_get_profile,
            ):
                mock_exchange.return_value = ("mock_access_token", "did:plc:abc123")
                mock_get_profile.return_value = BlueskyUserInfo(
                    did="did:plc:abc123",
                    handle="alice.bsky.social",
                    display_name="Alice",
                    avatar_url="https://example.com/avatar.jpg",
                )

                # Execute
                user_info = await oauth_client.complete_authorization(
                    code="auth_code_123",
                    state=mock_session.state,
                    iss="https://bsky.social",
                )

                # Verify result
                assert user_info.did == "did:plc:abc123"
                assert user_info.handle == "alice.bsky.social"
                assert user_info.display_name == "Alice"

                # Verify token exchange was called
                mock_exchange.assert_called_once()

                # Verify profile fetch was called
                mock_get_profile.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_on_invalid_session(self, oauth_client):
        """Should raise error for invalid or expired session."""
        with pytest.raises(BlueskyAuthError, match="Invalid or expired OAuth session"):
            await oauth_client.complete_authorization(
                code="auth_code_123",
                state="invalid_state",
                iss="https://bsky.social",
            )

    @pytest.mark.asyncio
    async def test_raises_on_issuer_mismatch(
        self, oauth_client, session_store, mock_session
    ):
        """Should raise error if issuer doesn't match session."""
        await session_store.save(mock_session.state, mock_session)

        with pytest.raises(BlueskyAuthError, match="Issuer mismatch"):
            await oauth_client.complete_authorization(
                code="auth_code_123",
                state=mock_session.state,
                iss="https://different-server.com",
            )

    @pytest.mark.asyncio
    async def test_raises_on_did_mismatch(
        self, oauth_client, session_store, mock_session
    ):
        """Should raise error if returned DID doesn't match expected."""
        await session_store.save(mock_session.state, mock_session)

        with (
            patch(
                "talk.adapter.bluesky.auth.discover_auth_server"
            ) as mock_discover_auth,
            patch("talk.adapter.bluesky.auth.resolve_did_document") as mock_resolve_did,
            patch("talk.adapter.bluesky.auth.get_pds_endpoint") as mock_get_pds,
        ):
            mock_auth_metadata = MagicMock()
            mock_auth_metadata.token_endpoint = "https://bsky.social/oauth/token"
            mock_discover_auth.return_value = mock_auth_metadata

            mock_did_doc = MagicMock()
            mock_resolve_did.return_value = mock_did_doc
            mock_get_pds.return_value = "https://bsky.social"

            with (
                patch.object(
                    oauth_client,
                    "_exchange_code_for_token",
                    new_callable=AsyncMock,
                ) as mock_exchange,
                patch.object(
                    oauth_client, "_get_user_profile", new_callable=AsyncMock
                ) as mock_get_profile,
            ):
                mock_exchange.return_value = ("mock_access_token", "did:plc:abc123")
                # Return different DID than expected
                mock_get_profile.return_value = BlueskyUserInfo(
                    did="did:plc:different",
                    handle="different.bsky.social",
                )

                with pytest.raises(BlueskyAuthError, match="DID mismatch"):
                    await oauth_client.complete_authorization(
                        code="auth_code_123",
                        state=mock_session.state,
                        iss="https://bsky.social",
                    )

    @pytest.mark.asyncio
    async def test_deletes_session_after_completion(
        self, oauth_client, session_store, mock_session
    ):
        """Should delete session after successful completion."""
        await session_store.save(mock_session.state, mock_session)

        with (
            patch(
                "talk.adapter.bluesky.auth.discover_auth_server"
            ) as mock_discover_auth,
            patch("talk.adapter.bluesky.auth.resolve_did_document") as mock_resolve_did,
            patch("talk.adapter.bluesky.auth.get_pds_endpoint") as mock_get_pds,
        ):
            mock_auth_metadata = MagicMock()
            mock_auth_metadata.token_endpoint = "https://bsky.social/oauth/token"
            mock_discover_auth.return_value = mock_auth_metadata

            mock_did_doc = MagicMock()
            mock_resolve_did.return_value = mock_did_doc
            mock_get_pds.return_value = "https://bsky.social"

            with (
                patch.object(
                    oauth_client,
                    "_exchange_code_for_token",
                    new_callable=AsyncMock,
                ) as mock_exchange,
                patch.object(
                    oauth_client, "_get_user_profile", new_callable=AsyncMock
                ) as mock_get_profile,
            ):
                mock_exchange.return_value = ("mock_access_token", "did:plc:abc123")
                mock_get_profile.return_value = BlueskyUserInfo(
                    did="did:plc:abc123",
                    handle="alice.bsky.social",
                )

                await oauth_client.complete_authorization(
                    code="auth_code_123",
                    state=mock_session.state,
                    iss="https://bsky.social",
                )

                # Verify session was deleted
                retrieved_session = await session_store.get(mock_session.state)
                assert retrieved_session is None


class TestMakePARRequest(TestATProtocolOAuthClient):
    """Tests for _make_par_request method."""

    @pytest.mark.asyncio
    async def test_makes_par_request_successfully(self, oauth_client):
        """Should make PAR request and return request_uri."""
        dpop_keypair = DPoPKeyPair()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(
            return_value={"request_uri": "urn:ietf:params:oauth:request_uri:abc123"}
        )
        mock_response.headers = {"DPoP-Nonce": "test_nonce"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            request_uri, dpop_nonce = await oauth_client._make_par_request(
                par_endpoint="https://bsky.social/oauth/par",
                pkce_challenge="test_challenge",
                dpop_keypair=dpop_keypair,
                login_hint="did:plc:abc123",
                state="test_state",
            )

            assert request_uri == "urn:ietf:params:oauth:request_uri:abc123"
            assert dpop_nonce == "test_nonce"

    @pytest.mark.asyncio
    async def test_retries_with_dpop_nonce(self, oauth_client):
        """Should retry PAR request with DPoP nonce on 401."""
        dpop_keypair = DPoPKeyPair()

        # First response: 401 with nonce
        mock_response_401 = MagicMock()
        mock_response_401.status_code = 401
        mock_response_401.json = MagicMock(return_value={"error": "use_dpop_nonce"})
        mock_response_401.headers = {"DPoP-Nonce": "server_nonce_123"}

        # Second response: success
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.json = MagicMock(
            return_value={"request_uri": "urn:ietf:params:oauth:request_uri:abc123"}
        )
        mock_response_200.headers = {"DPoP-Nonce": "server_nonce_123"}
        mock_response_200.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            # First call returns 401, second returns 200
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=[mock_response_401, mock_response_200]
            )

            request_uri, dpop_nonce = await oauth_client._make_par_request(
                par_endpoint="https://bsky.social/oauth/par",
                pkce_challenge="test_challenge",
                dpop_keypair=dpop_keypair,
                login_hint="did:plc:abc123",
                state="test_state",
            )

            # Should succeed on retry
            assert request_uri == "urn:ietf:params:oauth:request_uri:abc123"
            assert dpop_nonce == "server_nonce_123"

            # Verify two calls were made
            assert mock_client.return_value.__aenter__.return_value.post.call_count == 2

    @pytest.mark.asyncio
    async def test_raises_on_missing_request_uri(self, oauth_client):
        """Should raise error if response missing request_uri."""
        dpop_keypair = DPoPKeyPair()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={})  # Missing request_uri
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            with pytest.raises(BlueskyAuthError, match="Missing request_uri"):
                await oauth_client._make_par_request(
                    par_endpoint="https://bsky.social/oauth/par",
                    pkce_challenge="test_challenge",
                    dpop_keypair=dpop_keypair,
                    login_hint="did:plc:abc123",
                    state="test_state",
                )


class TestExchangeCodeForToken(TestATProtocolOAuthClient):
    """Tests for _exchange_code_for_token method."""

    @pytest.mark.asyncio
    async def test_exchanges_code_for_token(self, oauth_client, mock_session):
        """Should exchange authorization code for access token."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"DPoP-Nonce": "test_nonce_123"}
        mock_response.json = MagicMock(
            return_value={
                "access_token": "access_token_123",
                "token_type": "DPoP",
                "scope": "atproto",
                "sub": "did:plc:abc123",
            }
        )
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            access_token, token_sub = await oauth_client._exchange_code_for_token(
                token_endpoint="https://bsky.social/oauth/token",
                code="auth_code_123",
                session=mock_session,
            )

            assert access_token == "access_token_123"
            assert token_sub == "did:plc:abc123"

    @pytest.mark.asyncio
    async def test_verifies_token_sub_matches_session_did(
        self, oauth_client, mock_session
    ):
        """Should verify token sub matches expected DID."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"DPoP-Nonce": "test_nonce_123"}
        mock_response.json = MagicMock(
            return_value={
                "access_token": "access_token_123",
                "scope": "atproto",
                "sub": "did:plc:different",  # Different from session
            }
        )
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            with pytest.raises(BlueskyAuthError, match="Token sub mismatch"):
                await oauth_client._exchange_code_for_token(
                    token_endpoint="https://bsky.social/oauth/token",
                    code="auth_code_123",
                    session=mock_session,
                )

    @pytest.mark.asyncio
    async def test_raises_on_missing_access_token(self, oauth_client, mock_session):
        """Should raise error if response missing access_token."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"DPoP-Nonce": "test_nonce_123"}
        mock_response.json = MagicMock(
            return_value={"scope": "atproto"}
        )  # Missing access_token
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            with pytest.raises(BlueskyAuthError, match="Missing access_token"):
                await oauth_client._exchange_code_for_token(
                    token_endpoint="https://bsky.social/oauth/token",
                    code="auth_code_123",
                    session=mock_session,
                )


class TestGetUserProfile(TestATProtocolOAuthClient):
    """Tests for _get_user_profile method."""

    @pytest.mark.asyncio
    async def test_fetches_user_profile(self, oauth_client):
        """Should fetch user profile from PDS."""
        dpop_keypair = DPoPKeyPair()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(
            return_value={
                "did": "did:plc:abc123",
                "handle": "alice.bsky.social",
                "displayName": "Alice",
                "avatar": "https://example.com/avatar.jpg",
            }
        )
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            user_info = await oauth_client._get_user_profile(
                pds_url="https://bsky.social",
                access_token="access_token_123",
                dpop_keypair=dpop_keypair,
                pds_nonce=None,
            )

            assert user_info.did == "did:plc:abc123"
            assert user_info.handle == "alice.bsky.social"
            assert user_info.display_name == "Alice"
            assert user_info.avatar_url == "https://example.com/avatar.jpg"

    @pytest.mark.asyncio
    async def test_handles_missing_optional_fields(self, oauth_client):
        """Should handle missing display name and avatar."""
        dpop_keypair = DPoPKeyPair()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(
            return_value={
                "did": "did:plc:abc123",
                "handle": "alice.bsky.social",
                # displayName and avatar missing
            }
        )
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            user_info = await oauth_client._get_user_profile(
                pds_url="https://bsky.social",
                access_token="access_token_123",
                dpop_keypair=dpop_keypair,
                pds_nonce=None,
            )

            assert user_info.did == "did:plc:abc123"
            assert user_info.handle == "alice.bsky.social"
            assert user_info.display_name is None
            assert user_info.avatar_url is None
