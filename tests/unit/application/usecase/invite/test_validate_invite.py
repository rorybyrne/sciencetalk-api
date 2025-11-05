"""Tests for validate invite use case."""

from uuid import uuid4

import pytest

from talk.application.usecase.invite.validate_invite import (
    ValidateInviteRequest,
    ValidateInviteUseCase,
)
from talk.domain.model import User
from talk.domain.service import InviteService, UserService
from talk.domain.value import AuthProvider, InviteStatus, InviteToken, UserId
from talk.domain.value.types import Handle
from tests.harness import create_env_fixture

# Unit test fixture
unit_env = create_env_fixture()


class TestValidateInviteUseCase:
    """Tests for ValidateInviteUseCase."""

    @pytest.mark.asyncio
    async def test_validate_valid_pending_invite(self, unit_env):
        """Test validating a valid pending invite."""
        # Arrange
        invite_service = await unit_env.get(InviteService)
        user_service = await unit_env.get(UserService)
        use_case = ValidateInviteUseCase(invite_service, user_service)

        # Create inviter user
        inviter_id = UserId(uuid4())
        inviter = User(
            id=inviter_id,
            handle=Handle("inviter.bsky.social"),
        )
        await user_service.save(inviter)

        # Create a pending invite
        token = InviteToken(root="test-token-123")
        await invite_service.create_invite(
            inviter_id=inviter_id,
            provider=AuthProvider.BLUESKY,
            invitee_handle="alice.bsky.social",
            invitee_provider_id="did:plc:alice123",
            invitee_name="Alice",
            invite_token=token,
        )

        # Act
        request = ValidateInviteRequest(token="test-token-123")
        response = await use_case.execute(request)

        # Assert
        assert response.valid is True
        assert response.status == InviteStatus.PENDING
        assert response.provider == AuthProvider.BLUESKY
        assert response.invitee_handle == "alice.bsky.social"
        assert response.invitee_name == "Alice"
        assert response.inviter_handle == "inviter.bsky.social"
        assert response.message == "Valid invite"

    @pytest.mark.asyncio
    async def test_validate_nonexistent_invite(self, unit_env):
        """Test validating a nonexistent invite."""
        # Arrange
        invite_service = await unit_env.get(InviteService)
        user_service = await unit_env.get(UserService)
        use_case = ValidateInviteUseCase(invite_service, user_service)

        # Act
        request = ValidateInviteRequest(token="nonexistent-token")
        response = await use_case.execute(request)

        # Assert
        assert response.valid is False
        assert response.status is None
        assert response.provider is None
        assert response.message == "Invite not found"

    @pytest.mark.asyncio
    async def test_validate_accepted_invite(self, unit_env):
        """Test validating an already accepted invite."""
        # Arrange
        invite_service = await unit_env.get(InviteService)
        user_service = await unit_env.get(UserService)
        use_case = ValidateInviteUseCase(invite_service, user_service)

        # Create and accept an invite
        token = InviteToken(root="accepted-token-123")
        invite = await invite_service.create_invite(
            inviter_id=UserId(uuid4()),
            provider=AuthProvider.BLUESKY,
            invitee_handle="bob.bsky.social",
            invitee_provider_id="did:plc:bob123",
            invitee_name="Bob",
            invite_token=token,
        )
        await invite_service.accept_invite(invite.id, UserId(uuid4()))

        # Act
        request = ValidateInviteRequest(token="accepted-token-123")
        response = await use_case.execute(request)

        # Assert
        assert response.valid is False
        assert response.status == InviteStatus.ACCEPTED
        assert response.message == "Invite has already been accepted"
