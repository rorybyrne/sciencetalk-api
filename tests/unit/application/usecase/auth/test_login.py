"""Unit tests for LoginUseCase."""

from datetime import datetime
from uuid import uuid4

import pytest

from talk.application.usecase.auth.login import LoginRequest, LoginUseCase
from talk.config import Settings
from talk.domain.model.user import User
from talk.domain.service import AuthService, InviteService, JWTService
from talk.domain.value import UserId
from talk.domain.value.types import BlueskyDID, Handle
from talk.persistence.repository.user import UserRepository
from tests.harness import create_env_fixture

# Unit test fixture
unit_env = create_env_fixture()


class TestLoginUseCase:
    """Tests for LoginUseCase."""

    @pytest.mark.asyncio
    async def test_login_creates_new_user_when_not_exists_and_has_invite(
        self, unit_env
    ):
        """Login should create new user when not exists and has pending invite."""
        # Arrange
        user_repo = await unit_env.get(UserRepository)
        auth_service = await unit_env.get(AuthService)
        jwt_service = await unit_env.get(JWTService)
        invite_service = await unit_env.get(InviteService)
        settings = await unit_env.get(Settings)

        # Create a pending invite for the user (MockBlueskyAuthClient returns "user.bsky.social")
        inviter_id = UserId(uuid4())
        await invite_service.create_invite(inviter_id, Handle(root="user.bsky.social"))

        login_use_case = LoginUseCase(
            auth_service=auth_service,
            jwt_service=jwt_service,
            user_repository=user_repo,
            invite_service=invite_service,
            settings=settings,
        )

        code = "oauth_code_123"
        state = "test_state_123"
        iss = "https://bsky.social"

        # Act
        response = await login_use_case.execute(
            LoginRequest(code=code, state=state, iss=iss)
        )

        # Assert
        # Verify user was created (MockBlueskyAuthClient returns mock data)
        saved_user = await user_repo.find_by_bluesky_did(
            BlueskyDID(root="did:plc:mock123")
        )
        assert saved_user is not None
        assert saved_user.handle.root == "user.bsky.social"
        assert saved_user.karma == 0  # New users start with 0 karma
        assert saved_user.invite_quota == 5  # Default quota

        # Verify response
        assert response.token is not None
        assert response.handle.root == "user.bsky.social"

        # Verify invite was marked as accepted
        has_pending = await invite_service.check_invite_exists(
            Handle(root="user.bsky.social")
        )
        assert has_pending is False  # No longer pending

    @pytest.mark.asyncio
    async def test_login_updates_existing_user(self, unit_env):
        """Login should update existing user handle/display/avatar."""
        # Arrange
        user_repo = await unit_env.get(UserRepository)
        auth_service = await unit_env.get(AuthService)
        jwt_service = await unit_env.get(JWTService)
        invite_service = await unit_env.get(InviteService)
        settings = await unit_env.get(Settings)

        login_use_case = LoginUseCase(
            auth_service=auth_service,
            jwt_service=jwt_service,
            user_repository=user_repo,
            invite_service=invite_service,
            settings=settings,
        )

        # Create existing user with same DID as mock client will return
        existing_user_id = UserId(uuid4())
        existing_user = User(
            id=existing_user_id,
            bluesky_did=BlueskyDID(root="did:plc:mock123"),
            handle=Handle(root="old.bsky.social"),
            display_name="Old Name",
            avatar_url="https://example.com/old_avatar.jpg",
            karma=150,
            invite_quota=10,
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1),
        )
        await user_repo.save(existing_user)

        code = "oauth_code_456"
        state = "test_state_456"
        iss = "https://bsky.social"

        # Act
        response = await login_use_case.execute(
            LoginRequest(code=code, state=state, iss=iss)
        )

        # Assert
        saved_user = await user_repo.find_by_bluesky_did(
            BlueskyDID(root="did:plc:mock123")
        )

        # Verify user ID preserved
        assert saved_user.id == existing_user_id

        # Verify user data updated from mock auth client
        assert saved_user.handle.root == "user.bsky.social"
        assert saved_user.display_name == "Test User"

        # Verify karma preserved
        assert saved_user.karma == 150

        # Verify invite_quota preserved
        assert saved_user.invite_quota == 10

        # Verify timestamps
        assert saved_user.created_at == existing_user.created_at
        assert saved_user.updated_at > existing_user.updated_at

        assert response.user_id == str(existing_user_id)

    @pytest.mark.asyncio
    async def test_login_rejects_new_user_without_invite(self, unit_env):
        """Login should reject new user signup when no pending invite exists."""
        # Arrange
        user_repo = await unit_env.get(UserRepository)
        auth_service = await unit_env.get(AuthService)
        jwt_service = await unit_env.get(JWTService)
        invite_service = await unit_env.get(InviteService)
        settings = await unit_env.get(Settings)

        login_use_case = LoginUseCase(
            auth_service=auth_service,
            jwt_service=jwt_service,
            user_repository=user_repo,
            invite_service=invite_service,
            settings=settings,
        )

        code = "oauth_code_123"
        state = "test_state_789"
        iss = "https://bsky.social"

        # Act & Assert - Should raise error because no invite exists
        with pytest.raises(ValueError, match="No invite found.*invite-only"):
            await login_use_case.execute(LoginRequest(code=code, state=state, iss=iss))

        # Verify user was NOT created
        saved_user = await user_repo.find_by_bluesky_did(
            BlueskyDID(root="did:plc:mock123")
        )
        assert saved_user is None

    @pytest.mark.asyncio
    async def test_login_accepts_new_user_with_accepted_invite_rejected(self, unit_env):
        """Login should reject new user when invite was already accepted."""
        # Arrange
        user_repo = await unit_env.get(UserRepository)
        auth_service = await unit_env.get(AuthService)
        jwt_service = await unit_env.get(JWTService)
        invite_service = await unit_env.get(InviteService)
        settings = await unit_env.get(Settings)

        # Create invite and mark as accepted
        inviter_id = UserId(uuid4())
        await invite_service.create_invite(inviter_id, Handle(root="user.bsky.social"))
        await invite_service.accept_invite(
            Handle(root="user.bsky.social"), UserId(uuid4())
        )

        login_use_case = LoginUseCase(
            auth_service=auth_service,
            jwt_service=jwt_service,
            user_repository=user_repo,
            invite_service=invite_service,
            settings=settings,
        )

        code = "oauth_code_123"
        state = "test_state_999"
        iss = "https://bsky.social"

        # Act & Assert - Should fail because invite is no longer pending
        with pytest.raises(ValueError, match="No invite found.*invite-only"):
            await login_use_case.execute(LoginRequest(code=code, state=state, iss=iss))

    @pytest.mark.asyncio
    async def test_login_allows_seed_user_without_invite(self, unit_env):
        """Login should allow seed users (unlimited inviters) to sign up without invite."""
        # Arrange
        user_repo = await unit_env.get(UserRepository)
        auth_service = await unit_env.get(AuthService)
        jwt_service = await unit_env.get(JWTService)
        invite_service = await unit_env.get(InviteService)
        settings = await unit_env.get(Settings)

        # Override settings to add seed user
        # MockBlueskyAuthClient returns handle "user.bsky.social"
        settings.invitations.unlimited_inviters = [Handle(root="user.bsky.social")]

        login_use_case = LoginUseCase(
            auth_service=auth_service,
            jwt_service=jwt_service,
            user_repository=user_repo,
            invite_service=invite_service,
            settings=settings,
        )

        code = "oauth_code_seed"
        state = "test_state_seed"
        iss = "https://bsky.social"

        # Act - Should succeed without invite because user is a seed user
        response = await login_use_case.execute(
            LoginRequest(code=code, state=state, iss=iss)
        )

        # Assert
        # Verify user was created
        saved_user = await user_repo.find_by_bluesky_did(
            BlueskyDID(root="did:plc:mock123")
        )
        assert saved_user is not None
        assert saved_user.handle.root == "user.bsky.social"
        assert saved_user.karma == 0
        assert saved_user.invite_quota == 5

        # Verify response
        assert response.token is not None
        assert response.handle.root == "user.bsky.social"

        # Verify NO invite was used (seed users don't need invites)
        has_pending = await invite_service.check_invite_exists(
            Handle(root="user.bsky.social")
        )
        assert has_pending is False  # No invite needed or used
