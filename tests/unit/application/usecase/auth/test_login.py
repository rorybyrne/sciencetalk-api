"""Unit tests for LoginUseCase."""

from datetime import datetime, timezone
from uuid import uuid4

from dishka import AsyncContainer
import pytest

from talk.application.usecase.auth.login import LoginRequest, LoginUseCase
from talk.config import Settings
from talk.domain.model.user import User
from talk.domain.service import (
    AuthService,
    InviteService,
    JWTService,
    UserIdentityService,
    UserService,
)
from talk.domain.value import AuthProvider, InviteToken, UserId, UserIdentityId
from talk.domain.value.types import Handle
from tests.harness import create_env_fixture

# Unit test fixture
unit_env = create_env_fixture()


class TestLoginUseCase:
    """Tests for LoginUseCase."""

    @pytest.mark.asyncio
    async def test_login_creates_new_user_when_not_exists_and_has_invite(
        self, unit_env: AsyncContainer
    ):
        """Login should create new user when not exists and has pending invite."""
        # Arrange
        user_service = await unit_env.get(UserService)
        user_identity_service = await unit_env.get(UserIdentityService)
        auth_service = await unit_env.get(AuthService)
        jwt_service = await unit_env.get(JWTService)
        invite_service = await unit_env.get(InviteService)
        settings = await unit_env.get(Settings)

        # Create a pending invite for the user (MockBlueskyAuthClient returns "user.bsky.social")
        inviter_id = UserId(uuid4())
        invite_token = InviteToken(root="test-token-123")
        await invite_service.create_invite(
            inviter_id=inviter_id,
            provider=AuthProvider.BLUESKY,
            invitee_handle="user.bsky.social",
            invitee_provider_id="did:plc:mock123",
            invitee_name=None,
            invite_token=invite_token,
        )

        login_use_case = LoginUseCase(
            auth_service=auth_service,
            jwt_service=jwt_service,
            user_service=user_service,
            user_identity_service=user_identity_service,
            invite_service=invite_service,
            settings=settings,
        )

        code = "oauth_code_123"
        state = "test_state_123"
        iss = "https://bsky.social"

        # Act
        response = await login_use_case.execute(
            LoginRequest(provider=AuthProvider.BLUESKY, code=code, state=state, iss=iss)
        )

        # Assert
        # Verify user was created (MockBlueskyAuthClient returns mock data)
        identity = await user_identity_service.get_identity_by_provider(
            AuthProvider.BLUESKY, "did:plc:mock123"
        )
        assert identity is not None

        saved_user = await user_service.get_by_id(identity.user_id)
        assert saved_user is not None
        assert saved_user.handle.root == "user.bsky.social"
        assert saved_user.karma == 0  # New users start with 0 karma
        assert saved_user.invite_quota == 5  # Default quota

        # Verify response
        assert response.token is not None
        assert response.handle.root == "user.bsky.social"

        # Verify invite was marked as accepted
        has_pending = await invite_service.check_invite_exists(
            AuthProvider.BLUESKY, "did:plc:mock123"
        )
        assert has_pending is False  # No longer pending

    @pytest.mark.asyncio
    async def test_login_updates_existing_user(self, unit_env):
        """Login should update existing user last_login_at for existing identity."""
        # Arrange
        user_service = await unit_env.get(UserService)
        user_identity_service = await unit_env.get(UserIdentityService)
        auth_service = await unit_env.get(AuthService)
        jwt_service = await unit_env.get(JWTService)
        invite_service = await unit_env.get(InviteService)
        settings = await unit_env.get(Settings)

        login_use_case = LoginUseCase(
            auth_service=auth_service,
            jwt_service=jwt_service,
            user_service=user_service,
            user_identity_service=user_identity_service,
            invite_service=invite_service,
            settings=settings,
        )

        # Create existing user with identity
        existing_user_id = UserId(uuid4())
        existing_user = User(
            id=existing_user_id,
            handle=Handle("old.bsky.social"),
            avatar_url="https://example.com/old_avatar.jpg",
            email=None,
            bio=None,
            karma=150,
            invite_quota=10,
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        await user_service.save(existing_user)

        # Create identity for this user (mock client will return same DID)
        from talk.domain.model.user_identity import UserIdentity

        identity = UserIdentity(
            id=UserIdentityId(uuid4()),
            user_id=existing_user_id,
            provider=AuthProvider.BLUESKY,
            provider_user_id="did:plc:mock123",
            provider_handle="old.bsky.social",
            provider_email=None,
            is_primary=True,
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            last_login_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        await user_identity_service.save(identity)

        code = "oauth_code_456"
        state = "test_state_456"
        iss = "https://bsky.social"

        # Act
        response = await login_use_case.execute(
            LoginRequest(provider=AuthProvider.BLUESKY, code=code, state=state, iss=iss)
        )

        # Assert
        # Verify user ID preserved
        assert response.user_id == str(existing_user_id)

        # Verify user still exists
        saved_user = await user_service.get_by_id(existing_user_id)
        assert saved_user is not None

        # Verify karma preserved
        assert saved_user.karma == 150

        # Verify invite_quota preserved
        assert saved_user.invite_quota == 10

        # Verify identity last_login_at was updated
        updated_identity = await user_identity_service.get_identity_by_provider(
            AuthProvider.BLUESKY, "did:plc:mock123"
        )
        assert updated_identity is not None
        assert updated_identity.last_login_at > identity.last_login_at

    @pytest.mark.asyncio
    async def test_login_rejects_new_user_without_invite(self, unit_env):
        """Login should reject new user signup when no pending invite exists."""
        # Arrange
        user_service = await unit_env.get(UserService)
        user_identity_service = await unit_env.get(UserIdentityService)
        auth_service = await unit_env.get(AuthService)
        jwt_service = await unit_env.get(JWTService)
        invite_service = await unit_env.get(InviteService)
        settings = await unit_env.get(Settings)

        login_use_case = LoginUseCase(
            auth_service=auth_service,
            jwt_service=jwt_service,
            user_service=user_service,
            user_identity_service=user_identity_service,
            invite_service=invite_service,
            settings=settings,
        )

        code = "oauth_code_123"
        state = "test_state_789"
        iss = "https://bsky.social"

        # Act & Assert - Should raise error because no invite exists
        with pytest.raises(ValueError, match="No invitation found.*invite-only"):
            await login_use_case.execute(
                LoginRequest(
                    provider=AuthProvider.BLUESKY, code=code, state=state, iss=iss
                )
            )

        # Verify user was NOT created
        identity = await user_identity_service.get_identity_by_provider(
            AuthProvider.BLUESKY, "did:plc:mock123"
        )
        assert identity is None

    @pytest.mark.asyncio
    async def test_login_accepts_new_user_with_accepted_invite_rejected(self, unit_env):
        """Login should reject new user when invite was already accepted."""
        # Arrange
        user_service = await unit_env.get(UserService)
        user_identity_service = await unit_env.get(UserIdentityService)
        auth_service = await unit_env.get(AuthService)
        jwt_service = await unit_env.get(JWTService)
        invite_service = await unit_env.get(InviteService)
        settings = await unit_env.get(Settings)

        # Create invite and mark as accepted
        inviter_id = UserId(uuid4())
        invite_token = InviteToken(root="test-token-999")
        invite = await invite_service.create_invite(
            inviter_id=inviter_id,
            provider=AuthProvider.BLUESKY,
            invitee_handle="user.bsky.social",
            invitee_provider_id="did:plc:mock123",
            invitee_name=None,
            invite_token=invite_token,
        )
        await invite_service.accept_invite(invite.id, UserId(uuid4()))

        login_use_case = LoginUseCase(
            auth_service=auth_service,
            jwt_service=jwt_service,
            user_service=user_service,
            user_identity_service=user_identity_service,
            invite_service=invite_service,
            settings=settings,
        )

        code = "oauth_code_123"
        state = "test_state_999"
        iss = "https://bsky.social"

        # Act & Assert - Should fail because invite is no longer pending
        with pytest.raises(ValueError, match="No invitation found.*invite-only"):
            await login_use_case.execute(
                LoginRequest(
                    provider=AuthProvider.BLUESKY, code=code, state=state, iss=iss
                )
            )

    @pytest.mark.asyncio
    async def test_login_allows_seed_user_without_invite(
        self, unit_env: AsyncContainer
    ):
        """Login should allow seed users to sign up without invite."""
        # Arrange
        user_service = await unit_env.get(UserService)
        user_identity_service = await unit_env.get(UserIdentityService)
        auth_service = await unit_env.get(AuthService)
        jwt_service = await unit_env.get(JWTService)
        invite_service = await unit_env.get(InviteService)
        settings = await unit_env.get(Settings)

        # Configure seed user (MockBlueskyAuthClient returns "user.bsky.social")
        settings.invitations.seed_users = ["user.bsky.social"]

        login_use_case = LoginUseCase(
            auth_service=auth_service,
            jwt_service=jwt_service,
            user_service=user_service,
            user_identity_service=user_identity_service,
            invite_service=invite_service,
            settings=settings,
        )

        code = "oauth_code_seed"
        state = "test_state_seed"
        iss = "https://bsky.social"

        # Act - No invite created, but should succeed because user is seed user
        response = await login_use_case.execute(
            LoginRequest(provider=AuthProvider.BLUESKY, code=code, state=state, iss=iss)
        )

        # Assert
        # Verify user was created
        identity = await user_identity_service.get_identity_by_provider(
            AuthProvider.BLUESKY, "did:plc:mock123"
        )
        assert identity is not None

        saved_user = await user_service.get_by_id(identity.user_id)
        assert saved_user is not None
        assert saved_user.handle.root == "user.bsky.social"
        assert saved_user.karma == 0
        assert saved_user.invite_quota == 5

        # Verify response
        assert response.token is not None
        assert response.handle.root == "user.bsky.social"

        # Verify no invite was needed
        has_pending = await invite_service.check_invite_exists(
            AuthProvider.BLUESKY, "did:plc:mock123"
        )
        assert has_pending is False  # No invite exists
