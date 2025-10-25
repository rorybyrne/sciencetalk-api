"""Unit tests for InviteService."""

from datetime import datetime
from uuid import uuid4

import pytest

from talk.domain.service import InviteService
from talk.domain.value import InviteStatus, UserId
from talk.domain.value.types import Handle
from talk.persistence.repository.invite import InviteRepository
from tests.harness import create_env_fixture

# Unit test fixture - everything mocked, no docker needed
unit_env = create_env_fixture()


class TestCreateInvite:
    """Tests for create_invite method."""

    @pytest.mark.asyncio
    async def test_create_invite_success(self, unit_env):
        """Creating an invite should save it with pending status."""
        # Arrange
        invite_service = await unit_env.get(InviteService)
        invite_repo = await unit_env.get(InviteRepository)

        inviter_id = UserId(uuid4())
        invitee_handle = Handle(root="friend.bsky.social")

        # Act
        result = await invite_service.create_invite(inviter_id, invitee_handle)

        # Assert
        assert result.inviter_id == inviter_id
        assert result.invitee_handle == invitee_handle
        assert result.status == InviteStatus.PENDING
        assert result.accepted_at is None
        assert result.accepted_by_user_id is None

        # Verify it was saved
        saved_invite = await invite_repo.find_by_id(result.id)
        assert saved_invite is not None
        assert saved_invite.id == result.id

    @pytest.mark.asyncio
    async def test_create_invite_duplicate_raises_error(self, unit_env):
        """Creating duplicate pending invite should raise error."""
        # Arrange
        invite_service = await unit_env.get(InviteService)

        inviter_id = UserId(uuid4())
        invitee_handle = Handle(root="friend.bsky.social")

        # Create first invite
        await invite_service.create_invite(inviter_id, invitee_handle)

        # Act & Assert - Second invite for same handle should fail
        with pytest.raises(ValueError, match="Invite already exists"):
            await invite_service.create_invite(inviter_id, invitee_handle)

    @pytest.mark.asyncio
    async def test_create_invite_after_accepted_succeeds(self, unit_env):
        """Creating new invite after previous was accepted should succeed."""
        # Arrange
        invite_service = await unit_env.get(InviteService)

        inviter_id = UserId(uuid4())
        invitee_handle = Handle(root="friend.bsky.social")

        # Create and accept first invite
        await invite_service.create_invite(inviter_id, invitee_handle)
        await invite_service.accept_invite(invitee_handle, UserId(uuid4()))

        # Act - Create new invite from different inviter
        another_inviter = UserId(uuid4())
        result = await invite_service.create_invite(another_inviter, invitee_handle)

        # Assert - Should succeed because previous invite is no longer pending
        assert result.inviter_id == another_inviter
        assert result.status == InviteStatus.PENDING


class TestAcceptInvite:
    """Tests for accept_invite method."""

    @pytest.mark.asyncio
    async def test_accept_invite_success(self, unit_env):
        """Accepting an invite should update status and link to new user."""
        # Arrange
        invite_service = await unit_env.get(InviteService)
        invite_repo = await unit_env.get(InviteRepository)

        inviter_id = UserId(uuid4())
        invitee_handle = Handle(root="newuser.bsky.social")
        new_user_id = UserId(uuid4())

        # Create pending invite
        invite = await invite_service.create_invite(inviter_id, invitee_handle)

        # Act
        result = await invite_service.accept_invite(invitee_handle, new_user_id)

        # Assert
        assert result.id == invite.id
        assert result.status == InviteStatus.ACCEPTED
        assert result.accepted_by_user_id == new_user_id
        assert result.accepted_at is not None
        assert isinstance(result.accepted_at, datetime)

        # Verify it was saved
        saved_invite = await invite_repo.find_by_id(invite.id)
        assert saved_invite.status == InviteStatus.ACCEPTED
        assert saved_invite.accepted_by_user_id == new_user_id

    @pytest.mark.asyncio
    async def test_accept_invite_not_found_raises_error(self, unit_env):
        """Accepting non-existent invite should raise error."""
        # Arrange
        invite_service = await unit_env.get(InviteService)

        invitee_handle = Handle(root="nobody.bsky.social")
        new_user_id = UserId(uuid4())

        # Act & Assert
        with pytest.raises(ValueError, match="No pending invite found"):
            await invite_service.accept_invite(invitee_handle, new_user_id)

    @pytest.mark.asyncio
    async def test_accept_already_accepted_invite_raises_error(self, unit_env):
        """Accepting already accepted invite should raise error."""
        # Arrange
        invite_service = await unit_env.get(InviteService)

        inviter_id = UserId(uuid4())
        invitee_handle = Handle(root="user.bsky.social")

        # Create and accept invite
        await invite_service.create_invite(inviter_id, invitee_handle)
        first_user_id = UserId(uuid4())
        await invite_service.accept_invite(invitee_handle, first_user_id)

        # Act & Assert - Try to accept again
        with pytest.raises(ValueError, match="No pending invite found"):
            await invite_service.accept_invite(invitee_handle, UserId(uuid4()))


