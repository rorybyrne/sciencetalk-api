"""Unit tests for CreateInvitesUseCase."""

from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

import pytest

from talk.application.usecase.invite import CreateInvitesUseCase
from talk.application.usecase.invite.create_invites import CreateInvitesRequest
from talk.config import InvitationSettings, Settings
from talk.domain.model.user import User
from talk.domain.repository import UserRepository
from talk.domain.service import UserService
from talk.domain.service import InviteService
from talk.domain.value import UserId
from talk.domain.value.types import BlueskyDID, Handle
from tests.harness import create_env_fixture

# Unit test fixture
unit_env = create_env_fixture()


# Mock DID resolver to return deterministic DIDs based on handle
def mock_resolve_handle_to_did(handle: str) -> BlueskyDID:
    """Mock that returns deterministic DIDs for testing."""
    # Create a deterministic DID based on the handle
    handle_hash = hash(handle) % 1000000
    return BlueskyDID(f"did:plc:test{handle_hash:06d}")


class TestCreateInvitesUseCase:
    """Tests for CreateInvitesUseCase."""

    async def _create_test_user(
        self, user_repo: UserRepository, handle: str, invite_quota: int = 5
    ) -> User:
        """Helper to create a test user."""
        user = User(
            id=UserId(uuid4()),
            bluesky_did=BlueskyDID(root=f"did:plc:{uuid4()}"),
            handle=Handle(root=handle),
            display_name="Test User",
            avatar_url=None,
            karma=0,
            invite_quota=invite_quota,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        return await user_repo.save(user)

    @pytest.mark.asyncio
    @patch(
        "talk.application.usecase.invite.create_invites.resolve_handle_to_did",
        side_effect=mock_resolve_handle_to_did,
    )
    async def test_create_invites_success(self, mock_resolve, unit_env):
        """Should create multiple invites when quota available."""
        # Arrange
        user_repo = await unit_env.get(UserRepository)
        user_service = await unit_env.get(UserService)
        invite_service = await unit_env.get(InviteService)
        settings = await unit_env.get(Settings)

        user = await self._create_test_user(user_repo, "inviter.bsky.social")

        use_case = CreateInvitesUseCase(invite_service, user_service, settings)

        request = CreateInvitesRequest(
            inviter_id=str(user.id),
            inviter_handle=str(user.handle),
            invitee_handles=["friend1.bsky.social", "friend2.bsky.social"],
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert len(response.invites) == 2
        assert response.failed_handles == []

        # Verify invites were created
        pending_count = await invite_service.get_pending_count(user.id)
        assert pending_count == 2

    @pytest.mark.asyncio
    @patch(
        "talk.application.usecase.invite.create_invites.resolve_handle_to_did",
        side_effect=mock_resolve_handle_to_did,
    )
    async def test_create_invites_exceeds_quota_raises_error(
        self, mock_resolve, unit_env
    ):
        """Should raise error when requested invites exceed available quota."""
        # Arrange
        user_repo = await unit_env.get(UserRepository)
        user_service = await unit_env.get(UserService)
        invite_service = await unit_env.get(InviteService)
        settings = await unit_env.get(Settings)

        # Create user with quota of 5
        user = await self._create_test_user(
            user_repo, "inviter.bsky.social", invite_quota=5
        )

        # Use up 3 of the quota
        await invite_service.create_invite(
            user.id, Handle(root="used1.bsky.social"), BlueskyDID("did:plc:used1")
        )
        await invite_service.create_invite(
            user.id, Handle(root="used2.bsky.social"), BlueskyDID("did:plc:used2")
        )
        await invite_service.create_invite(
            user.id, Handle(root="used3.bsky.social"), BlueskyDID("did:plc:used3")
        )

        use_case = CreateInvitesUseCase(invite_service, user_service, settings)

        # Try to create 3 more (only 2 available)
        request = CreateInvitesRequest(
            inviter_id=str(user.id),
            inviter_handle=str(user.handle),
            invitee_handles=[
                "new1.bsky.social",
                "new2.bsky.social",
                "new3.bsky.social",
            ],
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Insufficient invite quota"):
            await use_case.execute(request)

    @pytest.mark.asyncio
    @patch(
        "talk.application.usecase.invite.create_invites.resolve_handle_to_did",
        side_effect=mock_resolve_handle_to_did,
    )
    async def test_create_invites_with_unlimited_inviter_bypasses_quota(
        self, mock_resolve, unit_env
    ):
        """Unlimited inviters should bypass quota restrictions."""
        # Arrange
        user_repo = await unit_env.get(UserRepository)
        user_service = await unit_env.get(UserService)
        invite_service = await unit_env.get(InviteService)
        settings = await unit_env.get(Settings)

        handle = Handle(root="admin.bsky.social")
        # Create user with quota of 5
        user = await self._create_test_user(user_repo, handle.root, invite_quota=5)

        # Use up all quota
        for i in range(5):
            await invite_service.create_invite(
                user.id,
                Handle(root=f"used{i}.bsky.social"),
                BlueskyDID(f"did:plc:used{i}"),
            )

        # Configure unlimited inviters
        settings.invitations = InvitationSettings(unlimited_inviters=[handle])
        use_case = CreateInvitesUseCase(invite_service, user_service, settings)

        # Try to create more invites (should succeed despite quota exhausted)
        request = CreateInvitesRequest(
            inviter_id=str(user.id),
            inviter_handle=str(user.handle),
            invitee_handles=["bonus1.bsky.social", "bonus2.bsky.social"],
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert len(response.invites) == 2
        assert response.failed_handles == []

        # Verify we now have 7 pending invites (5 + 2)
        pending_count = await invite_service.get_pending_count(user.id)
        assert pending_count == 7

    @pytest.mark.asyncio
    @patch(
        "talk.application.usecase.invite.create_invites.resolve_handle_to_did",
        side_effect=mock_resolve_handle_to_did,
    )
    async def test_create_invites_handles_duplicates_gracefully(
        self, mock_resolve, unit_env
    ):
        """Should track failed handles when duplicates exist."""
        # Arrange
        user_repo = await unit_env.get(UserRepository)
        user_service = await unit_env.get(UserService)
        invite_service = await unit_env.get(InviteService)
        settings = await unit_env.get(Settings)

        user = await self._create_test_user(user_repo, "inviter.bsky.social")

        # Create an existing invite with the deterministic DID
        existing_did = mock_resolve_handle_to_did("existing.bsky.social")
        await invite_service.create_invite(
            user.id, Handle(root="existing.bsky.social"), existing_did
        )

        use_case = CreateInvitesUseCase(invite_service, user_service, settings)

        request = CreateInvitesRequest(
            inviter_id=str(user.id),
            inviter_handle=str(user.handle),
            invitee_handles=[
                "new.bsky.social",
                "existing.bsky.social",  # Duplicate
                "another.bsky.social",
            ],
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert (
            len(response.invites) == 2
        )  # Only new.bsky.social and another.bsky.social
        assert "existing.bsky.social" in response.failed_handles

    @pytest.mark.asyncio
    async def test_create_invites_batch_limit_enforced(self, unit_env):
        """Should enforce maximum batch size of 10 invites via Pydantic validation."""
        # Arrange
        from pydantic import ValidationError

        user_repo = await unit_env.get(UserRepository)
        user = await self._create_test_user(
            user_repo, "inviter.bsky.social", invite_quota=20
        )

        # Act & Assert - Pydantic validates max 10 at request level
        with pytest.raises(ValidationError):
            CreateInvitesRequest(
                inviter_id=str(user.id),
                inviter_handle=str(user.handle),
                invitee_handles=[f"user{i}.bsky.social" for i in range(11)],
            )

    @pytest.mark.asyncio
    async def test_create_invites_with_nonexistent_user_raises_error(self, unit_env):
        """Should raise error when inviter user not found."""
        # Arrange
        user_service = await unit_env.get(UserService)
        invite_service = await unit_env.get(InviteService)
        settings = await unit_env.get(Settings)

        use_case = CreateInvitesUseCase(invite_service, user_service, settings)

        # Use non-existent user ID
        request = CreateInvitesRequest(
            inviter_id=str(uuid4()),
            inviter_handle="nonexistent.bsky.social",
            invitee_handles=["friend.bsky.social"],
        )

        # Act & Assert
        with pytest.raises(ValueError, match="User not found"):
            await use_case.execute(request)

    @pytest.mark.asyncio
    @patch(
        "talk.application.usecase.invite.create_invites.resolve_handle_to_did",
        side_effect=mock_resolve_handle_to_did,
    )
    async def test_create_invites_zero_available_quota(self, mock_resolve, unit_env):
        """Should raise error when user has zero available quota."""
        # Arrange
        user_repo = await unit_env.get(UserRepository)
        user_service = await unit_env.get(UserService)
        invite_service = await unit_env.get(InviteService)
        settings = await unit_env.get(Settings)

        # Create user with quota of 2
        user = await self._create_test_user(
            user_repo, "inviter.bsky.social", invite_quota=2
        )

        # Use up all quota
        await invite_service.create_invite(
            user.id, Handle(root="used1.bsky.social"), BlueskyDID("did:plc:used1")
        )
        await invite_service.create_invite(
            user.id, Handle(root="used2.bsky.social"), BlueskyDID("did:plc:used2")
        )

        use_case = CreateInvitesUseCase(invite_service, user_service, settings)

        request = CreateInvitesRequest(
            inviter_id=str(user.id),
            inviter_handle=str(user.handle),
            invitee_handles=["new.bsky.social"],
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Insufficient invite quota.*Available: 0"):
            await use_case.execute(request)

    @pytest.mark.asyncio
    @patch(
        "talk.application.usecase.invite.create_invites.resolve_handle_to_did",
        side_effect=mock_resolve_handle_to_did,
    )
    async def test_create_invites_partial_quota_success(self, mock_resolve, unit_env):
        """Should succeed when creating invites within available quota."""
        # Arrange
        user_repo = await unit_env.get(UserRepository)
        user_service = await unit_env.get(UserService)
        invite_service = await unit_env.get(InviteService)
        settings = await unit_env.get(Settings)

        # Create user with quota of 5
        user = await self._create_test_user(
            user_repo, "inviter.bsky.social", invite_quota=5
        )

        # Use up 3 of the quota
        await invite_service.create_invite(
            user.id, Handle(root="used1.bsky.social"), BlueskyDID("did:plc:used1")
        )
        await invite_service.create_invite(
            user.id, Handle(root="used2.bsky.social"), BlueskyDID("did:plc:used2")
        )
        await invite_service.create_invite(
            user.id, Handle(root="used3.bsky.social"), BlueskyDID("did:plc:used3")
        )

        use_case = CreateInvitesUseCase(invite_service, user_service, settings)

        # Create exactly 2 more (uses all remaining quota)
        request = CreateInvitesRequest(
            inviter_id=str(user.id),
            inviter_handle=str(user.handle),
            invitee_handles=["new1.bsky.social", "new2.bsky.social"],
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert len(response.invites) == 2
        assert response.failed_handles == []

        # Verify quota is now fully used
        pending_count = await invite_service.get_pending_count(user.id)
        assert pending_count == 5  # All quota used
