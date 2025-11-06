"""Unit tests for UpdatePostUseCase."""

from datetime import datetime
from uuid import uuid4

import pytest

from talk.application.usecase.post.update_post import (
    UpdatePostRequest,
    UpdatePostUseCase,
)
from talk.domain.error import (
    ContentDeletedException,
    InvalidEditOperationError,
    NotAuthorizedError,
)
from talk.domain.model.post import Post
from talk.domain.service import PostService
from talk.domain.value import PostId, UserId
from talk.domain.value.types import Handle, TagName
from talk.persistence.repository.post import PostRepository
from talk.persistence.repository.vote import VoteRepository
from tests.harness import create_env_fixture

# Unit test fixture
unit_env = create_env_fixture()


class TestUpdatePostUseCase:
    """Tests for UpdatePostUseCase."""

    @pytest.mark.asyncio
    async def test_update_post_text_success(self, unit_env):
        """Updating post text by author should succeed."""
        # Arrange
        post_service = await unit_env.get(PostService)
        post_repo = await unit_env.get(PostRepository)
        vote_repo = await unit_env.get(VoteRepository)

        use_case = UpdatePostUseCase(
            post_service=post_service,
            vote_repository=vote_repo,
        )

        post_id = PostId(uuid4())
        author_id = UserId(uuid4())

        post = Post(
            id=post_id,
            tag_names=[TagName("discussion")],
            author_id=author_id,
            author_handle=Handle(root="author.bsky.social"),
            title="Test Post",
            url=None,
            text="Original content",
            points=1,
            comment_count=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            deleted_at=None,
        )
        await post_repo.save(post)

        request = UpdatePostRequest(
            post_id=str(post_id),
            user_id=str(author_id),
            text="Updated content",
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.post_id == str(post_id)
        assert response.text == "Updated content"

        # Verify it was saved
        saved_post = await post_repo.find_by_id(post_id)
        assert saved_post.text == "Updated content"

    @pytest.mark.asyncio
    async def test_update_post_not_authorized_when_not_author(self, unit_env):
        """Updating post by non-author should raise NotAuthorizedError."""
        # Arrange
        post_service = await unit_env.get(PostService)
        post_repo = await unit_env.get(PostRepository)
        vote_repo = await unit_env.get(VoteRepository)

        use_case = UpdatePostUseCase(
            post_service=post_service,
            vote_repository=vote_repo,
        )

        post_id = PostId(uuid4())
        author_id = UserId(uuid4())
        different_user_id = UserId(uuid4())

        post = Post(
            id=post_id,
            tag_names=[TagName("discussion")],
            author_id=author_id,
            author_handle=Handle(root="author.bsky.social"),
            title="Test Post",
            url=None,
            text="Original content",
            points=1,
            comment_count=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            deleted_at=None,
        )
        await post_repo.save(post)

        request = UpdatePostRequest(
            post_id=str(post_id),
            user_id=str(different_user_id),  # Different user
            text="Hacked content",
        )

        # Act & Assert
        with pytest.raises(NotAuthorizedError):
            await use_case.execute(request)

    @pytest.mark.asyncio
    async def test_update_post_fails_when_post_deleted(self, unit_env):
        """Updating deleted post should raise ContentDeletedException."""
        # Arrange
        post_service = await unit_env.get(PostService)
        post_repo = await unit_env.get(PostRepository)
        vote_repo = await unit_env.get(VoteRepository)

        use_case = UpdatePostUseCase(
            post_service=post_service,
            vote_repository=vote_repo,
        )

        post_id = PostId(uuid4())
        author_id = UserId(uuid4())

        post = Post(
            id=post_id,
            tag_names=[TagName("discussion")],
            author_id=author_id,
            author_handle=Handle(root="author.bsky.social"),
            title="Test Post",
            url=None,
            text="Original content",
            points=1,
            comment_count=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            deleted_at=datetime.now(),  # Deleted
        )
        await post_repo.save(post)

        request = UpdatePostRequest(
            post_id=str(post_id),
            user_id=str(author_id),
            text="Updated content",
        )

        # Act & Assert
        with pytest.raises(ContentDeletedException):
            await use_case.execute(request)

    @pytest.mark.asyncio
    async def test_update_post_fails_when_url_based_post(self, unit_env):
        """Updating text on URL-based post should raise InvalidEditOperationError."""
        # Arrange
        post_service = await unit_env.get(PostService)
        post_repo = await unit_env.get(PostRepository)
        vote_repo = await unit_env.get(VoteRepository)

        use_case = UpdatePostUseCase(
            post_service=post_service,
            vote_repository=vote_repo,
        )

        post_id = PostId(uuid4())
        author_id = UserId(uuid4())

        post = Post(
            id=post_id,
            tag_names=[TagName("result")],
            author_id=author_id,
            author_handle=Handle(root="author.bsky.social"),
            title="Research Paper",
            url="https://example.com/paper.pdf",  # URL-based post
            text=None,
            points=1,
            comment_count=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            deleted_at=None,
        )
        await post_repo.save(post)

        request = UpdatePostRequest(
            post_id=str(post_id),
            user_id=str(author_id),
            text="Adding text to URL post",
        )

        # Act & Assert
        with pytest.raises(InvalidEditOperationError, match="Cannot edit text"):
            await use_case.execute(request)

    @pytest.mark.asyncio
    async def test_update_post_fails_when_post_not_found(self, unit_env):
        """Updating non-existent post should raise ValueError."""
        # Arrange
        post_service = await unit_env.get(PostService)
        vote_repo = await unit_env.get(VoteRepository)

        use_case = UpdatePostUseCase(
            post_service=post_service,
            vote_repository=vote_repo,
        )

        request = UpdatePostRequest(
            post_id=str(uuid4()),
            user_id=str(uuid4()),
            text="New text",
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Post not found"):
            await use_case.execute(request)
