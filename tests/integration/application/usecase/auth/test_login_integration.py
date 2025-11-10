"""Integration test for LoginUseCase with real database.

This test demonstrates:
1. Using real PostgreSQL database via docker-compose
2. Running migrations before tests
3. Testing the full invite-only user creation flow
4. Using the test harness with unmocked persistence
"""

from datetime import datetime
from uuid import uuid4

from dishka import AsyncContainer
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from talk.application.usecase.auth.login import LoginRequest, LoginUseCase
from talk.config import Settings
from talk.domain.model.user import User
from talk.domain.repository import InviteRepository, UserRepository
from talk.domain.service import InviteService, UserIdentityService, UserService
from talk.domain.value import AuthProvider, InviteToken, UserId
from talk.domain.value.types import Handle
from tests.harness import create_env_fixture

# Integration test fixture - real PostgreSQL, mocked external services
integration_env = create_env_fixture(unmock={"persistence"})


@pytest_asyncio.fixture(autouse=True)
async def clean_database(integration_env):
    """Clean database before each test."""
    # Get session from DI container
    session = await integration_env.get(AsyncSession)

    # Truncate all tables (CASCADE removes foreign key constraints)
    await session.execute(
        text(
            "TRUNCATE TABLE comments, votes, posts, invites, user_identities, users CASCADE"
        )
    )
    await session.commit()

    yield
    # No cleanup needed after test since next test will truncate


class TestLoginIntegration:
    """Integration tests for login flow with real database."""

    @pytest.mark.asyncio
    async def test_create_new_user_with_invite_full_stack(
        self, integration_env: AsyncContainer
    ):
        """Test creating a new user through login with invite - full database stack.

        This test validates:
        - InviteService can create invites in real PostgreSQL
        - LoginUseCase can authenticate and create users
        - Invite is properly marked as accepted
        - Data persists correctly across the full stack
        """
        # Arrange - Get real repositories from DI container
        user_repo = await integration_env.get(UserRepository)
        user_service = await integration_env.get(UserService)
        user_identity_service = await integration_env.get(UserIdentityService)
        invite_service = await integration_env.get(InviteService)
        login_use_case = await integration_env.get(LoginUseCase)
        settings = await integration_env.get(Settings)

        # Enable invite-only mode for this test
        settings.auth.invite_only = True

        # Create an inviter (this user would normally exist from previous signup)
        inviter_id = UserId(uuid4())
        inviter = User(
            id=inviter_id,
            handle=Handle("inviter.bsky.social"),
            avatar_url=None,
            email=None,
            bio=None,
            karma=100,
            invite_quota=5,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        await user_repo.save(inviter)

        # Inviter creates an invite for new user (MockBlueskyAuthClient returns "user.bsky.social")
        invite_token = InviteToken(root="test-invite-token-123")
        created_invite = await invite_service.create_invite(
            inviter_id=inviter_id,
            provider=AuthProvider.BLUESKY,
            invitee_handle="user.bsky.social",
            invitee_provider_id="did:plc:mock123",
            invitee_name=None,
            invite_token=invite_token,
        )

        # Verify invite was saved to database
        invite_repo = await integration_env.get(InviteRepository)
        saved_invite = await invite_repo.find_by_id(created_invite.id)
        assert saved_invite is not None
        assert saved_invite.status.value == "pending"
        assert saved_invite.invitee_handle == "user.bsky.social"

        # Act - New user logs in (MockBlueskyAuthClient will return user.bsky.social)
        login_response = await login_use_case.execute(
            LoginRequest(
                provider=AuthProvider.BLUESKY,
                code="oauth_123",
                state="test_state",
                iss="https://bsky.social",
            )
        )

        # Assert - User was created
        assert login_response.token is not None
        assert login_response.handle.root == "user.bsky.social"

        # Verify user exists in database via identity
        created_identity = await user_identity_service.get_identity_by_provider(
            AuthProvider.BLUESKY, "did:plc:mock123"
        )
        assert created_identity is not None

        created_user = await user_service.get_by_id(created_identity.user_id)
        assert created_user is not None
        assert created_user.handle.root == "user.bsky.social"
        assert created_user.karma == 0  # New users start with 0 karma
        assert created_user.invite_quota == 5  # Default quota

        # Verify invite was marked as accepted in database
        updated_invite = await invite_repo.find_by_id(created_invite.id)
        assert updated_invite is not None
        assert updated_invite.status.value == "accepted"
        assert updated_invite.accepted_by_user_id == created_user.id
        assert updated_invite.accepted_at is not None

        # Verify no pending invite remains (login check should fail for second attempt)
        has_pending = await invite_service.check_invite_exists(
            AuthProvider.BLUESKY, "did:plc:mock123"
        )
        assert has_pending is False

    @pytest.mark.asyncio
    async def test_reject_new_user_without_invite_database(self, integration_env):
        """Test that new user signup is rejected without invite - database verified.

        This validates the invite-only enforcement at the database level.
        """
        # Arrange
        login_use_case = await integration_env.get(LoginUseCase)
        user_identity_service = await integration_env.get(UserIdentityService)
        settings = await integration_env.get(Settings)

        # Enable invite-only mode for this test
        settings.auth.invite_only = True

        # Act & Assert - Try to login without invite
        with pytest.raises(ValueError, match="No invitation found.*invite-only"):
            await login_use_case.execute(
                LoginRequest(
                    provider=AuthProvider.BLUESKY,
                    code="oauth_123",
                    state="test_state",
                    iss="https://bsky.social",
                )
            )

        # Verify no user identity was created in database
        identity = await user_identity_service.get_identity_by_provider(
            AuthProvider.BLUESKY, "did:plc:mock123"
        )
        assert identity is None
