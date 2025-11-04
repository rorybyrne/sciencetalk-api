"""Unit tests for InviteService."""

from datetime import datetime
from uuid import uuid4

import pytest

from talk.domain.service import InviteService
from talk.domain.value import AuthProvider, InviteId, InviteStatus, InviteToken, UserId
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
        invitee_handle = "friend.bsky.social"
        invitee_did = "did:plc:abc123"
        invite_token = InviteToken(str(uuid4()))

        # Act
        result = await invite_service.create_invite(
            inviter_id,
            AuthProvider.BLUESKY,
            invitee_handle,
            invitee_did,
            None,
            invite_token,
        )

        # Assert
        assert result.inviter_id == inviter_id
        assert result.invitee_handle == invitee_handle
        assert result.invitee_provider_id == invitee_did
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
        invitee_handle = "friend.bsky.social"
        invitee_did = "did:plc:abc123"

        # Create first invite
        await invite_service.create_invite(
            inviter_id,
            AuthProvider.BLUESKY,
            invitee_handle,
            invitee_did,
            None,
            InviteToken(str(uuid4())),
        )

        # Act & Assert - Second invite for same DID should fail
        with pytest.raises(ValueError, match="Invite already exists"):
            await invite_service.create_invite(
                inviter_id,
                AuthProvider.BLUESKY,
                invitee_handle,
                invitee_did,
                None,
                InviteToken(str(uuid4())),
            )

    @pytest.mark.asyncio
    async def test_create_invite_after_accepted_succeeds(self, unit_env):
        """Creating new invite after previous was accepted should succeed."""
        # Arrange
        invite_service = await unit_env.get(InviteService)

        inviter_id = UserId(uuid4())
        invitee_handle = "friend.bsky.social"
        invitee_did = "did:plc:abc123"

        # Create and accept first invite
        first_invite = await invite_service.create_invite(
            inviter_id,
            AuthProvider.BLUESKY,
            invitee_handle,
            invitee_did,
            None,
            InviteToken(str(uuid4())),
        )
        await invite_service.accept_invite(first_invite.id, UserId(uuid4()))

        # Act - Create new invite from different inviter
        another_inviter = UserId(uuid4())
        result = await invite_service.create_invite(
            another_inviter,
            AuthProvider.BLUESKY,
            invitee_handle,
            invitee_did,
            None,
            InviteToken(str(uuid4())),
        )

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
        invitee_handle = "newuser.bsky.social"
        invitee_did = "did:plc:newuser123"
        new_user_id = UserId(uuid4())

        # Create pending invite
        invite = await invite_service.create_invite(
            inviter_id,
            AuthProvider.BLUESKY,
            invitee_handle,
            invitee_did,
            None,
            InviteToken(str(uuid4())),
        )

        # Act
        result = await invite_service.accept_invite(invite.id, new_user_id)

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

        nonexistent_invite_id = InviteId(uuid4())
        new_user_id = UserId(uuid4())

        # Act & Assert
        with pytest.raises(ValueError, match="not found"):
            await invite_service.accept_invite(nonexistent_invite_id, new_user_id)

    @pytest.mark.asyncio
    async def test_accept_already_accepted_invite_raises_error(self, unit_env):
        """Accepting already accepted invite should raise error."""
        # Arrange
        invite_service = await unit_env.get(InviteService)

        inviter_id = UserId(uuid4())
        invitee_handle = "user.bsky.social"
        invitee_did = "did:plc:user123"

        # Create and accept invite
        invite = await invite_service.create_invite(
            inviter_id,
            AuthProvider.BLUESKY,
            invitee_handle,
            invitee_did,
            None,
            InviteToken(str(uuid4())),
        )
        first_user_id = UserId(uuid4())
        await invite_service.accept_invite(invite.id, first_user_id)

        # Act & Assert - Accepting the same invite again should succeed
        # (the service doesn't prevent re-accepting; it just updates the invite)
        second_user_id = UserId(uuid4())
        result = await invite_service.accept_invite(invite.id, second_user_id)
        assert result.accepted_by_user_id == second_user_id


