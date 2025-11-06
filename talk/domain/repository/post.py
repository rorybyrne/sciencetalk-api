"""Post repository interface."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional

from talk.domain.model.post import Post
from talk.domain.value import PostId, UserId
from talk.domain.value.types import TagName


class PostSortOrder(str, Enum):
    """Sort order for post listings."""

    RECENT = "recent"  # Sort by created_at DESC
    ACTIVE = "active"  # Sort by most recent comment activity


class PostRepository(ABC):
    """Repository for Post aggregate.

    Defines the contract for post persistence operations.
    Implementations live in the infrastructure layer.
    """

    @abstractmethod
    async def find_by_id(self, post_id: PostId) -> Optional[Post]:
        """Find a post by ID.

        Args:
            post_id: The post's unique identifier

        Returns:
            The post if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_all(
        self,
        sort: PostSortOrder = PostSortOrder.RECENT,
        tag: Optional[TagName] = None,
        include_deleted: bool = False,
        limit: int = 30,
        offset: int = 0,
    ) -> List[Post]:
        """Find posts with filtering and pagination.

        Args:
            sort: Sort order (recent or active)
            tag: Filter by tag name (None for all tags)
            include_deleted: Whether to include soft-deleted posts
            limit: Maximum number of posts to return
            offset: Number of posts to skip

        Returns:
            List of posts matching the criteria
        """
        pass

    @abstractmethod
    async def count(
        self,
        tag: Optional[TagName] = None,
        include_deleted: bool = False,
    ) -> int:
        """Count posts matching the given filters.

        Args:
            tag: Filter by tag name (None for all tags)
            include_deleted: Whether to include soft-deleted posts

        Returns:
            Total number of posts matching the criteria
        """
        pass

    @abstractmethod
    async def find_by_author(
        self,
        author_id: UserId,
        include_deleted: bool = False,
        limit: int = 30,
        offset: int = 0,
    ) -> List[Post]:
        """Find posts by a specific author.

        Args:
            author_id: The author's user ID
            include_deleted: Whether to include soft-deleted posts
            limit: Maximum number of posts to return
            offset: Number of posts to skip

        Returns:
            List of posts by the author
        """
        pass

    @abstractmethod
    async def save(self, post: Post) -> Post:
        """Save a post (create or update).

        Args:
            post: The post to save

        Returns:
            The saved post
        """
        pass

    @abstractmethod
    async def delete(self, post_id: PostId) -> None:
        """Delete a post (hard delete).

        Note: In practice, we use soft deletes via Post.soft_delete()
        This is here for completeness but may not be used.

        Args:
            post_id: The post ID to delete
        """
        pass

    @abstractmethod
    async def increment_points(self, post_id: PostId) -> None:
        """Atomically increment points by 1.

        Uses SQL-level increment to avoid race conditions.

        Args:
            post_id: The post ID
        """
        pass

    @abstractmethod
    async def decrement_points(self, post_id: PostId) -> None:
        """Atomically decrement points by 1 (minimum 1).

        Uses SQL-level decrement to avoid race conditions.
        Will not decrement below 1 (business rule).

        Args:
            post_id: The post ID
        """
        pass

    @abstractmethod
    async def update_text(self, post_id: PostId, text: str | None) -> Optional[Post]:
        """Update the text content of a post.

        Args:
            post_id: ID of the post to update
            text: New text content (None to clear)

        Returns:
            Updated Post entity, or None if post doesn't exist or is deleted
        """
        pass