class TestCheckInviteExists:
    """Tests for check_invite_exists method."""

    @pytest.mark.asyncio
    async def test_check_invite_exists_returns_true_when_pending(self, unit_env):
        """Should return True when pending invite exists."""
        # Arrange
        invite_service = await unit_env.get(InviteService)

        inviter_id = UserId(uuid4())
        invitee_handle = Handle(root="invited.bsky.social")

        await invite_service.create_invite(inviter_id, invitee_handle)

        # Act
        result = await invite_service.check_invite_exists(invitee_handle)

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_check_invite_exists_returns_false_when_not_found(self, unit_env):
        """Should return False when no pending invite exists."""
        # Arrange
        invite_service = await unit_env.get(InviteService)
        invitee_handle = Handle(root="notinvited.bsky.social")

        # Act
        result = await invite_service.check_invite_exists(invitee_handle)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_check_invite_exists_returns_false_when_accepted(self, unit_env):
        """Should return False when invite has been accepted."""
        # Arrange
        invite_service = await unit_env.get(InviteService)

        inviter_id = UserId(uuid4())
        invitee_handle = Handle(root="user.bsky.social")

        # Create and accept invite
        await invite_service.create_invite(inviter_id, invitee_handle)
        await invite_service.accept_invite(invitee_handle, UserId(uuid4()))

        # Act
        result = await invite_service.check_invite_exists(invitee_handle)

        # Assert
        assert result is False  # No PENDING invite


class TestGetPendingCount:
    """Tests for get_pending_count method."""

    @pytest.mark.asyncio
    async def test_get_pending_count_returns_zero_when_none(self, unit_env):
        """Should return 0 when user has no pending invites."""
        # Arrange
        invite_service = await unit_env.get(InviteService)
        inviter_id = UserId(uuid4())

        # Act
        count = await invite_service.get_pending_count(inviter_id)

        # Assert
        assert count == 0

    @pytest.mark.asyncio
    async def test_get_pending_count_counts_only_pending(self, unit_env):
        """Should count only pending invites, not accepted ones."""
        # Arrange
        invite_service = await unit_env.get(InviteService)
        inviter_id = UserId(uuid4())

        # Create 3 invites
        await invite_service.create_invite(inviter_id, Handle(root="user1.bsky.social"))
        await invite_service.create_invite(inviter_id, Handle(root="user2.bsky.social"))
        await invite_service.create_invite(inviter_id, Handle(root="user3.bsky.social"))

        # Accept one of them
        await invite_service.accept_invite(
            Handle(root="user2.bsky.social"), UserId(uuid4())
        )

        # Act
        count = await invite_service.get_pending_count(inviter_id)

        # Assert
        assert count == 2  # Only 2 still pending

    @pytest.mark.asyncio
    async def test_get_pending_count_per_user(self, unit_env):
        """Should count pending invites per user separately."""
        # Arrange
        invite_service = await unit_env.get(InviteService)
        user1_id = UserId(uuid4())
        user2_id = UserId(uuid4())

        # User 1 creates 2 invites
        await invite_service.create_invite(user1_id, Handle(root="friend1.bsky.social"))
        await invite_service.create_invite(user1_id, Handle(root="friend2.bsky.social"))

        # User 2 creates 1 invite
        await invite_service.create_invite(user2_id, Handle(root="friend3.bsky.social"))

        # Act
        user1_count = await invite_service.get_pending_count(user1_id)
        user2_count = await invite_service.get_pending_count(user2_id)

        # Assert
        assert user1_count == 2
        assert user2_count == 1


class TestListInvites:
    """Tests for list_invites method."""

    @pytest.mark.asyncio
    async def test_list_invites_returns_all_invites(self, unit_env):
        """Should return all invites for a user."""
        # Arrange
        invite_service = await unit_env.get(InviteService)
        inviter_id = UserId(uuid4())

        # Create invites
        invite1 = await invite_service.create_invite(
            inviter_id, Handle(root="user1.bsky.social")
        )
        invite2 = await invite_service.create_invite(
            inviter_id, Handle(root="user2.bsky.social")
        )

        # Act
        invites = await invite_service.list_invites(inviter_id)

        # Assert
        assert len(invites) == 2
        invite_ids = {inv.id for inv in invites}
        assert invite1.id in invite_ids
        assert invite2.id in invite_ids

    @pytest.mark.asyncio
    async def test_list_invites_filters_by_status(self, unit_env):
        """Should filter invites by status."""
        # Arrange
        invite_service = await unit_env.get(InviteService)
        inviter_id = UserId(uuid4())

        # Create invites
        await invite_service.create_invite(inviter_id, Handle(root="user1.bsky.social"))
        await invite_service.create_invite(inviter_id, Handle(root="user2.bsky.social"))
        await invite_service.create_invite(inviter_id, Handle(root="user3.bsky.social"))

        # Accept one
        await invite_service.accept_invite(
            Handle(root="user2.bsky.social"), UserId(uuid4())
        )

        # Act - Get only pending
        pending = await invite_service.list_invites(
            inviter_id, status=InviteStatus.PENDING
        )
        accepted = await invite_service.list_invites(
            inviter_id, status=InviteStatus.ACCEPTED
        )

        # Assert
        assert len(pending) == 2
        assert len(accepted) == 1
        assert all(inv.status == InviteStatus.PENDING for inv in pending)
        assert all(inv.status == InviteStatus.ACCEPTED for inv in accepted)

    @pytest.mark.asyncio
    async def test_list_invites_respects_pagination(self, unit_env):
        """Should respect limit and offset for pagination."""
        # Arrange
        invite_service = await unit_env.get(InviteService)
        inviter_id = UserId(uuid4())

        # Create 5 invites
        for i in range(5):
            await invite_service.create_invite(
                inviter_id, Handle(root=f"user{i}.bsky.social")
            )

        # Act
        page1 = await invite_service.list_invites(inviter_id, limit=2, offset=0)
        page2 = await invite_service.list_invites(inviter_id, limit=2, offset=2)

        # Assert
        assert len(page1) == 2
        assert len(page2) == 2
        # Should be different invites
        page1_ids = {inv.id for inv in page1}
        page2_ids = {inv.id for inv in page2}
        assert page1_ids.isdisjoint(page2_ids)
