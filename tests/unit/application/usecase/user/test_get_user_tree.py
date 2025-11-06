"""Unit tests for GetUserTreeUseCase."""

from uuid import uuid4

import pytest

from talk.application.usecase.user.get_user_tree import GetUserTreeUseCase
from talk.domain.model import Invite, User
from talk.domain.service import UserService
from talk.domain.value import AuthProvider, InviteId, InviteStatus, InviteToken, UserId
from talk.domain.value.types import Handle
from talk.persistence.repository.inmemory import (
    InMemoryInviteRepository,
    InMemoryUserRepository,
)


class TestGetUserTreeUseCase:
    """Tests for GetUserTreeUseCase."""

    @pytest.mark.asyncio
    async def test_returns_tree_structure(self):
        """Should return tree structure with roots and total count."""
        # Arrange
        user_repo = InMemoryUserRepository()
        invite_repo = InMemoryInviteRepository()
        user_service = UserService(user_repo, invite_repo)
        use_case = GetUserTreeUseCase(user_service)

        parent = User(id=UserId(uuid4()), handle=Handle("parent"), karma=100)
        child = User(id=UserId(uuid4()), handle=Handle("child"), karma=50)
        await user_repo.save(parent)
        await user_repo.save(child)

        invite = Invite(
            id=InviteId(uuid4()),
            inviter_id=parent.id,
            provider=AuthProvider.BLUESKY,
            invitee_handle="child",
            invitee_provider_id="did:child",
            invite_token=InviteToken(str(uuid4())),
            status=InviteStatus.ACCEPTED,
            accepted_by_user_id=child.id,
        )
        await invite_repo.save(invite)

        # Act
        response = await use_case.execute()

        # Assert
        assert len(response.roots) == 1
        assert response.total_users == 2
        assert response.roots[0].user_id == str(parent.id)
        assert response.roots[0].handle == "parent"
        assert response.roots[0].karma == 100
        assert len(response.roots[0].children) == 1
        assert response.roots[0].children[0].user_id == str(child.id)

    @pytest.mark.asyncio
    async def test_converts_domain_model_to_response(self):
        """Should convert domain UserTreeNode to response model."""
        # Arrange
        user_repo = InMemoryUserRepository()
        invite_repo = InMemoryInviteRepository()
        user_service = UserService(user_repo, invite_repo)
        use_case = GetUserTreeUseCase(user_service)

        user = User(id=UserId(uuid4()), handle=Handle("test.user"), karma=42)
        await user_repo.save(user)

        # Act
        response = await use_case.execute()

        # Assert
        assert len(response.roots) == 1
        assert isinstance(response.roots[0].user_id, str)  # Converted to string
        assert isinstance(response.roots[0].handle, str)  # Converted to string
        assert response.roots[0].karma == 42

    @pytest.mark.asyncio
    async def test_counts_total_users_recursively(self):
        """Should count total users across entire tree."""
        # Arrange
        user_repo = InMemoryUserRepository()
        invite_repo = InMemoryInviteRepository()
        user_service = UserService(user_repo, invite_repo)
        use_case = GetUserTreeUseCase(user_service)

        # Create tree: root -> child -> grandchild
        root = User(id=UserId(uuid4()), handle=Handle("root"), karma=100)
        child = User(id=UserId(uuid4()), handle=Handle("child"), karma=50)
        grandchild = User(id=UserId(uuid4()), handle=Handle("grandchild"), karma=25)

        await user_repo.save(root)
        await user_repo.save(child)
        await user_repo.save(grandchild)

        invite1 = Invite(
            id=InviteId(uuid4()),
            inviter_id=root.id,
            provider=AuthProvider.BLUESKY,
            invitee_handle="child",
            invitee_provider_id="did:child",
            invite_token=InviteToken(str(uuid4())),
            status=InviteStatus.ACCEPTED,
            accepted_by_user_id=child.id,
        )
        invite2 = Invite(
            id=InviteId(uuid4()),
            inviter_id=child.id,
            provider=AuthProvider.BLUESKY,
            invitee_handle="grandchild",
            invitee_provider_id="did:grandchild",
            invite_token=InviteToken(str(uuid4())),
            status=InviteStatus.ACCEPTED,
            accepted_by_user_id=grandchild.id,
        )
        await invite_repo.save(invite1)
        await invite_repo.save(invite2)

        # Act
        response = await use_case.execute()

        # Assert
        assert response.total_users == 3

    @pytest.mark.asyncio
    async def test_respects_include_karma_parameter(self):
        """Should pass through include_karma parameter to service."""
        # Arrange
        user_repo = InMemoryUserRepository()
        invite_repo = InMemoryInviteRepository()
        user_service = UserService(user_repo, invite_repo)
        use_case = GetUserTreeUseCase(user_service)

        user = User(id=UserId(uuid4()), handle=Handle("user"), karma=100)
        await user_repo.save(user)

        # Act
        response = await use_case.execute(include_karma=False)

        # Assert
        assert response.roots[0].karma is None

    @pytest.mark.asyncio
    async def test_empty_tree(self):
        """Should handle empty tree gracefully."""
        # Arrange
        user_repo = InMemoryUserRepository()
        invite_repo = InMemoryInviteRepository()
        user_service = UserService(user_repo, invite_repo)
        use_case = GetUserTreeUseCase(user_service)

        # Act
        response = await use_case.execute()

        # Assert
        assert response.roots == []
        assert response.total_users == 0

    @pytest.mark.asyncio
    async def test_multiple_roots(self):
        """Should handle multiple root users."""
        # Arrange
        user_repo = InMemoryUserRepository()
        invite_repo = InMemoryInviteRepository()
        user_service = UserService(user_repo, invite_repo)
        use_case = GetUserTreeUseCase(user_service)

        root1 = User(id=UserId(uuid4()), handle=Handle("root1"), karma=100)
        root2 = User(id=UserId(uuid4()), handle=Handle("root2"), karma=150)
        await user_repo.save(root1)
        await user_repo.save(root2)

        # Act
        response = await use_case.execute()

        # Assert
        assert len(response.roots) == 2
        assert response.total_users == 2
