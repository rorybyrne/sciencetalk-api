"""Post domain service."""

import logging
from datetime import datetime

from talk.domain.model.post import Post
from talk.domain.repository import PostRepository
from talk.domain.value import PostId

from .base import Service

logger = logging.getLogger(__name__)


class PostService(Service):
    """Domain service for post operations."""

    def __init__(self, post_repository: PostRepository) -> None:
        """Initialize post service.

        Args:
            post_repository: Post repository
        """
        self.post_repository = post_repository

    async def get_post_by_id(self, post_id: PostId) -> Post | None:
        """Get a post by ID.

        Args:
            post_id: Post ID

        Returns:
            Post if found, None otherwise
        """
        logger.debug(f"Looking up post in repository: post_id={post_id}")
        post = await self.post_repository.find_by_id(post_id)

        if post:
            logger.info(f"Post found: post_id={post_id}, title='{post.title}'")
        else:
            logger.warning(f"Post not found in repository: post_id={post_id}")

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
        post = await self.post_repository.find_by_id(post_id)
        if not post:
            raise ValueError("Post not found")

        # Update comment count (domain models are immutable)
        updated_post = post.model_copy(
            update={
                "comment_count": post.comment_count + 1,
                "updated_at": datetime.now(),
            }
        )

        return await self.post_repository.save(updated_post)

    async def increment_points(self, post_id: PostId) -> None:
        """Atomically increment post points.

        Uses SQL-level increment to avoid race conditions.

        Args:
            post_id: Post ID
        """
        await self.post_repository.increment_points(post_id)

    async def decrement_points(self, post_id: PostId) -> None:
        """Atomically decrement post points (minimum 1).

        Uses SQL-level decrement to avoid race conditions.

        Args:
            post_id: Post ID
        """
        await self.post_repository.decrement_points(post_id)
