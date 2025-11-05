"""Integration tests for InviteRepository.

These tests verify that the repository correctly handles value objects
when interacting with the database.
"""

from datetime import datetime
from uuid import uuid4

import pytest

from talk.domain.model.invite import Invite
from talk.domain.repository import InviteRepository
from talk.domain.value import AuthProvider, InviteId, InviteStatus, InviteToken, UserId
from tests.harness import create_env_fixture

# Integration test fixture
integration_env = create_env_fixture()


class TestInviteRepositoryIntegration:
    """Integration tests for PostgresInviteRepository.

    These tests verify database interaction and value object handling.
    """

    @pytest.mark.asyncio
    async def test_find_by_token_extracts_root_value(self, integration_env):
        """Regression test: find_by_token must extract .root from InviteToken.

        This test ensures that the repository correctly extracts the string value
        from the InviteToken value object before querying the database.

        Previously, this caused a TypeError:
        "expected str, got InviteToken"
        """
        # Arrange
        invite_repo = await integration_env.get(InviteRepository)

        # Create an invite with a known token
        token_value = "test-token-12345"
        invite_token = InviteToken(root=token_value)

        invite = Invite(
            id=InviteId(uuid4()),
            inviter_id=UserId(uuid4()),
            provider=AuthProvider.BLUESKY,
            invitee_handle="test.bsky.social",
            invitee_provider_id="did:plc:test123",
            invitee_name="Test User",
            invite_token=invite_token,
            status=InviteStatus.PENDING,
            created_at=datetime.now(),
            accepted_at=None,
            accepted_by_user_id=None,
        )

        # Save the invite
        await invite_repo.save(invite)

        # Act - Query by token (this should extract .root internally)
        found_invite = await invite_repo.find_by_token(invite_token)

        # Assert
        assert found_invite is not None
        assert found_invite.id == invite.id
        assert found_invite.invite_token.root == token_value
        assert found_invite.invitee_handle == "test.bsky.social"

    @pytest.mark.asyncio
    async def test_find_by_token_returns_none_for_nonexistent_token(
        self, integration_env
    ):
        """Verify find_by_token returns None for non-existent tokens."""
        # Arrange
        invite_repo = await integration_env.get(InviteRepository)
        nonexistent_token = InviteToken(root="nonexistent-token")

        # Act
        result = await invite_repo.find_by_token(nonexistent_token)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_save_and_retrieve_invite_with_token(self, integration_env):
        """Verify complete save/retrieve cycle preserves token value."""
        # Arrange
        invite_repo = await integration_env.get(InviteRepository)

        original_token = InviteToken(root="complete-cycle-token")
        invite = Invite(
            id=InviteId(uuid4()),
            inviter_id=UserId(uuid4()),
            provider=AuthProvider.BLUESKY,
            invitee_handle="saveretrieve.bsky.social",
            invitee_provider_id="did:plc:saveretrieve",
            invitee_name=None,
            invite_token=original_token,
            status=InviteStatus.PENDING,
            created_at=datetime.now(),
            accepted_at=None,
            accepted_by_user_id=None,
        )

        # Act
        saved_invite = await invite_repo.save(invite)
        retrieved_invite = await invite_repo.find_by_token(original_token)

        # Assert
        assert retrieved_invite is not None
        assert retrieved_invite.id == saved_invite.id
        assert retrieved_invite.invite_token.root == original_token.root
        assert isinstance(retrieved_invite.invite_token, InviteToken)
