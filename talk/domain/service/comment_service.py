"""Comment domain service."""

import logfire
from datetime import datetime
from uuid import uuid4

from talk.domain.model.comment import Comment
from talk.domain.repository import CommentRepository
from talk.domain.value import CommentId, PostId, UserId
from talk.domain.value.types import Handle

from .base import Service


class CommentService(Service):
    """Domain service for comment operations."""

    def __init__(self, comment_repository: CommentRepository) -> None:
        """Initialize comment service.

        Args:
            comment_repository: Comment repository
        """
        self.comment_repository = comment_repository

    async def create_comment(
        self,
        post_id: PostId,
        author_id: UserId,
        author_handle: Handle,
        text: str,
        parent_id: CommentId | None = None,
    ) -> Comment:
        """Create a comment on a post or reply to another comment.

        Args:
            post_id: Post ID
            author_id: Author user ID
            author_handle: Author handle
            text: Comment text
            parent_id: Parent comment ID for replies (None for top-level)

        Returns:
            Created comment (with path and depth set by database)

        Raises:
            ValueError: If parent comment invalid
        """
        with logfire.span(
            "comment_service.create_comment",
            post_id=str(post_id),
            author_id=str(author_id),
            author_handle=author_handle.root,
            parent_id=str(parent_id) if parent_id else None,
        ):
            # If replying, verify parent exists and calculate depth
            depth = 0
            if parent_id:
                parent = await self.comment_repository.find_by_id(parent_id)
                if not parent:
                    logfire.error(
                        "Parent comment not found",
                        parent_id=str(parent_id),
                        post_id=str(post_id),
                    )
                    raise ValueError("Parent comment not found")
                if parent.post_id != post_id:
                    logfire.error(
                        "Parent comment does not belong to post",
                        parent_id=str(parent_id),
                        parent_post_id=str(parent.post_id),
                        target_post_id=str(post_id),
                    )
                    raise ValueError("Parent comment does not belong to this post")
                depth = parent.depth + 1

            # Create comment
            comment = Comment(
                id=CommentId(uuid4()),
                post_id=post_id,
                author_id=author_id,
                author_handle=author_handle,
                text=text,
                parent_id=parent_id,
                depth=depth,
                path=None,  # Set by database trigger
                points=1,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                deleted_at=None,
            )

            saved = await self.comment_repository.save(comment)
            logfire.info(
                "Comment created",
                comment_id=str(saved.id),
                post_id=str(post_id),
                author_handle=author_handle.root,
                depth=depth,
            )
            return saved

    async def get_comments_for_post(
        self, post_id: PostId, include_deleted: bool = False
    ) -> list[Comment]:
        """Get all comments for a post in tree order.

        Args:
            post_id: Post ID
            include_deleted: Whether to include deleted comments

        Returns:
            List of comments in tree order
        """
        with logfire.span(
            "comment_service.get_comments_for_post",
            post_id=str(post_id),
            include_deleted=include_deleted,
        ):
            comments = await self.comment_repository.find_by_post(
                post_id=post_id,
                include_deleted=include_deleted,
            )
            logfire.info(
                "Comments retrieved for post",
                post_id=str(post_id),
                count=len(comments),
            )
            return comments

    async def get_comment_by_id(self, comment_id: CommentId) -> Comment | None:
        """Get a comment by ID.

        Args:
            comment_id: Comment ID

        Returns:
            Comment if found, None otherwise
        """
        with logfire.span(
            "comment_service.get_comment_by_id", comment_id=str(comment_id)
        ):
            comment = await self.comment_repository.find_by_id(comment_id)
            if comment:
                logfire.info("Comment found", comment_id=str(comment_id))
            else:
                logfire.warn("Comment not found", comment_id=str(comment_id))
            return comment

    async def increment_points(self, comment_id: CommentId) -> None:
        """Atomically increment comment points.

        Uses SQL-level increment to avoid race conditions.

        Args:
            comment_id: Comment ID
        """
        with logfire.span(
            "comment_service.increment_points", comment_id=str(comment_id)
        ):
            await self.comment_repository.increment_points(comment_id)
            logfire.info("Comment points incremented", comment_id=str(comment_id))

    async def decrement_points(self, comment_id: CommentId) -> None:
        """Atomically decrement comment points (minimum 1).

        Uses SQL-level decrement to avoid race conditions.

        Args:
            comment_id: Comment ID
        """
        with logfire.span(
            "comment_service.decrement_points", comment_id=str(comment_id)
        ):
            await self.comment_repository.decrement_points(comment_id)
            logfire.info("Comment points decremented", comment_id=str(comment_id))

    async def update_text(self, comment_id: CommentId, text: str) -> Comment | None:
        """Update the text content of a comment.

        Args:
            comment_id: Comment ID
            text: New text content

        Returns:
            Updated comment if found and updated, None if comment doesn't exist or is deleted
        """
        with logfire.span(
            "comment_service.update_text",
            comment_id=str(comment_id),
            text_length=len(text),
        ):
            updated = await self.comment_repository.update_text(comment_id, text)

            if updated:
                logfire.info(
                    "Comment text updated",
                    comment_id=str(comment_id),
                    post_id=str(updated.post_id),
                    text_length=len(updated.text),
                    depth=updated.depth,
                )
            else:
                logfire.warn(
                    "Comment not found or deleted for text update",
                    comment_id=str(comment_id),
                )

            return updated
