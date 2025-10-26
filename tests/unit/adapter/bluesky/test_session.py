"""Unit tests for OAuth session state management."""

from datetime import datetime, timedelta, timezone

import pytest

from talk.adapter.bluesky.dpop import DPoPKeyPair
from talk.adapter.bluesky.session import InMemorySessionStore, OAuthSession


class TestOAuthSession:
    """Tests for OAuthSession dataclass."""

    def test_creates_session_with_required_fields(self):
        """Should create session with all required fields."""
        keypair = DPoPKeyPair()
        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=15)

        session = OAuthSession(
            state="test-state-123",
            pkce_verifier="test-verifier",
            pkce_challenge="test-challenge",
            dpop_keypair=keypair,
            account_did="did:plc:test123",
            auth_server_issuer="https://bsky.social",
            created_at=now,
            expires_at=expires,
        )

        assert session.state == "test-state-123"
        assert session.pkce_verifier == "test-verifier"
        assert session.pkce_challenge == "test-challenge"
        assert session.dpop_keypair == keypair
        assert session.account_did == "did:plc:test123"
        assert session.auth_server_issuer == "https://bsky.social"
        assert session.created_at == now
        assert session.expires_at == expires

    def test_optional_nonces_default_to_none(self):
        """Optional nonce fields should default to None."""
        keypair = DPoPKeyPair()
        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=15)

        session = OAuthSession(
            state="test-state",
            pkce_verifier="verifier",
            pkce_challenge="challenge",
            dpop_keypair=keypair,
            account_did="did:plc:test",
            auth_server_issuer="https://bsky.social",
            created_at=now,
            expires_at=expires,
        )

        assert session.auth_server_nonce is None
        assert session.pds_nonce is None

    def test_can_set_nonces(self):
        """Should be able to set nonce values."""
        keypair = DPoPKeyPair()
        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=15)

        session = OAuthSession(
            state="test-state",
            pkce_verifier="verifier",
            pkce_challenge="challenge",
            dpop_keypair=keypair,
            account_did="did:plc:test",
            auth_server_issuer="https://bsky.social",
            auth_server_nonce="auth-nonce-123",
            pds_nonce="pds-nonce-456",
            created_at=now,
            expires_at=expires,
        )

        assert session.auth_server_nonce == "auth-nonce-123"
        assert session.pds_nonce == "pds-nonce-456"


class TestInMemorySessionStore:
    """Tests for InMemorySessionStore class."""

    @pytest.mark.asyncio
    async def test_save_and_get_session(self):
        """Should save and retrieve session by state."""
        store = InMemorySessionStore()
        keypair = DPoPKeyPair()
        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=15)

        session = OAuthSession(
            state="state-123",
            pkce_verifier="verifier",
            pkce_challenge="challenge",
            dpop_keypair=keypair,
            account_did="did:plc:test",
            auth_server_issuer="https://bsky.social",
            created_at=now,
            expires_at=expires,
        )

        # Save session
        await store.save("state-123", session)

        # Retrieve session
        retrieved = await store.get("state-123")

        assert retrieved is not None
        assert retrieved.state == "state-123"
        assert retrieved.pkce_verifier == "verifier"
        assert retrieved.pkce_challenge == "challenge"
        assert retrieved.account_did == "did:plc:test"

    @pytest.mark.asyncio
    async def test_get_nonexistent_session_returns_none(self):
        """Should return None for non-existent state."""
        store = InMemorySessionStore()

        result = await store.get("nonexistent-state")

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_session(self):
        """Should delete session by state."""
        store = InMemorySessionStore()
        keypair = DPoPKeyPair()
        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=15)

        session = OAuthSession(
            state="state-to-delete",
            pkce_verifier="verifier",
            pkce_challenge="challenge",
            dpop_keypair=keypair,
            account_did="did:plc:test",
            auth_server_issuer="https://bsky.social",
            created_at=now,
            expires_at=expires,
        )

        # Save and verify
        await store.save("state-to-delete", session)
        assert await store.get("state-to-delete") is not None

        # Delete
        await store.delete("state-to-delete")

        # Should be gone
        assert await store.get("state-to-delete") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_session_does_not_error(self):
        """Should not error when deleting non-existent session."""
        store = InMemorySessionStore()

        # Should not raise
        await store.delete("nonexistent-state")

    @pytest.mark.asyncio
    async def test_get_expired_session_returns_none(self):
        """Should return None for expired session."""
        store = InMemorySessionStore()
        keypair = DPoPKeyPair()
        now = datetime.now(timezone.utc)
        # Create already-expired session
        expired = now - timedelta(minutes=1)

        session = OAuthSession(
            state="expired-state",
            pkce_verifier="verifier",
            pkce_challenge="challenge",
            dpop_keypair=keypair,
            account_did="did:plc:test",
            auth_server_issuer="https://bsky.social",
            created_at=now - timedelta(minutes=16),
            expires_at=expired,
        )

        # Save session
        await store.save("expired-state", session)

        # Try to retrieve - should return None
        result = await store.get("expired-state")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_expired_session_deletes_it(self):
        """Should delete expired session when attempting to retrieve."""
        store = InMemorySessionStore()
        keypair = DPoPKeyPair()
        now = datetime.now(timezone.utc)
        expired = now - timedelta(minutes=1)

        session = OAuthSession(
            state="expired-state",
            pkce_verifier="verifier",
            pkce_challenge="challenge",
            dpop_keypair=keypair,
            account_did="did:plc:test",
            auth_server_issuer="https://bsky.social",
            created_at=now - timedelta(minutes=16),
            expires_at=expired,
        )

        # Save session
        await store.save("expired-state", session)

        # Try to retrieve - triggers cleanup
        await store.get("expired-state")

        # Session should be deleted from internal storage
        assert "expired-state" not in store._sessions

    @pytest.mark.asyncio
    async def test_stores_multiple_sessions(self):
        """Should store and retrieve multiple sessions."""
        store = InMemorySessionStore()
        keypair1 = DPoPKeyPair()
        keypair2 = DPoPKeyPair()
        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=15)

        session1 = OAuthSession(
            state="state-1",
            pkce_verifier="verifier-1",
            pkce_challenge="challenge-1",
            dpop_keypair=keypair1,
            account_did="did:plc:test1",
            auth_server_issuer="https://bsky.social",
            created_at=now,
            expires_at=expires,
        )

        session2 = OAuthSession(
            state="state-2",
            pkce_verifier="verifier-2",
            pkce_challenge="challenge-2",
            dpop_keypair=keypair2,
            account_did="did:plc:test2",
            auth_server_issuer="https://bsky.social",
            created_at=now,
            expires_at=expires,
        )

        # Save both
        await store.save("state-1", session1)
        await store.save("state-2", session2)

        # Retrieve both
        retrieved1 = await store.get("state-1")
        retrieved2 = await store.get("state-2")

        assert retrieved1 is not None
        assert retrieved2 is not None
        assert retrieved1.pkce_verifier == "verifier-1"
        assert retrieved2.pkce_verifier == "verifier-2"
