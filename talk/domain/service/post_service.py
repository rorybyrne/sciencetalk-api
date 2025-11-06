"""Post domain service."""

import logfire
from datetime import datetime

from talk.domain.model.post import Post
from talk.domain.repository import PostRepository
from talk.domain.value import PostId

from .base import Service


class PostService(Service):
    """Domain service for post operations."""

    def __init__(self, post_repository: PostRepository) -> None:
        """Initialize post service.

        Args:
            post_repository: Post repository
        """
        self.post_repository = post_repository

    async def save_post(self, post: Post) -> Post:
        """Save a post.

        Args:
            post: Post to save

        Returns:
            Saved post
        """
        with logfire.span(
            "post_service.save_post", post_id=str(post.id), title=post.title
        ):
            saved = await self.post_repository.save(post)
            logfire.info("Post saved", post_id=str(saved.id))
            return saved

    async def get_post_by_id(self, post_id: PostId) -> Post | None:
        """Get a post by ID.

        Args:
            post_id: Post ID

        Returns:
            Post if found, None otherwise
        """
        with logfire.span("post_service.get_post_by_id", post_id=str(post_id)):
            post = await self.post_repository.find_by_id(post_id)

            if post:
                logfire.info("Post found", post_id=str(post_id), title=post.title)
            else:
                logfire.warn("Post not found", post_id=str(post_id))

            return post

    async def increment_comment_count(self, post_id: PostId) -> Post:
        """Increment a post's comment count.

        Args:
            post_id: Post ID

        Returns:
            Updated post

        Raises:
            ValueError: If post not found
        """
        with logfire.span("post_service.increment_comment_count", post_id=str(post_id)):
            post = await self.post_repository.find_by_id(post_id)
            if not post:
                logfire.error(
                    "Post not found for comment count increment", post_id=str(post_id)
                )
                raise ValueError("Post not found")

            # Update comment count (domain models are immutable)
            updated_post = post.model_copy(
                update={
                    "comment_count": post.comment_count + 1,
                    "updated_at": datetime.now(),
                }
            )

            saved = await self.post_repository.save(updated_post)
            logfire.info(
                "Comment count incremented",
                post_id=str(post_id),
                new_count=saved.comment_count,
            )
            return saved

    async def increment_points(self, post_id: PostId) -> None:
        """Atomically increment post points.

        Uses SQL-level increment to avoid race conditions.

        Args:
            post_id: Post ID
        """
        with logfire.span("post_service.increment_points", post_id=str(post_id)):
            await self.post_repository.increment_points(post_id)
            logfire.info("Post points incremented", post_id=str(post_id))

    async def decrement_points(self, post_id: PostId) -> None:
        """Atomically decrement post points (minimum 1).

        Uses SQL-level decrement to avoid race conditions.

        Args:
            post_id: Post ID
        """
        with logfire.span("post_service.decrement_points", post_id=str(post_id)):
            await self.post_repository.decrement_points(post_id)
            logfire.info("Post points decremented", post_id=str(post_id))

    async def update_text(self, post_id: PostId, text: str | None) -> Post | None:
        """Update the text content of a post.

        Args:
            post_id: Post ID
            text: New text content (None to clear)

        Returns:
            Updated post if found and updated, None if post doesn't exist or is deleted
        """
        with logfire.span(
            "post_service.update_text",
            post_id=str(post_id),
            text_length=len(text) if text else 0,
            clearing_text=text is None,
        ):
            updated = await self.post_repository.update_text(post_id, text)

            if updated:
                logfire.info(
                    "Post text updated",
                    post_id=str(post_id),
                    title=updated.title,
                    text_length=len(updated.text) if updated.text else 0,
                )
            else:
                logfire.warn(
                    "Post not found or deleted for text update", post_id=str(post_id)
                )

            return updated
