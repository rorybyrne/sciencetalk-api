"""User domain service."""

from collections import defaultdict
from dataclasses import dataclass

import logfire

from talk.domain.error import NotFoundError
from talk.domain.model import User
from talk.domain.repository import InviteRepository, UserRepository
from talk.domain.value import AuthProvider, UserId
from talk.domain.value.types import Handle


@dataclass
class UserTreeNode:
    """Node in the user invitation tree.

    Represents a user and their invited children in the invitation hierarchy.
    """

    user_id: UserId
    handle: Handle
    karma: int | None
    children: list["UserTreeNode"]


class UserService:
    """Domain service for user operations."""

    def __init__(
        self,
        user_repository: UserRepository,
        invite_repository: InviteRepository,
    ) -> None:
        """Initialize user service.

        Args:
            user_repository: User repository
            invite_repository: Invite repository
        """
        self.user_repository = user_repository
        self.invite_repository = invite_repository

    async def get_by_id(self, user_id: UserId) -> User:
        """Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User entity

        Raises:
            NotFoundError: If user not found
        """
        with logfire.span("user_service.get_by_id", user_id=str(user_id)):
            user = await self.user_repository.find_by_id(user_id)
            if not user:
                logfire.warn("User not found", user_id=str(user_id))
                raise NotFoundError("User", str(user_id))
            logfire.info("User found", user_id=str(user_id), handle=user.handle.root)
            return user

    async def get_user_by_handle(self, handle: Handle) -> User | None:
        """Get user by handle.

        Args:
            handle: User handle

        Returns:
            User if found, None otherwise
        """
        with logfire.span("user_service.get_user_by_handle", handle=handle.root):
            user = await self.user_repository.find_by_handle(handle)
            if user:
                logfire.info("User found", handle=handle.root, user_id=str(user.id))
            else:
                logfire.warn("User not found", handle=handle.root)
            return user

    async def get_user_by_email(self, email: str) -> User | None:
        """Get user by email.

        Args:
            email: User email

        Returns:
            User if found, None otherwise
        """
        with logfire.span("user_service.get_user_by_email", email=email):
            user = await self.user_repository.find_by_email(email)
            if user:
                logfire.info("User found", email=email, user_id=str(user.id))
            else:
                logfire.warn("User not found", email=email)
            return user

    async def get_user_by_provider_identity(
        self, provider: AuthProvider, provider_user_id: str
    ) -> User | None:
        """Get user by provider identity.

        Args:
            provider: Authentication provider
            provider_user_id: Provider-specific user ID

        Returns:
            User if found, None otherwise
        """
        with logfire.span(
            "user_service.get_user_by_provider_identity",
            provider=provider.value,
            provider_user_id=provider_user_id,
        ):
            user = await self.user_repository.find_by_provider_identity(
                provider, provider_user_id
            )
            if user:
                logfire.info(
                    "User found",
                    provider=provider.value,
                    provider_user_id=provider_user_id,
                    user_id=str(user.id),
                )
            else:
                logfire.warn(
                    "User not found",
                    provider=provider.value,
                    provider_user_id=provider_user_id,
                )
            return user

    async def increment_karma(self, user_id: UserId) -> None:
        """Atomically increment user's karma by 1.

        Called when someone upvotes the user's post or comment.
        Uses atomic database operation to avoid race conditions.

        Args:
            user_id: User ID
        """
        with logfire.span("user_service.increment_karma", user_id=str(user_id)):
            await self.user_repository.increment_karma(user_id)
            logfire.info("Karma incremented", user_id=str(user_id))

    async def decrement_karma(self, user_id: UserId) -> None:
        """Atomically decrement user's karma by 1.

        Called when someone removes their upvote from the user's post or comment.
        Uses atomic database operation to avoid race conditions.

        Args:
            user_id: User ID
        """
        with logfire.span("user_service.decrement_karma", user_id=str(user_id)):
            await self.user_repository.decrement_karma(user_id)
            logfire.info("Karma decremented", user_id=str(user_id))

    async def save(self, user: User) -> User:
        """Save user (create or update).

        Args:
            user: User to save

        Returns:
            Saved user
        """
        with logfire.span(
            "user_service.save", user_id=str(user.id), handle=user.handle.root
        ):
            saved = await self.user_repository.save(user)
            logfire.info("User saved", user_id=str(saved.id), handle=saved.handle.root)
            return saved

    async def build_invitation_tree(
        self, include_karma: bool = True
    ) -> list[UserTreeNode]:
        """Build the user invitation tree.

        Creates a hierarchical tree structure showing who invited whom.
        Users without a parent (root users) appear at the top level.

        Algorithm:
        1. Fetch all users (minimal data: id, handle, karma)
        2. Fetch all accepted invite relationships (parent->child pairs)
        3. Build adjacency map of parent_id -> [child_ids]
        4. Identify root users (users with no parent)
        5. Recursively build tree from each root, sorting children by karma

        Args:
            include_karma: Whether to fetch and include karma (default: True).
                          Can be disabled for better performance if karma not needed.

        Returns:
            List of root UserTreeNode objects with children populated recursively.
            Children at each level are sorted by karma (descending).
        """
        with logfire.span("user_service.build_invitation_tree"):
            # Fetch all users (optimized query with minimal fields)
            users_data = await self.user_repository.find_all_for_tree(
                include_karma=include_karma
            )
            logfire.info("Fetched users for tree", count=len(users_data))

            # Fetch all accepted invite relationships
            relationships = (
                await self.invite_repository.find_all_accepted_relationships()
            )
            logfire.info("Fetched invite relationships", count=len(relationships))

            # Build user lookup map: user_id -> (handle, karma)
            user_map: dict[UserId, tuple[Handle, int | None]] = {
                user_id: (handle, karma) for user_id, handle, karma in users_data
            }

            # Build adjacency map: parent_id -> [child_ids]
            adjacency: dict[UserId, list[UserId]] = defaultdict(list)
            for parent_id, child_id in relationships:
                adjacency[parent_id].append(child_id)

            # Identify root users (users with no parent in relationships)
            all_children = {child_id for _, child_id in relationships}
            roots = [
                user_id for user_id, _, _ in users_data if user_id not in all_children
            ]

            logfire.info("Identified root users", count=len(roots))

            # Recursively build tree from each root
            def build_subtree(user_id: UserId) -> UserTreeNode:
                """Build tree recursively from a user node."""
                handle, karma = user_map[user_id]

                # Get children and recursively build their subtrees
                child_ids = adjacency.get(user_id, [])
                children = [build_subtree(child_id) for child_id in child_ids]

                # Sort children by karma (descending), handle as tiebreaker
                # Users without karma (None) sort to the end
                children.sort(
                    key=lambda node: (
                        node.karma if node.karma is not None else -1,
                        node.handle.root,
                    ),
                    reverse=True,
                )

                return UserTreeNode(
                    user_id=user_id,
                    handle=handle,
                    karma=karma,
                    children=children,
                )

            # Build tree from all roots
            tree_roots = [build_subtree(root_id) for root_id in roots]

            # Sort roots by karma as well
            tree_roots.sort(
                key=lambda node: (
                    node.karma if node.karma is not None else -1,
                    node.handle.root,
                ),
                reverse=True,
            )

            logfire.info("Built invitation tree", root_count=len(tree_roots))
            return tree_roots
