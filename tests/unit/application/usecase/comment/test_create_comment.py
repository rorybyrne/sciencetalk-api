"""Unit tests for CreateCommentUseCase."""

from datetime import datetime
from uuid import uuid4

import pytest

from talk.application.usecase.comment.create_comment import (
    CreateCommentRequest,
    CreateCommentUseCase,
)
from talk.domain.model.post import Post
from talk.domain.service import CommentService, PostService
from talk.domain.value import PostId, UserId
from talk.domain.value.types import Handle, PostType
from talk.persistence.repository.post import PostRepository
from tests.harness import create_env_fixture

# Unit test fixture
unit_env = create_env_fixture()


class TestCreateCommentUseCase:
    """Tests for CreateCommentUseCase."""

    @pytest.mark.asyncio
    async def test_create_comment_increments_post_count(self, unit_env):
        """Creating comment should increment post comment count."""
        # Arrange
        comment_service = await unit_env.get(CommentService)
        post_service = await unit_env.get(PostService)
        post_repo = await unit_env.get(PostRepository)

        create_comment_use_case = CreateCommentUseCase(
            comment_service=comment_service,
            post_service=post_service,
        )

        post_id = PostId(uuid4())
        author_id = UserId(uuid4())
        author_handle = "user.bsky.social"
        text = "Test comment"

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
            created_at=datetime.now(),
            updated_at=datetime.now(),
            deleted_at=None,
        )
        await post_repo.save(post)

        request = CreateCommentRequest(
            post_id=str(post_id),
            text=text,
            author_id=str(author_id),
            author_handle=author_handle,
            parent_id=None,
        )

        # Act
        response = await create_comment_use_case.execute(request)

        # Assert
        assert response.comment_id is not None
        assert response.post_id == str(post_id)

        # Verify post comment count was incremented
        updated_post = await post_repo.find_by_id(post_id)
        assert updated_post.comment_count == 6

    @pytest.mark.asyncio
    async def test_create_comment_with_nonexistent_post_raises_error(self, unit_env):
        """Creating comment for non-existent post should raise error."""
        # Arrange
        comment_service = await unit_env.get(CommentService)
        post_service = await unit_env.get(PostService)

        create_comment_use_case = CreateCommentUseCase(
            comment_service=comment_service,
            post_service=post_service,
        )

        post_id = PostId(uuid4())

        request = CreateCommentRequest(
            post_id=str(post_id),
            text="Test comment",
            author_id=str(uuid4()),
            author_handle="user.bsky.social",
            parent_id=None,
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Post not found"):
            await create_comment_use_case.execute(request)
