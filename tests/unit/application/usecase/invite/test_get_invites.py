"""Unit tests for GetInvitesUseCase."""

from datetime import datetime
from uuid import uuid4

import pytest

from talk.application.usecase.invite import GetInvitesUseCase
from talk.application.usecase.invite.get_invites import GetInvitesRequest
from talk.config import Settings
from talk.domain.model.invite import Invite
from talk.domain.model.user import User
from talk.domain.repository import UserRepository
from talk.domain.service import InviteService, UserService
from talk.domain.value import AuthProvider, InviteStatus, InviteToken, UserId
from talk.domain.value.types import Handle
from tests.harness import create_env_fixture

# Unit test fixture
unit_env = create_env_fixture()


class TestGetInvitesUseCase:
    """Tests for GetInvitesUseCase."""

    async def _create_test_user(self, user_repo: UserRepository, handle: str) -> User:
        """Helper to create a test user."""
        user = User(
            id=UserId(uuid4()),
            handle=Handle(handle),
            avatar_url=None,
            email=None,
            bio=None,
            karma=0,
            invite_quota=5,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        return await user_repo.save(user)

    async def _create_invite(
        self,
        invite_service: InviteService,
        inviter_id: UserId,
        invitee_handle: str,
        invitee_did: str = "did:plc:default",
    ) -> Invite:
        """Helper to create an invite."""
        # Generate unique token for each invite
        token = InviteToken(f"token-{uuid4()}")
        return await invite_service.create_invite(
            inviter_id,
            AuthProvider.BLUESKY,
            invitee_handle,
            invitee_did,
            None,
            token,
        )

    @pytest.mark.asyncio
    async def test_get_invites_empty_list(self, unit_env):
        """Should return empty list when user has no invites."""
        # Arrange
        user_repo = await unit_env.get(UserRepository)
        user_service = await unit_env.get(UserService)
        invite_service = await unit_env.get(InviteService)

        user = await self._create_test_user(user_repo, "inviter.bsky.social")
        settings = await unit_env.get(Settings)
        use_case = GetInvitesUseCase(invite_service, user_service, settings)

        request = GetInvitesRequest(inviter_id=str(user.id))

        # Act
        response = await use_case.execute(request)

        # Assert
        assert len(response.invites) == 0
        assert response.total == 0
        assert response.remaining_quota == 5  # Default quota

    @pytest.mark.asyncio
    async def test_get_invites_returns_all_invites(self, unit_env):
        """Should return all invites created by user."""
        # Arrange
        user_repo = await unit_env.get(UserRepository)
        user_service = await unit_env.get(UserService)
        invite_service = await unit_env.get(InviteService)

        user = await self._create_test_user(user_repo, "inviter.bsky.social")

        # Create some invites
        await self._create_invite(
            invite_service, user.id, "friend1.bsky.social", "did:plc:friend1"
        )
        await self._create_invite(
            invite_service, user.id, "friend2.bsky.social", "did:plc:friend2"
        )
        await self._create_invite(
            invite_service, user.id, "friend3.bsky.social", "did:plc:friend3"
        )

        settings = await unit_env.get(Settings)
        use_case = GetInvitesUseCase(invite_service, user_service, settings)
        request = GetInvitesRequest(inviter_id=str(user.id))

        # Act
        response = await use_case.execute(request)

        # Assert
        assert len(response.invites) == 3
        assert response.total == 3

        # Verify all invites are present
        handles = {invite.invitee_handle for invite in response.invites}
        assert handles == {
            "friend1.bsky.social",
            "friend2.bsky.social",
            "friend3.bsky.social",
        }

    @pytest.mark.asyncio
    async def test_get_invites_filter_by_pending_status(self, unit_env):
        """Should return only pending invites when status filter is pending."""
        # Arrange
        user_repo = await unit_env.get(UserRepository)
        user_service = await unit_env.get(UserService)
        invite_service = await unit_env.get(InviteService)

        user = await self._create_test_user(user_repo, "inviter.bsky.social")

        # Create pending invites
        await self._create_invite(
            invite_service, user.id, "pending1.bsky.social", "did:plc:pending1"
        )
        await self._create_invite(
            invite_service, user.id, "pending2.bsky.social", "did:plc:pending2"
        )

        # Create an accepted invite
        accepted_invite = await self._create_invite(
            invite_service, user.id, "accepted.bsky.social", "did:plc:accepted"
        )
        # Create a new user to accept the invite
        new_user = await self._create_test_user(user_repo, "accepted.bsky.social")
        await invite_service.accept_invite(accepted_invite.id, new_user.id)

        settings = await unit_env.get(Settings)
        use_case = GetInvitesUseCase(invite_service, user_service, settings)
        request = GetInvitesRequest(
            inviter_id=str(user.id),
            status=InviteStatus.PENDING,
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert len(response.invites) == 2
        assert all(invite.status == InviteStatus.PENDING for invite in response.invites)

        handles = {invite.invitee_handle for invite in response.invites}
        assert handles == {"pending1.bsky.social", "pending2.bsky.social"}

    @pytest.mark.asyncio
    async def test_get_invites_filter_by_accepted_status(self, unit_env):
        """Should return only accepted invites when status filter is accepted."""
        # Arrange
        user_repo = await unit_env.get(UserRepository)
        user_service = await unit_env.get(UserService)
        invite_service = await unit_env.get(InviteService)

        user = await self._create_test_user(user_repo, "inviter.bsky.social")

        # Create pending invite
        await self._create_invite(
            invite_service, user.id, "pending.bsky.social", "did:plc:pending"
        )

        # Create accepted invites
        invite1 = await self._create_invite(
            invite_service, user.id, "accepted1.bsky.social", "did:plc:accepted1"
        )
        invite2 = await self._create_invite(
            invite_service, user.id, "accepted2.bsky.social", "did:plc:accepted2"
        )

        # Accept the invites
        for handle, invite in [
            ("accepted1.bsky.social", invite1),
            ("accepted2.bsky.social", invite2),
        ]:
            new_user = await self._create_test_user(user_repo, handle)
            await invite_service.accept_invite(invite.id, new_user.id)

        settings = await unit_env.get(Settings)
        use_case = GetInvitesUseCase(invite_service, user_service, settings)
        request = GetInvitesRequest(
            inviter_id=str(user.id),
            status=InviteStatus.ACCEPTED,
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert len(response.invites) == 2
        assert all(
            invite.status == InviteStatus.ACCEPTED for invite in response.invites
        )
        assert all(invite.accepted_at is not None for invite in response.invites)

        handles = {invite.invitee_handle for invite in response.invites}
        assert handles == {"accepted1.bsky.social", "accepted2.bsky.social"}

    @pytest.mark.asyncio
    async def test_get_invites_pagination_limit(self, unit_env):
        """Should respect limit parameter for pagination."""
        # Arrange
        user_repo = await unit_env.get(UserRepository)
        user_service = await unit_env.get(UserService)
        invite_service = await unit_env.get(InviteService)

        user = await self._create_test_user(user_repo, "inviter.bsky.social")

        # Create 10 invites
        for i in range(10):
            await self._create_invite(
                invite_service, user.id, f"friend{i}.bsky.social", f"did:plc:friend{i}"
            )

        settings = await unit_env.get(Settings)
        use_case = GetInvitesUseCase(invite_service, user_service, settings)
        request = GetInvitesRequest(inviter_id=str(user.id), limit=5)

        # Act
        response = await use_case.execute(request)

        # Assert
        assert len(response.invites) == 5
        assert response.total == 5  # Total matches returned count

    @pytest.mark.asyncio
    async def test_get_invites_pagination_offset(self, unit_env):
        """Should respect offset parameter for pagination."""
        # Arrange
        user_repo = await unit_env.get(UserRepository)
        user_service = await unit_env.get(UserService)
        invite_service = await unit_env.get(InviteService)

        user = await self._create_test_user(user_repo, "inviter.bsky.social")

        # Create invites with predictable handles
        for i in range(10):
            await self._create_invite(
                invite_service,
                user.id,
                f"friend{i:02d}.bsky.social",
                f"did:plc:friend{i:02d}",
            )

        settings = await unit_env.get(Settings)
        use_case = GetInvitesUseCase(invite_service, user_service, settings)

        # Get first page
        request_page1 = GetInvitesRequest(inviter_id=str(user.id), limit=5, offset=0)
        response_page1 = await use_case.execute(request_page1)

        # Get second page
        request_page2 = GetInvitesRequest(inviter_id=str(user.id), limit=5, offset=5)
        response_page2 = await use_case.execute(request_page2)

        # Assert
        assert len(response_page1.invites) == 5
        assert len(response_page2.invites) == 5

        # Verify no overlap between pages
        handles_page1 = {invite.invitee_handle for invite in response_page1.invites}
        handles_page2 = {invite.invitee_handle for invite in response_page2.invites}
        assert len(handles_page1.intersection(handles_page2)) == 0

    @pytest.mark.asyncio
    async def test_get_invites_includes_all_fields(self, unit_env):
        """Should include all required fields in response."""
        # Arrange
        user_repo = await unit_env.get(UserRepository)
        user_service = await unit_env.get(UserService)
        invite_service = await unit_env.get(InviteService)

        user = await self._create_test_user(user_repo, "inviter.bsky.social")

        # Create and accept an invite
        invite = await self._create_invite(
            invite_service, user.id, "friend.bsky.social", "did:plc:friend"
        )
        new_user = await self._create_test_user(user_repo, "friend.bsky.social")
        await invite_service.accept_invite(invite.id, new_user.id)

        settings = await unit_env.get(Settings)
        use_case = GetInvitesUseCase(invite_service, user_service, settings)
        request = GetInvitesRequest(inviter_id=str(user.id))

        # Act
        response = await use_case.execute(request)

        # Assert
        assert len(response.invites) == 1
        invite_item = response.invites[0]

        assert invite_item.invite_id is not None
        assert invite_item.inviter_handle == "inviter.bsky.social"
        assert invite_item.invitee_handle == "friend.bsky.social"
        assert invite_item.status == InviteStatus.ACCEPTED
        assert invite_item.created_at is not None
        assert invite_item.accepted_at is not None

    @pytest.mark.asyncio
    async def test_get_invites_pending_has_null_accepted_at(self, unit_env):
        """Should have null accepted_at for pending invites."""
        # Arrange
        user_repo = await unit_env.get(UserRepository)
        user_service = await unit_env.get(UserService)
        invite_service = await unit_env.get(InviteService)

        user = await self._create_test_user(user_repo, "inviter.bsky.social")
        await self._create_invite(
            invite_service, user.id, "pending.bsky.social", "did:plc:pending"
        )

        settings = await unit_env.get(Settings)
        use_case = GetInvitesUseCase(invite_service, user_service, settings)
        request = GetInvitesRequest(inviter_id=str(user.id))

        # Act
        response = await use_case.execute(request)

        # Assert
        assert len(response.invites) == 1
        invite_item = response.invites[0]

        assert invite_item.status == InviteStatus.PENDING
        assert invite_item.accepted_at is None

    @pytest.mark.asyncio
    async def test_get_invites_with_max_limit(self, unit_env):
        """Should enforce maximum limit of 100."""
        # Arrange
        user_repo = await unit_env.get(UserRepository)

        user = await self._create_test_user(user_repo, "inviter.bsky.social")

        # Test with limit > 100 (should be validated by Pydantic)
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            GetInvitesRequest(inviter_id=str(user.id), limit=101)

    @pytest.mark.asyncio
    async def test_get_invites_isolates_users(self, unit_env):
        """Should only return invites created by specified user."""
        # Arrange
        user_repo = await unit_env.get(UserRepository)
        user_service = await unit_env.get(UserService)
        invite_service = await unit_env.get(InviteService)

        user1 = await self._create_test_user(user_repo, "user1.bsky.social")
        user2 = await self._create_test_user(user_repo, "user2.bsky.social")

        # User 1 creates invites
        await self._create_invite(
            invite_service, user1.id, "user1friend1.bsky.social", "did:plc:user1friend1"
        )
        await self._create_invite(
            invite_service, user1.id, "user1friend2.bsky.social", "did:plc:user1friend2"
        )

        # User 2 creates invites
        await self._create_invite(
            invite_service, user2.id, "user2friend1.bsky.social", "did:plc:user2friend1"
        )

        settings = await unit_env.get(Settings)
        use_case = GetInvitesUseCase(invite_service, user_service, settings)
        request = GetInvitesRequest(inviter_id=str(user1.id))

        # Act
        response = await use_case.execute(request)

        # Assert - should only get user1's invites
        assert len(response.invites) == 2
        handles = {invite.invitee_handle for invite in response.invites}
        assert handles == {"user1friend1.bsky.social", "user1friend2.bsky.social"}
