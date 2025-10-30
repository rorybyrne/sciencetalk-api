"""Integration test for LoginUseCase with real database.

This test demonstrates:
1. Using real PostgreSQL database via docker-compose
2. Running migrations before tests
3. Testing the full invite-only user creation flow
4. Using the test harness with unmocked persistence
"""

from datetime import datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from talk.application.usecase.auth.login import LoginRequest, LoginUseCase
from talk.domain.model.user import User
from talk.domain.repository import InviteRepository, UserRepository
from talk.domain.service import InviteService
from talk.domain.value import UserId
from talk.domain.value.types import BlueskyDID, Handle
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
        text("TRUNCATE TABLE comments, votes, posts, invites, users CASCADE")
    )
    await session.commit()

    yield
    # No cleanup needed after test since next test will truncate


class TestLoginIntegration:
    """Integration tests for login flow with real database."""

    @pytest.mark.asyncio
    async def test_create_new_user_with_invite_full_stack(self, integration_env):
        """Test creating a new user through login with invite - full database stack.

        This test validates:
        - InviteService can create invites in real PostgreSQL
        - LoginUseCase can authenticate and create users
        - Invite is properly marked as accepted
        - Data persists correctly across the full stack
        """
        # Arrange - Get real repositories from DI container
        user_repo = await integration_env.get(UserRepository)
        invite_service = await integration_env.get(InviteService)
        login_use_case = await integration_env.get(LoginUseCase)

        # Create an inviter (this user would normally exist from previous signup)
        inviter_id = UserId(uuid4())
        inviter = User(
            id=inviter_id,
            bluesky_did=BlueskyDID(root=f"did:plc:{uuid4()}"),
            handle=Handle(root="inviter.bsky.social"),
            display_name="Original User",
            avatar_url=None,
            karma=100,
            invite_quota=5,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        await user_repo.save(inviter)

        # Inviter creates an invite for new user (MockBlueskyAuthClient returns "user.bsky.social")
        new_user_handle = Handle(root="user.bsky.social")
        new_user_did = BlueskyDID("did:plc:mock123")
        created_invite = await invite_service.create_invite(
            inviter_id, new_user_handle, new_user_did
        )

        # Verify invite was saved to database
        invite_repo = await integration_env.get(InviteRepository)
        saved_invite = await invite_repo.find_by_id(created_invite.id)
        assert saved_invite is not None
        assert saved_invite.status.value == "pending"
        assert saved_invite.invitee_handle.root == "user.bsky.social"

        # Act - New user logs in (MockBlueskyAuthClient will return user.bsky.social)
        login_response = await login_use_case.execute(
            LoginRequest(
                code="oauth_123", state="test_state", iss="https://bsky.social"
            )
        )

        # Assert - User was created
        assert login_response.token is not None
        assert login_response.handle.root == "user.bsky.social"

        # Verify user exists in database
        created_user = await user_repo.find_by_bluesky_did(
            BlueskyDID(root="did:plc:mock123")
        )
        assert created_user is not None
        assert created_user.handle.root == "user.bsky.social"
        assert created_user.karma == 0  # New users start with 0 karma
        assert created_user.invite_quota == 5  # Default quota

        # Verify invite was marked as accepted in database
        updated_invite = await invite_repo.find_by_id(created_invite.id)
        assert updated_invite.status.value == "accepted"
        assert updated_invite.accepted_by_user_id == created_user.id
        assert updated_invite.accepted_at is not None

        # Verify no pending invite remains (login check should fail for second attempt)
        has_pending = await invite_service.check_invite_exists(new_user_did)
        assert has_pending is False

    @pytest.mark.asyncio
    async def test_reject_new_user_without_invite_database(self, integration_env):
        """Test that new user signup is rejected without invite - database verified.

        This validates the invite-only enforcement at the database level.
        """
        # Arrange
        login_use_case = await integration_env.get(LoginUseCase)
        user_repo = await integration_env.get(UserRepository)

        # Act & Assert - Try to login without invite
        with pytest.raises(ValueError, match="No invite found.*invite-only"):
            await login_use_case.execute(
                LoginRequest(
                    code="oauth_123", state="test_state", iss="https://bsky.social"
                )
            )

        # Verify no user was created in database
        user = await user_repo.find_by_bluesky_did(BlueskyDID(root="did:plc:mock123"))
        assert user is None
