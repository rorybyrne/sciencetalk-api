"""Unit tests for LoginUseCase."""

from datetime import datetime
from uuid import uuid4

import pytest

from talk.application.usecase.auth.login import LoginRequest, LoginUseCase
from talk.domain.model.user import User
from talk.domain.service import AuthService, JWTService
from talk.domain.value import UserId
from talk.domain.value.types import BlueskyDID, Handle
from talk.persistence.repository.user import UserRepository
from tests.harness import create_env_fixture

# Unit test fixture
unit_env = create_env_fixture()


class TestLoginUseCase:
    """Tests for LoginUseCase."""

    @pytest.mark.asyncio
    async def test_login_creates_new_user_when_not_exists(self, unit_env):
        """Login should create new user when not exists."""
        # Arrange
        user_repo = await unit_env.get(UserRepository)
        auth_service = await unit_env.get(AuthService)
        jwt_service = await unit_env.get(JWTService)

        login_use_case = LoginUseCase(
            auth_service=auth_service,
            jwt_service=jwt_service,
            user_repository=user_repo,
        )

        code = "oauth_code_123"

        # Act
        response = await login_use_case.execute(LoginRequest(code=code))

        # Assert
        # Verify user was created (MockBlueskyAuthClient returns mock data)
        saved_user = await user_repo.find_by_bluesky_did(
            BlueskyDID(value="did:plc:mock123")
        )
        assert saved_user is not None
        assert saved_user.handle.value == "user.bsky.social"
        assert saved_user.karma == 0  # New users start with 0 karma

        # Verify response
        assert response.token is not None
        assert response.handle == "user.bsky.social"

    @pytest.mark.asyncio
    async def test_login_updates_existing_user(self, unit_env):
        """Login should update existing user handle/display/avatar."""
        # Arrange
        user_repo = await unit_env.get(UserRepository)
        auth_service = await unit_env.get(AuthService)
        jwt_service = await unit_env.get(JWTService)

        login_use_case = LoginUseCase(
            auth_service=auth_service,
            jwt_service=jwt_service,
            user_repository=user_repo,
        )

        # Create existing user with same DID as mock client will return
        existing_user_id = UserId(uuid4())
        existing_user = User(
            id=existing_user_id,
            bluesky_did=BlueskyDID(value="did:plc:mock123"),
            handle=Handle(value="old.bsky.social"),
            display_name="Old Name",
            avatar_url="https://example.com/old_avatar.jpg",
            karma=150,
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1),
        )
        await user_repo.save(existing_user)

        code = "oauth_code_456"

        # Act
        response = await login_use_case.execute(LoginRequest(code=code))

        # Assert
        saved_user = await user_repo.find_by_bluesky_did(
            BlueskyDID(value="did:plc:mock123")
        )

        # Verify user ID preserved
        assert saved_user.id == existing_user_id

        # Verify user data updated from mock auth client
        assert saved_user.handle.value == "user.bsky.social"
        assert saved_user.display_name == "Test User"

        # Verify karma preserved
        assert saved_user.karma == 150

        # Verify timestamps
        assert saved_user.created_at == existing_user.created_at
        assert saved_user.updated_at > existing_user.updated_at

        assert response.user_id == str(existing_user_id)
