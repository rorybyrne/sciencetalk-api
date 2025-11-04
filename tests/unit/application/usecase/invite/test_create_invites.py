"""Unit tests for CreateInvitesUseCase."""

from datetime import datetime
from uuid import uuid4

import pytest

from talk.application.usecase.invite import CreateInvitesUseCase
from talk.application.usecase.invite.create_invites import (
    CreateInvitesRequest,
    InviteeInfo,
)
from talk.config import Settings
from talk.domain.model.user import User
from talk.domain.repository import UserRepository
from talk.domain.service import InviteService, UserIdentityService, UserService
from talk.domain.value import AuthProvider, InviteToken, UserId
from talk.domain.value.types import Handle
from tests.harness import create_env_fixture

# Unit test fixture
unit_env = create_env_fixture()


# Mock identity resolver to return deterministic provider IDs based on handle
async def mock_normalize_and_resolve(
    provider: AuthProvider, handle: str
) -> tuple[str, str]:
    """Mock that returns deterministic (handle, provider_id) for testing."""
    if provider == AuthProvider.BLUESKY:
        # Create a deterministic DID based on the handle
        handle_hash = hash(handle) % 1000000
        return (handle, f"did:plc:test{handle_hash:06d}")
    elif provider == AuthProvider.TWITTER:
        # Twitter uses username as provider_id
        return (handle.lower(), handle.lower())
    else:
        raise ValueError(f"Unsupported provider: {provider}")


