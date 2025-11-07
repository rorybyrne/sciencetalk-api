"""Unit tests for PostService."""

from datetime import datetime
from uuid import uuid4

import pytest

from talk.domain.model.post import Post
from talk.domain.service import PostService
from talk.domain.value import PostId, UserId
from talk.domain.value.types import Handle, TagName
from talk.persistence.repository.post import PostRepository
from tests.conftest import make_slug
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
            slug=make_slug("Test Post", post_id),
            tag_names=[TagName("discussion")],
            author_id=UserId(uuid4()),
            author_handle=Handle(root="author.bsky.social"),
            title="Test Post",
            url=None,
            text="Test content",
            points=1,
            comment_count=5,
            created_at=original_time,
            comments_updated_at=original_time,
            content_updated_at=original_time,
            deleted_at=None,
        )
        await post_repo.save(post)

        # Act
        result = await post_service.increment_comment_count(post_id)

        # Assert
        assert result.comment_count == 6
        assert result.comments_updated_at > original_time

        # Verify it was saved
        saved_post = await post_repo.find_by_id(post_id)
        assert saved_post.comment_count == 6
        assert saved_post.comments_updated_at > original_time

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


class TestUpdateText:
    """Tests for update_text method."""

    @pytest.mark.asyncio
    async def test_update_text_updates_post_text(self, unit_env):
        """Updating text should update post text and timestamp."""
        # Arrange
        post_service = await unit_env.get(PostService)
        post_repo = await unit_env.get(PostRepository)

        post_id = PostId(uuid4())
        original_time = datetime(2024, 1, 1, 12, 0, 0)
        original_text = "Original content"
        new_text = "Updated content"

        post = Post(
            id=post_id,
            slug=make_slug("Test Post", post_id),
            tag_names=[TagName("discussion")],
            author_id=UserId(uuid4()),
            author_handle=Handle(root="author.bsky.social"),
            title="Test Post",
            url=None,
            text=original_text,
            points=1,
            comment_count=0,
            created_at=original_time,
            comments_updated_at=original_time,
            content_updated_at=original_time,
            deleted_at=None,
        )
        await post_repo.save(post)

        # Act
        result = await post_service.update_text(post_id, new_text)

        # Assert
        assert result is not None
        assert result.text == new_text
        assert result.content_updated_at > original_time

        # Verify it was saved
        saved_post = await post_repo.find_by_id(post_id)
        assert saved_post.text == new_text
        assert saved_post.content_updated_at > original_time

    @pytest.mark.asyncio
    async def test_update_text_returns_none_when_post_not_found(self, unit_env):
        """Updating text for non-existent post should return None."""
        # Arrange
        post_service = await unit_env.get(PostService)
        post_id = PostId(uuid4())

        # Act
        result = await post_service.update_text(post_id, "New text")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_update_text_returns_none_when_post_deleted(self, unit_env):
        """Updating text for deleted post should return None."""
        # Arrange
        post_service = await unit_env.get(PostService)
        post_repo = await unit_env.get(PostRepository)

        post_id = PostId(uuid4())
        now = datetime.now()
        post = Post(
            id=post_id,
            slug=make_slug("Test Post", post_id),
            tag_names=[TagName("discussion")],
            author_id=UserId(uuid4()),
            author_handle=Handle(root="author.bsky.social"),
            title="Test Post",
            url=None,
            text="Original content",
            points=1,
            comment_count=0,
            created_at=now,
            comments_updated_at=now,
            content_updated_at=now,
            deleted_at=now,  # Deleted
        )
        await post_repo.save(post)

        # Act
        result = await post_service.update_text(post_id, "New text")

        # Assert
        assert result is None
