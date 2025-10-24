"""Comment repository interface."""

from abc import ABC, abstractmethod
from typing import List, Optional

from talk.domain.model.comment import Comment
from talk.domain.value import CommentId, PostId, UserId


class CommentRepository(ABC):
    """Repository for Comment entity.

    Defines the contract for comment persistence operations.
    Implementations live in the infrastructure layer.
    """

    @abstractmethod
    async def find_by_id(self, comment_id: CommentId) -> Optional[Comment]:
        """Find a comment by ID.

        Args:
            comment_id: The comment's unique identifier

        Returns:
            The comment if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_by_post(
        self,
        post_id: PostId,
        include_deleted: bool = False,
    ) -> List[Comment]:
        """Find all comments for a post in tree order.

        Comments should be returned in tree order (using ltree path)
        for efficient rendering of threaded discussions.

        Args:
            post_id: The post ID
            include_deleted: Whether to include soft-deleted comments

        Returns:
            List of comments in tree order
        """
        pass

    @abstractmethod
    async def find_by_author(
        self,
        author_id: UserId,
        include_deleted: bool = False,
        limit: int = 30,
        offset: int = 0,
    ) -> List[Comment]:
        """Find comments by a specific author.

        Args:
            author_id: The author's user ID
            include_deleted: Whether to include soft-deleted comments
            limit: Maximum number of comments to return
            offset: Number of comments to skip

        Returns:
            List of comments by the author
        """
        pass

    @abstractmethod
    async def find_children(
        self,
        parent_id: CommentId,
        include_deleted: bool = False,
    ) -> List[Comment]:
        """Find direct child comments of a parent comment.

        Args:
            parent_id: The parent comment ID
            include_deleted: Whether to include soft-deleted comments

        Returns:
            List of child comments
        """
        pass

    @abstractmethod
    async def save(self, comment: Comment) -> Comment:
        """Save a comment (create or update).

        When creating a new comment, the database trigger will
        automatically set the path and depth based on parent_id.

        Args:
            comment: The comment to save

        Returns:
            The saved comment (with path and depth populated)
        """
        pass

    @abstractmethod
    async def delete(self, comment_id: CommentId) -> None:
        """Delete a comment (hard delete).

        Note: In practice, we use soft deletes via Comment.soft_delete()
        This is here for completeness but may not be used.

        Args:
            comment_id: The comment ID to delete
        """
        pass

    @abstractmethod
    async def count_by_post(self, post_id: PostId) -> int:
        """Count comments for a post (excluding deleted).

        Args:
            post_id: The post ID

        Returns:
            Number of comments
        """
        pass
