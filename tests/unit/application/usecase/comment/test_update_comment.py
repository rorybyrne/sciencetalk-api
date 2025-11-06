"""Unit tests for UpdateCommentUseCase."""

from datetime import datetime
from uuid import uuid4

import pytest

from talk.application.usecase.comment.update_comment import (
    UpdateCommentRequest,
    UpdateCommentUseCase,
)
from talk.domain.error import (
    ContentDeletedException,
    NotAuthorizedError,
)
from talk.domain.model.comment import Comment
from talk.domain.model.post import Post
from talk.domain.service import CommentService, PostService
from talk.domain.value import CommentId, PostId, UserId
from talk.domain.value.types import Handle, TagName
from talk.persistence.repository.comment import CommentRepository
from talk.persistence.repository.post import PostRepository
from talk.persistence.repository.vote import VoteRepository
from tests.harness import create_env_fixture

# Unit test fixture
unit_env = create_env_fixture()


class TestUpdateCommentUseCase:
    """Tests for UpdateCommentUseCase."""

    @pytest.mark.asyncio
    async def test_update_comment_text_success(self, unit_env):
        """Updating comment text by author should succeed."""
        # Arrange
        comment_service = await unit_env.get(CommentService)
        post_service = await unit_env.get(PostService)
        comment_repo = await unit_env.get(CommentRepository)
        post_repo = await unit_env.get(PostRepository)
        vote_repo = await unit_env.get(VoteRepository)

        use_case = UpdateCommentUseCase(
            comment_service=comment_service,
            post_service=post_service,
            vote_repository=vote_repo,
        )

        post_id = PostId(uuid4())
        comment_id = CommentId(uuid4())
        author_id = UserId(uuid4())

        # Create post
        post = Post(
            id=post_id,
            tag_names=[TagName("discussion")],
            author_id=UserId(uuid4()),
            author_handle=Handle(root="post_author.bsky.social"),
            title="Test Post",
            url=None,
            text="Post content",
            points=1,
            comment_count=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            deleted_at=None,
        )
        await post_repo.save(post)

        # Create comment
        comment = Comment(
            id=comment_id,
            post_id=post_id,
            author_id=author_id,
            author_handle=Handle(root="comment_author.bsky.social"),
            text="Original comment",
            parent_id=None,
            depth=0,
            path="1",
            points=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            deleted_at=None,
        )
        await comment_repo.save(comment)

        request = UpdateCommentRequest(
            post_id=str(post_id),
            comment_id=str(comment_id),
            user_id=str(author_id),
            text="Updated comment",
        )

        # Act
        response = await use_case.execute(request)

        # Assert
        assert response.comment_id == str(comment_id)
        assert response.text == "Updated comment"

        # Verify it was saved
        saved_comment = await comment_repo.find_by_id(comment_id)
        assert saved_comment.text == "Updated comment"

    @pytest.mark.asyncio
    async def test_update_comment_not_authorized_when_not_author(self, unit_env):
        """Updating comment by non-author should raise NotAuthorizedError."""
        # Arrange
        comment_service = await unit_env.get(CommentService)
        post_service = await unit_env.get(PostService)
        comment_repo = await unit_env.get(CommentRepository)
        post_repo = await unit_env.get(PostRepository)
        vote_repo = await unit_env.get(VoteRepository)

        use_case = UpdateCommentUseCase(
            comment_service=comment_service,
            post_service=post_service,
            vote_repository=vote_repo,
        )

        post_id = PostId(uuid4())
        comment_id = CommentId(uuid4())
        author_id = UserId(uuid4())
        different_user_id = UserId(uuid4())

        # Create post
        post = Post(
            id=post_id,
            tag_names=[TagName("discussion")],
            author_id=UserId(uuid4()),
            author_handle=Handle(root="post_author.bsky.social"),
            title="Test Post",
            url=None,
            text="Post content",
            points=1,
            comment_count=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            deleted_at=None,
        )
        await post_repo.save(post)

        # Create comment
        comment = Comment(
            id=comment_id,
            post_id=post_id,
            author_id=author_id,
            author_handle=Handle(root="comment_author.bsky.social"),
            text="Original comment",
            parent_id=None,
            depth=0,
            path="1",
            points=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            deleted_at=None,
        )
        await comment_repo.save(comment)

        request = UpdateCommentRequest(
            post_id=str(post_id),
            comment_id=str(comment_id),
            user_id=str(different_user_id),  # Different user
            text="Hacked comment",
        )

        # Act & Assert
        with pytest.raises(NotAuthorizedError):
            await use_case.execute(request)

    @pytest.mark.asyncio
    async def test_update_comment_fails_when_comment_deleted(self, unit_env):
        """Updating deleted comment should raise ContentDeletedException."""
        # Arrange
        comment_service = await unit_env.get(CommentService)
        post_service = await unit_env.get(PostService)
        comment_repo = await unit_env.get(CommentRepository)
        post_repo = await unit_env.get(PostRepository)
        vote_repo = await unit_env.get(VoteRepository)

        use_case = UpdateCommentUseCase(
            comment_service=comment_service,
            post_service=post_service,
            vote_repository=vote_repo,
        )

        post_id = PostId(uuid4())
        comment_id = CommentId(uuid4())
        author_id = UserId(uuid4())

        # Create post
        post = Post(
            id=post_id,
            tag_names=[TagName("discussion")],
            author_id=UserId(uuid4()),
            author_handle=Handle(root="post_author.bsky.social"),
            title="Test Post",
            url=None,
            text="Post content",
            points=1,
            comment_count=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            deleted_at=None,
        )
        await post_repo.save(post)

        # Create deleted comment
        comment = Comment(
            id=comment_id,
            post_id=post_id,
            author_id=author_id,
            author_handle=Handle(root="comment_author.bsky.social"),
            text="Original comment",
            parent_id=None,
            depth=0,
            path="1",
            points=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            deleted_at=datetime.now(),  # Deleted
        )
        await comment_repo.save(comment)

        request = UpdateCommentRequest(
            post_id=str(post_id),
            comment_id=str(comment_id),
            user_id=str(author_id),
            text="Updated comment",
        )

        # Act & Assert
        with pytest.raises(ContentDeletedException):
            await use_case.execute(request)

    @pytest.mark.asyncio
    async def test_update_comment_fails_when_comment_not_found(self, unit_env):
        """Updating non-existent comment should raise ValueError."""
        # Arrange
        comment_service = await unit_env.get(CommentService)
        post_service = await unit_env.get(PostService)
        vote_repo = await unit_env.get(VoteRepository)
        post_repo = await unit_env.get(PostRepository)

        use_case = UpdateCommentUseCase(
            comment_service=comment_service,
            post_service=post_service,
            vote_repository=vote_repo,
        )

        post_id = PostId(uuid4())

        # Create post (but no comment)
        post = Post(
            id=post_id,
            tag_names=[TagName("discussion")],
            author_id=UserId(uuid4()),
            author_handle=Handle(root="post_author.bsky.social"),
            title="Test Post",
            url=None,
            text="Post content",
            points=1,
            comment_count=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            deleted_at=None,
        )
        await post_repo.save(post)

        request = UpdateCommentRequest(
            post_id=str(post_id),
            comment_id=str(uuid4()),  # Non-existent comment
            user_id=str(uuid4()),
            text="New text",
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Comment not found"):
            await use_case.execute(request)

    @pytest.mark.asyncio
    async def test_update_comment_fails_when_post_not_found(self, unit_env):
        """Updating comment when post doesn't exist should raise ValueError."""
        # Arrange
        comment_service = await unit_env.get(CommentService)
        post_service = await unit_env.get(PostService)
        comment_repo = await unit_env.get(CommentRepository)
        vote_repo = await unit_env.get(VoteRepository)

        use_case = UpdateCommentUseCase(
            comment_service=comment_service,
            post_service=post_service,
            vote_repository=vote_repo,
        )

        post_id = PostId(uuid4())  # Non-existent post
        comment_id = CommentId(uuid4())
        author_id = UserId(uuid4())

        # Create comment (but no post)
        comment = Comment(
            id=comment_id,
            post_id=post_id,
            author_id=author_id,
            author_handle=Handle(root="comment_author.bsky.social"),
            text="Original comment",
            parent_id=None,
            depth=0,
            path="1",
            points=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            deleted_at=None,
        )
        await comment_repo.save(comment)

        request = UpdateCommentRequest(
            post_id=str(post_id),
            comment_id=str(comment_id),
            user_id=str(author_id),
            text="New text",
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Post not found"):
            await use_case.execute(request)

    @pytest.mark.asyncio
    async def test_update_comment_fails_when_post_deleted(self, unit_env):
        """Updating comment when post is deleted should raise ContentDeletedException."""
        # Arrange
        comment_service = await unit_env.get(CommentService)
        post_service = await unit_env.get(PostService)
        comment_repo = await unit_env.get(CommentRepository)
        post_repo = await unit_env.get(PostRepository)
        vote_repo = await unit_env.get(VoteRepository)

        use_case = UpdateCommentUseCase(
            comment_service=comment_service,
            post_service=post_service,
            vote_repository=vote_repo,
        )

        post_id = PostId(uuid4())
        comment_id = CommentId(uuid4())
        author_id = UserId(uuid4())

        # Create deleted post
        post = Post(
            id=post_id,
            tag_names=[TagName("discussion")],
            author_id=UserId(uuid4()),
            author_handle=Handle(root="post_author.bsky.social"),
            title="Test Post",
            url=None,
            text="Post content",
            points=1,
            comment_count=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            deleted_at=datetime.now(),  # Deleted
        )
        await post_repo.save(post)

        # Create comment
        comment = Comment(
            id=comment_id,
            post_id=post_id,
            author_id=author_id,
            author_handle=Handle(root="comment_author.bsky.social"),
            text="Original comment",
            parent_id=None,
            depth=0,
            path="1",
            points=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            deleted_at=None,
        )
        await comment_repo.save(comment)

        request = UpdateCommentRequest(
            post_id=str(post_id),
            comment_id=str(comment_id),
            user_id=str(author_id),
            text="Updated comment",
        )

        # Act & Assert
        with pytest.raises(ContentDeletedException, match="post"):
            await use_case.execute(request)

    @pytest.mark.asyncio
    async def test_update_comment_fails_when_comment_belongs_to_different_post(
        self, unit_env
    ):
        """Updating comment with mismatched post_id should raise ValueError."""
        # Arrange
        comment_service = await unit_env.get(CommentService)
        post_service = await unit_env.get(PostService)
        comment_repo = await unit_env.get(CommentRepository)
        post_repo = await unit_env.get(PostRepository)
        vote_repo = await unit_env.get(VoteRepository)

        use_case = UpdateCommentUseCase(
            comment_service=comment_service,
            post_service=post_service,
            vote_repository=vote_repo,
        )

        post_id = PostId(uuid4())
        different_post_id = PostId(uuid4())
        comment_id = CommentId(uuid4())
        author_id = UserId(uuid4())

        # Create first post
        post1 = Post(
            id=post_id,
            tag_names=[TagName("discussion")],
            author_id=UserId(uuid4()),
            author_handle=Handle(root="post_author.bsky.social"),
            title="Test Post 1",
            url=None,
            text="Post content",
            points=1,
            comment_count=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            deleted_at=None,
        )
        await post_repo.save(post1)

        # Create second post
        post2 = Post(
            id=different_post_id,
            tag_names=[TagName("discussion")],
            author_id=UserId(uuid4()),
            author_handle=Handle(root="post_author.bsky.social"),
            title="Test Post 2",
            url=None,
            text="Post content",
            points=1,
            comment_count=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            deleted_at=None,
        )
        await post_repo.save(post2)

        # Create comment belonging to first post
        comment = Comment(
            id=comment_id,
            post_id=post_id,  # Belongs to post1
            author_id=author_id,
            author_handle=Handle(root="comment_author.bsky.social"),
            text="Original comment",
            parent_id=None,
            depth=0,
            path="1",
            points=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            deleted_at=None,
        )
        await comment_repo.save(comment)

        # Try to update with different post_id
        request = UpdateCommentRequest(
            post_id=str(different_post_id),  # Wrong post!
            comment_id=str(comment_id),
            user_id=str(author_id),
            text="Updated comment",
        )

        # Act & Assert
        with pytest.raises(ValueError, match="does not belong to post"):
            await use_case.execute(request)
