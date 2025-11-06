"""Unit tests for UserService."""

from uuid import uuid4

import pytest

from talk.domain.model import Invite, User
from talk.domain.service import UserService
from talk.domain.value import AuthProvider, InviteId, InviteStatus, InviteToken, UserId
from talk.domain.value.types import Handle
from talk.persistence.repository.inmemory import (
    InMemoryInviteRepository,
    InMemoryUserRepository,
)


class TestBuildInvitationTree:
    """Tests for UserService.build_invitation_tree()."""

    @pytest.mark.asyncio
    async def test_build_tree_with_single_root(self):
        """Should build tree with single root user."""
        # Arrange
        user_repo = InMemoryUserRepository()
        invite_repo = InMemoryInviteRepository()
        service = UserService(user_repo, invite_repo)

        root_user = User(
            id=UserId(uuid4()),
            handle=Handle("root.user"),
            karma=100,
        )
        await user_repo.save(root_user)

        # Act
        tree = await service.build_invitation_tree()

        # Assert
        assert len(tree) == 1
        assert tree[0].user_id == root_user.id
        assert tree[0].handle == root_user.handle
        assert tree[0].karma == 100
        assert len(tree[0].children) == 0

    @pytest.mark.asyncio
    async def test_build_tree_with_parent_child(self):
        """Should build tree with parent-child relationship."""
        # Arrange
        user_repo = InMemoryUserRepository()
        invite_repo = InMemoryInviteRepository()
        service = UserService(user_repo, invite_repo)

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
        tree = await service.build_invitation_tree()

        # Assert
        assert len(tree) == 1  # One root
        assert tree[0].user_id == parent.id
        assert len(tree[0].children) == 1
        assert tree[0].children[0].user_id == child.id
        assert tree[0].children[0].karma == 50

    @pytest.mark.asyncio
    async def test_build_tree_sorts_children_by_karma(self):
        """Should sort children by karma descending."""
        # Arrange
        user_repo = InMemoryUserRepository()
        invite_repo = InMemoryInviteRepository()
        service = UserService(user_repo, invite_repo)

        parent = User(id=UserId(uuid4()), handle=Handle("parent"), karma=100)
        child1 = User(id=UserId(uuid4()), handle=Handle("child1"), karma=30)
        child2 = User(id=UserId(uuid4()), handle=Handle("child2"), karma=80)
        child3 = User(id=UserId(uuid4()), handle=Handle("child3"), karma=50)

        await user_repo.save(parent)
        await user_repo.save(child1)
        await user_repo.save(child2)
        await user_repo.save(child3)

        # Create invites
        for child in [child1, child2, child3]:
            invite = Invite(
                id=InviteId(uuid4()),
                inviter_id=parent.id,
                provider=AuthProvider.BLUESKY,
                invitee_handle=child.handle.root,
                invitee_provider_id=f"did:{child.handle.root}",
                invite_token=InviteToken(str(uuid4())),
                status=InviteStatus.ACCEPTED,
                accepted_by_user_id=child.id,
            )
            await invite_repo.save(invite)

        # Act
        tree = await service.build_invitation_tree()

        # Assert
        assert len(tree[0].children) == 3
        # Should be sorted by karma descending: child2 (80), child3 (50), child1 (30)
        assert tree[0].children[0].karma == 80
        assert tree[0].children[1].karma == 50
        assert tree[0].children[2].karma == 30

    @pytest.mark.asyncio
    async def test_build_tree_with_multiple_roots(self):
        """Should handle multiple root users (no parent)."""
        # Arrange
        user_repo = InMemoryUserRepository()
        invite_repo = InMemoryInviteRepository()
        service = UserService(user_repo, invite_repo)

        root1 = User(id=UserId(uuid4()), handle=Handle("root1"), karma=100)
        root2 = User(id=UserId(uuid4()), handle=Handle("root2"), karma=150)
        await user_repo.save(root1)
        await user_repo.save(root2)

        # Act
        tree = await service.build_invitation_tree()

        # Assert
        assert len(tree) == 2
        # Roots should be sorted by karma descending
        assert tree[0].karma == 150  # root2
        assert tree[1].karma == 100  # root1

    @pytest.mark.asyncio
    async def test_build_tree_with_deep_hierarchy(self):
        """Should build tree with multiple levels of depth."""
        # Arrange
        user_repo = InMemoryUserRepository()
        invite_repo = InMemoryInviteRepository()
        service = UserService(user_repo, invite_repo)

        # Create hierarchy: root -> child -> grandchild
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
        tree = await service.build_invitation_tree()

        # Assert
        assert len(tree) == 1
        assert tree[0].user_id == root.id
        assert len(tree[0].children) == 1
        assert tree[0].children[0].user_id == child.id
        assert len(tree[0].children[0].children) == 1
        assert tree[0].children[0].children[0].user_id == grandchild.id

    @pytest.mark.asyncio
    async def test_build_tree_excludes_pending_invites(self):
        """Should only include accepted invites in tree."""
        # Arrange
        user_repo = InMemoryUserRepository()
        invite_repo = InMemoryInviteRepository()
        service = UserService(user_repo, invite_repo)

        parent = User(id=UserId(uuid4()), handle=Handle("parent"), karma=100)
        child = User(id=UserId(uuid4()), handle=Handle("child"), karma=50)
        await user_repo.save(parent)
        await user_repo.save(child)

        # Create pending invite (should be excluded)
        invite = Invite(
            id=InviteId(uuid4()),
            inviter_id=parent.id,
            provider=AuthProvider.BLUESKY,
            invitee_handle="child",
            invitee_provider_id="did:child",
            invite_token=InviteToken(str(uuid4())),
            status=InviteStatus.PENDING,  # Pending, not accepted
        )
        await invite_repo.save(invite)

        # Act
        tree = await service.build_invitation_tree()

        # Assert - both should be roots since invite is pending
        assert len(tree) == 2
        assert all(len(node.children) == 0 for node in tree)

    @pytest.mark.asyncio
    async def test_build_tree_without_karma(self):
        """Should build tree without karma when include_karma=False."""
        # Arrange
        user_repo = InMemoryUserRepository()
        invite_repo = InMemoryInviteRepository()
        service = UserService(user_repo, invite_repo)

        user = User(id=UserId(uuid4()), handle=Handle("user"), karma=100)
        await user_repo.save(user)

        # Act
        tree = await service.build_invitation_tree(include_karma=False)

        # Assert
        assert len(tree) == 1
        assert tree[0].karma is None

    @pytest.mark.asyncio
    async def test_build_tree_empty_database(self):
        """Should return empty tree for empty database."""
        # Arrange
        user_repo = InMemoryUserRepository()
        invite_repo = InMemoryInviteRepository()
        service = UserService(user_repo, invite_repo)

        # Act
        tree = await service.build_invitation_tree()

        # Assert
        assert tree == []
