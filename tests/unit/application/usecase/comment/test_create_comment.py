"""Unit tests for CreateCommentUseCase."""

from datetime import datetime
from uuid import uuid4

import pytest

from talk.application.usecase.comment.create_comment import (
    CreateCommentRequest,
    CreateCommentUseCase,
)
from talk.domain.model.post import Post
from talk.domain.model.user import User
from talk.domain.service import CommentService, PostService, UserService
from talk.domain.value import PostId, UserId
from talk.domain.value.types import Handle, TagName
from talk.persistence.repository.post import PostRepository
from talk.persistence.repository.user import UserRepository
from tests.conftest import make_slug
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
        user_service = await unit_env.get(UserService)
        post_repo = await unit_env.get(PostRepository)
        user_repo = await unit_env.get(UserRepository)

        create_comment_use_case = CreateCommentUseCase(
            comment_service=comment_service,
            post_service=post_service,
            user_service=user_service,
        )

        post_id = PostId(uuid4())
        author_id = UserId(uuid4())
        author_handle = Handle(root="user.bsky.social")
        text = "Test comment"

        # Create and save user
        user = User(
            id=author_id,
            handle=author_handle,
            email=None,
            karma=0,
            bio=None,
            created_at=datetime.now(),
        )
        await user_repo.save(user)

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
            created_at=datetime.now(),
            comments_updated_at=datetime.now(),
            content_updated_at=datetime.now(),
            deleted_at=None,
        )
        await post_repo.save(post)

        request = CreateCommentRequest(
            post_id=str(post_id),
            text=text,
            author_id=str(author_id),
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
        user_service = await unit_env.get(UserService)
        user_repo = await unit_env.get(UserRepository)

        create_comment_use_case = CreateCommentUseCase(
            comment_service=comment_service,
            post_service=post_service,
            user_service=user_service,
        )

        post_id = PostId(uuid4())
        author_id = UserId(uuid4())
        author_handle = Handle(root="user.bsky.social")

        # Create and save user
        user = User(
            id=author_id,
            handle=author_handle,
            email=None,
            karma=0,
            bio=None,
            created_at=datetime.now(),
        )
        await user_repo.save(user)

        request = CreateCommentRequest(
            post_id=str(post_id),
            text="Test comment",
            author_id=str(author_id),
            parent_id=None,
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Post not found"):
            await create_comment_use_case.execute(request)
