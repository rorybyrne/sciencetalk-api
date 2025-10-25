"""Unit tests for PostService."""

from datetime import datetime
from uuid import uuid4

import pytest

from talk.domain.model.post import Post
from talk.domain.service import PostService
from talk.domain.value import PostId, UserId
from talk.domain.value.types import Handle, PostType
from talk.persistence.repository.post import PostRepository
from tests.harness import create_env_fixture

# Unit test fixture
unit_env = create_env_fixture()


class TestIncrementCommentCount:
    """Tests for increment_comment_count method."""

    @pytest.mark.asyncio
    async def test_increment_comment_count_updates_post(self, unit_env):
        """Incrementing comment count should update count and timestamp."""
        # Arrange
        post_service = await unit_env.get(PostService)
        post_repo = await unit_env.get(PostRepository)

        post_id = PostId(uuid4())
        original_time = datetime(2024, 1, 1, 12, 0, 0)

        post = Post(
            id=post_id,
            type=PostType.DISCUSSION,
            author_id=UserId(uuid4()),
            author_handle=Handle(value="author.bsky.social"),
            title="Test Post",
            url=None,
            text="Test content",
            points=1,
            comment_count=5,
            created_at=original_time,
            updated_at=original_time,
            deleted_at=None,
        )
        await post_repo.save(post)

        # Act
        result = await post_service.increment_comment_count(post_id)

        # Assert
        assert result.comment_count == 6
        assert result.updated_at > original_time

        # Verify it was saved
        saved_post = await post_repo.find_by_id(post_id)
        assert saved_post.comment_count == 6
        assert saved_post.updated_at > original_time

    @pytest.mark.asyncio
    async def test_increment_comment_count_raises_error_when_post_not_found(
        self, unit_env
    ):
        """Incrementing comment count for non-existent post should raise error."""
        # Arrange
        post_service = await unit_env.get(PostService)
        post_id = PostId(uuid4())

        # Act & Assert
        with pytest.raises(ValueError, match="Post not found"):
            await post_service.increment_comment_count(post_id)