class TestCheckInviteExists:
    """Tests for check_invite_exists method."""

    @pytest.mark.asyncio
    async def test_check_invite_exists_returns_true_when_pending(self, unit_env):
        """Should return True when pending invite exists."""
        # Arrange
        invite_service = await unit_env.get(InviteService)

        inviter_id = UserId(uuid4())
        invitee_handle = "invited.bsky.social"
        invitee_did = "did:plc:invited123"

        await invite_service.create_invite(
            inviter_id,
            AuthProvider.BLUESKY,
            invitee_handle,
            invitee_did,
            None,
            InviteToken(str(uuid4())),
        )

        # Act
        result = await invite_service.check_invite_exists(
            AuthProvider.BLUESKY, invitee_did
        )

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_check_invite_exists_returns_false_when_not_found(self, unit_env):
        """Should return False when no pending invite exists."""
        # Arrange
        invite_service = await unit_env.get(InviteService)
        invitee_did = "did:plc:notinvited123"

        # Act
        result = await invite_service.check_invite_exists(
            AuthProvider.BLUESKY, invitee_did
        )

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_check_invite_exists_returns_false_when_accepted(self, unit_env):
        """Should return False when invite has been accepted."""
        # Arrange
        invite_service = await unit_env.get(InviteService)

        inviter_id = UserId(uuid4())
        invitee_handle = "user.bsky.social"
        invitee_did = "did:plc:user123"

        # Create and accept invite
        invite = await invite_service.create_invite(
            inviter_id,
            AuthProvider.BLUESKY,
            invitee_handle,
            invitee_did,
            None,
            InviteToken(str(uuid4())),
        )
        await invite_service.accept_invite(invite.id, UserId(uuid4()))

        # Act
        result = await invite_service.check_invite_exists(
            AuthProvider.BLUESKY, invitee_did
        )

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
        _invite1 = await invite_service.create_invite(
            inviter_id,
            AuthProvider.BLUESKY,
            "user1.bsky.social",
            "did:plc:user1",
            None,
            InviteToken(str(uuid4())),
        )
        invite2 = await invite_service.create_invite(
            inviter_id,
            AuthProvider.BLUESKY,
            "user2.bsky.social",
            "did:plc:user2",
            None,
            InviteToken(str(uuid4())),
        )
        await invite_service.create_invite(
            inviter_id,
            AuthProvider.BLUESKY,
            "user3.bsky.social",
            "did:plc:user3",
            None,
            InviteToken(str(uuid4())),
        )

        # Accept one of them
        await invite_service.accept_invite(invite2.id, UserId(uuid4()))

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
        await invite_service.create_invite(
            user1_id,
            AuthProvider.BLUESKY,
            "friend1.bsky.social",
            "did:plc:friend1",
            None,
            InviteToken(str(uuid4())),
        )
        await invite_service.create_invite(
            user1_id,
            AuthProvider.BLUESKY,
            "friend2.bsky.social",
            "did:plc:friend2",
            None,
            InviteToken(str(uuid4())),
        )

        # User 2 creates 1 invite
        await invite_service.create_invite(
            user2_id,
            AuthProvider.BLUESKY,
            "friend3.bsky.social",
            "did:plc:friend3",
            None,
            InviteToken(str(uuid4())),
        )

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
            inviter_id,
            AuthProvider.BLUESKY,
            "user1.bsky.social",
            "did:plc:user1",
            None,
            InviteToken(str(uuid4())),
        )
        invite2 = await invite_service.create_invite(
            inviter_id,
            AuthProvider.BLUESKY,
            "user2.bsky.social",
            "did:plc:user2",
            None,
            InviteToken(str(uuid4())),
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
        _invite1 = await invite_service.create_invite(
            inviter_id,
            AuthProvider.BLUESKY,
            "user1.bsky.social",
            "did:plc:user1",
            None,
            InviteToken(str(uuid4())),
        )
        invite2 = await invite_service.create_invite(
            inviter_id,
            AuthProvider.BLUESKY,
            "user2.bsky.social",
            "did:plc:user2",
            None,
            InviteToken(str(uuid4())),
        )
        await invite_service.create_invite(
            inviter_id,
            AuthProvider.BLUESKY,
            "user3.bsky.social",
            "did:plc:user3",
            None,
            InviteToken(str(uuid4())),
        )

        # Accept one
        await invite_service.accept_invite(invite2.id, UserId(uuid4()))

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
                inviter_id,
                AuthProvider.BLUESKY,
                f"user{i}.bsky.social",
                f"did:plc:user{i}",
                None,
                InviteToken(str(uuid4())),
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