class TestCreateInvitesUseCase:
    """Tests for CreateInvitesUseCase."""

    async def _create_test_user(
        self, user_repo: UserRepository, handle: str, invite_quota: int = 5
    ) -> User:
        """Helper to create a test user."""
        user = User(
            id=UserId(uuid4()),
            handle=Handle(handle),
            avatar_url=None,
            email=None,
            bio=None,
            karma=0,
            invite_quota=invite_quota,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        return await user_repo.save(user)

    @pytest.mark.asyncio
    async def test_create_invites_success(self, unit_env):
        """Should create multiple invites when quota available."""
        # Arrange
        user_repo = await unit_env.get(UserRepository)
        user_service = await unit_env.get(UserService)
        user_identity_service = await unit_env.get(UserIdentityService)
        invite_service = await unit_env.get(InviteService)
        settings = await unit_env.get(Settings)

        user = await self._create_test_user(user_repo, "inviter.bsky.social")

        use_case = CreateInvitesUseCase(
            invite_service, user_service, user_identity_service, settings
        )

        # Patch the internal _normalize_and_resolve method
        use_case._normalize_and_resolve = mock_normalize_and_resolve

        request = CreateInvitesRequest(
            inviter_id=str(user.id),
            invitees=[
                InviteeInfo(
                    provider=AuthProvider.BLUESKY,
                    handle="friend1.bsky.social",
                    name=None,
                ),
                InviteeInfo(
                    provider=AuthProvider.BLUESKY,
                    handle="friend2.bsky.social",
                    name=None,
                ),
            ],
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert len(response.invites) == 2
        assert response.failed_invitees == []

        # Verify invites were created
        pending_count = await invite_service.get_pending_count(user.id)
        assert pending_count == 2

    @pytest.mark.asyncio
    async def test_create_invites_exceeds_quota_raises_error(self, unit_env):
        """Should raise error when requested invites exceed available quota."""
        # Arrange
        user_repo = await unit_env.get(UserRepository)
        user_service = await unit_env.get(UserService)
        user_identity_service = await unit_env.get(UserIdentityService)
        invite_service = await unit_env.get(InviteService)
        settings = await unit_env.get(Settings)

        # Create user with quota of 5
        user = await self._create_test_user(
            user_repo, "inviter.bsky.social", invite_quota=5
        )

        # Use up 3 of the quota
        await invite_service.create_invite(
            user.id,
            AuthProvider.BLUESKY,
            "used1.bsky.social",
            "did:plc:used1",
            None,
            InviteToken("token1"),
        )
        await invite_service.create_invite(
            user.id,
            AuthProvider.BLUESKY,
            "used2.bsky.social",
            "did:plc:used2",
            None,
            InviteToken("token2"),
        )
        await invite_service.create_invite(
            user.id,
            AuthProvider.BLUESKY,
            "used3.bsky.social",
            "did:plc:used3",
            None,
            InviteToken("token3"),
        )

        use_case = CreateInvitesUseCase(
            invite_service, user_service, user_identity_service, settings
        )

        # Try to create 3 more (only 2 available)
        request = CreateInvitesRequest(
            inviter_id=str(user.id),
            invitees=[
                InviteeInfo(
                    provider=AuthProvider.BLUESKY, handle="new1.bsky.social", name=None
                ),
                InviteeInfo(
                    provider=AuthProvider.BLUESKY, handle="new2.bsky.social", name=None
                ),
                InviteeInfo(
                    provider=AuthProvider.BLUESKY, handle="new3.bsky.social", name=None
                ),
            ],
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Insufficient invite quota"):
            await use_case.execute(request)

    @pytest.mark.asyncio
    async def test_create_invites_with_seed_user_bypasses_quota(self, unit_env):
        """Seed users should bypass quota restrictions (unlimited invites)."""
        # Arrange
        user_repo = await unit_env.get(UserRepository)
        user_service = await unit_env.get(UserService)
        user_identity_service = await unit_env.get(UserIdentityService)
        invite_service = await unit_env.get(InviteService)
        settings = await unit_env.get(Settings)

        # Create seed user with limited quota (should be bypassed)
        user = await self._create_test_user(
            user_repo, "seed.bsky.social", invite_quota=2
        )

        # Configure this user as a seed user
        settings.invitations.seed_users = ["seed.bsky.social"]

        use_case = CreateInvitesUseCase(
            invite_service, user_service, user_identity_service, settings
        )

        # Patch the internal _normalize_and_resolve method
        use_case._normalize_and_resolve = mock_normalize_and_resolve

        # Try to create 5 invites (more than quota of 2)
        request = CreateInvitesRequest(
            inviter_id=str(user.id),
            invitees=[
                InviteeInfo(
                    provider=AuthProvider.BLUESKY,
                    handle=f"friend{i}.bsky.social",
                    name=None,
                )
                for i in range(1, 6)  # 5 invites
            ],
        )

        # Act - Should succeed even though quota is only 2
        response = await use_case.execute(request)

        # Assert
        assert len(response.invites) == 5  # All 5 should succeed
        assert response.failed_invitees == []
        assert response.remaining_quota == 999999  # "Unlimited"

        # Verify invites were created
        pending_count = await invite_service.get_pending_count(user.id)
        assert pending_count == 5

    @pytest.mark.asyncio
    async def test_create_invites_handles_duplicates_gracefully(self, unit_env):
        """Should track failed handles when duplicates exist."""
        # Arrange
        user_repo = await unit_env.get(UserRepository)
        user_service = await unit_env.get(UserService)
        user_identity_service = await unit_env.get(UserIdentityService)
        invite_service = await unit_env.get(InviteService)
        settings = await unit_env.get(Settings)

        user = await self._create_test_user(user_repo, "inviter.bsky.social")

        # Create an existing invite with the deterministic DID
        _, existing_did = await mock_normalize_and_resolve(
            AuthProvider.BLUESKY, "existing.bsky.social"
        )
        await invite_service.create_invite(
            user.id,
            AuthProvider.BLUESKY,
            "existing.bsky.social",
            existing_did,
            None,
            InviteToken("existing-token"),
        )

        use_case = CreateInvitesUseCase(
            invite_service, user_service, user_identity_service, settings
        )
        use_case._normalize_and_resolve = mock_normalize_and_resolve

        request = CreateInvitesRequest(
            inviter_id=str(user.id),
            invitees=[
                InviteeInfo(
                    provider=AuthProvider.BLUESKY, handle="new.bsky.social", name=None
                ),
                InviteeInfo(
                    provider=AuthProvider.BLUESKY,
                    handle="existing.bsky.social",
                    name=None,
                ),  # Duplicate
                InviteeInfo(
                    provider=AuthProvider.BLUESKY,
                    handle="another.bsky.social",
                    name=None,
                ),
            ],
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert (
            len(response.invites) == 2
        )  # Only new.bsky.social and another.bsky.social
        assert (
            f"{AuthProvider.BLUESKY.value}:existing.bsky.social"
            in response.failed_invitees
        )

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
                invitees=[
                    InviteeInfo(
                        provider=AuthProvider.BLUESKY,
                        handle=f"user{i}.bsky.social",
                        name=None,
                    )
                    for i in range(11)
                ],
            )

    @pytest.mark.asyncio
    async def test_create_invites_with_nonexistent_user_raises_error(self, unit_env):
        """Should raise error when inviter user not found."""
        # Arrange
        user_service = await unit_env.get(UserService)
        user_identity_service = await unit_env.get(UserIdentityService)
        invite_service = await unit_env.get(InviteService)
        settings = await unit_env.get(Settings)

        use_case = CreateInvitesUseCase(
            invite_service, user_service, user_identity_service, settings
        )

        # Use non-existent user ID
        request = CreateInvitesRequest(
            inviter_id=str(uuid4()),
            invitees=[
                InviteeInfo(
                    provider=AuthProvider.BLUESKY,
                    handle="friend.bsky.social",
                    name=None,
                )
            ],
        )

        # Act & Assert
        with pytest.raises(ValueError, match="User not found"):
            await use_case.execute(request)

    @pytest.mark.asyncio
    async def test_create_invites_zero_available_quota(self, unit_env):
        """Should raise error when user has zero available quota."""
        # Arrange
        user_repo = await unit_env.get(UserRepository)
        user_service = await unit_env.get(UserService)
        user_identity_service = await unit_env.get(UserIdentityService)
        invite_service = await unit_env.get(InviteService)
        settings = await unit_env.get(Settings)

        # Create user with quota of 2
        user = await self._create_test_user(
            user_repo, "inviter.bsky.social", invite_quota=2
        )

        # Use up all quota
        await invite_service.create_invite(
            user.id,
            AuthProvider.BLUESKY,
            "used1.bsky.social",
            "did:plc:used1",
            None,
            InviteToken("token1"),
        )
        await invite_service.create_invite(
            user.id,
            AuthProvider.BLUESKY,
            "used2.bsky.social",
            "did:plc:used2",
            None,
            InviteToken("token2"),
        )

        use_case = CreateInvitesUseCase(
            invite_service, user_service, user_identity_service, settings
        )

        request = CreateInvitesRequest(
            inviter_id=str(user.id),
            invitees=[
                InviteeInfo(
                    provider=AuthProvider.BLUESKY, handle="new.bsky.social", name=None
                )
            ],
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Insufficient invite quota.*Available: 0"):
            await use_case.execute(request)

    @pytest.mark.asyncio
    async def test_create_invites_partial_quota_success(self, unit_env):
        """Should succeed when creating invites within available quota."""
        # Arrange
        user_repo = await unit_env.get(UserRepository)
        user_service = await unit_env.get(UserService)
        user_identity_service = await unit_env.get(UserIdentityService)
        invite_service = await unit_env.get(InviteService)
        settings = await unit_env.get(Settings)

        # Create user with quota of 5
        user = await self._create_test_user(
            user_repo, "inviter.bsky.social", invite_quota=5
        )

        # Use up 3 of the quota
        await invite_service.create_invite(
            user.id,
            AuthProvider.BLUESKY,
            "used1.bsky.social",
            "did:plc:used1",
            None,
            InviteToken("token1"),
        )
        await invite_service.create_invite(
            user.id,
            AuthProvider.BLUESKY,
            "used2.bsky.social",
            "did:plc:used2",
            None,
            InviteToken("token2"),
        )
        await invite_service.create_invite(
            user.id,
            AuthProvider.BLUESKY,
            "used3.bsky.social",
            "did:plc:used3",
            None,
            InviteToken("token3"),
        )

        use_case = CreateInvitesUseCase(
            invite_service, user_service, user_identity_service, settings
        )
        use_case._normalize_and_resolve = mock_normalize_and_resolve

        # Create exactly 2 more (uses all remaining quota)
        request = CreateInvitesRequest(
            inviter_id=str(user.id),
            invitees=[
                InviteeInfo(
                    provider=AuthProvider.BLUESKY, handle="new1.bsky.social", name=None
                ),
                InviteeInfo(
                    provider=AuthProvider.BLUESKY, handle="new2.bsky.social", name=None
                ),
            ],
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert len(response.invites) == 2
        assert response.failed_invitees == []

        # Verify quota is now fully used
        pending_count = await invite_service.get_pending_count(user.id)
        assert pending_count == 5  # All quota used
