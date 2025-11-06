"""Unit tests for CommentService."""

from datetime import datetime
from uuid import uuid4

import pytest

from talk.domain.model.comment import Comment
from talk.domain.service import CommentService
from talk.domain.value import CommentId, PostId, UserId
from talk.domain.value.types import Handle
from talk.persistence.repository.comment import CommentRepository
from tests.harness import create_env_fixture

# Unit test fixture - everything mocked, no docker needed
unit_env = create_env_fixture()


class TestCreateComment:
    """Tests for create_comment method."""

    @pytest.mark.asyncio
    async def test_create_comment_top_level_with_depth_zero(self, unit_env):
        """Top-level comment should have depth 0."""
        # Arrange
        comment_service = await unit_env.get(CommentService)
        comment_repo = await unit_env.get(CommentRepository)

        post_id = PostId(uuid4())
        author_id = UserId(uuid4())
        author_handle = Handle(root="user.bsky.social")
        text = "Test comment"

        # Act
        result = await comment_service.create_comment(
            post_id=post_id,
            author_id=author_id,
            author_handle=author_handle,
            text=text,
            parent_id=None,
        )

        # Assert
        assert result.depth == 0
        assert result.parent_id is None
        assert result.text == text
        assert result.post_id == post_id

        # Verify it was saved in repository
        saved = await comment_repo.find_by_id(result.id)
        assert saved is not None
        assert saved.depth == 0

    @pytest.mark.asyncio
    async def test_create_comment_reply_increments_depth(self, unit_env):
        """Reply comment should increment parent depth."""
        # Arrange
        comment_service = await unit_env.get(CommentService)
        comment_repo = await unit_env.get(CommentRepository)

        post_id = PostId(uuid4())
        parent_id = CommentId(uuid4())
        author_id = UserId(uuid4())
        author_handle = Handle(root="user.bsky.social")
        text = "Reply comment"

        # Create parent comment first
        parent_comment = Comment(
            id=parent_id,
            post_id=post_id,
            author_id=UserId(uuid4()),
            author_handle=Handle(root="parent.bsky.social"),
            text="Parent comment",
            parent_id=None,
            depth=2,  # Parent has depth 2
            path="1.2",
            points=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            deleted_at=None,
        )
        await comment_repo.save(parent_comment)

        # Act
        result = await comment_service.create_comment(
            post_id=post_id,
            author_id=author_id,
            author_handle=author_handle,
            text=text,
            parent_id=parent_id,
        )

        # Assert
        assert result.depth == 3  # parent depth (2) + 1
        assert result.parent_id == parent_id
        assert result.text == text

    @pytest.mark.asyncio
    async def test_create_comment_with_invalid_parent_raises_error(self, unit_env):
        """Creating comment with non-existent parent should raise error."""
        # Arrange
        comment_service = await unit_env.get(CommentService)

        post_id = PostId(uuid4())
        parent_id = CommentId(uuid4())  # Non-existent parent
        author_id = UserId(uuid4())
        author_handle = Handle(root="user.bsky.social")

        # Don't save parent - it doesn't exist

        # Act & Assert
        with pytest.raises(ValueError, match="Parent comment not found"):
            await comment_service.create_comment(
                post_id=post_id,
                author_id=author_id,
                author_handle=author_handle,
                text="Test",
                parent_id=parent_id,
            )

    @pytest.mark.asyncio
    async def test_create_comment_with_parent_from_different_post_raises_error(
        self, unit_env
    ):
        """Reply to comment from different post should raise error."""
        # Arrange
        comment_service = await unit_env.get(CommentService)
        comment_repo = await unit_env.get(CommentRepository)

        post_id = PostId(uuid4())
        different_post_id = PostId(uuid4())
        parent_id = CommentId(uuid4())
        author_id = UserId(uuid4())
        author_handle = Handle(root="user.bsky.social")

        # Create parent comment belonging to different post
        parent_comment = Comment(
            id=parent_id,
            post_id=different_post_id,  # Different post!
            author_id=UserId(uuid4()),
            author_handle=Handle(root="parent.bsky.social"),
            text="Parent comment",
            parent_id=None,
            depth=0,
            path="1",
            points=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            deleted_at=None,
        )
        await comment_repo.save(parent_comment)

        # Act & Assert
        with pytest.raises(ValueError, match="does not belong to this post"):
            await comment_service.create_comment(
                post_id=post_id,
                author_id=author_id,
                author_handle=author_handle,
                text="Test",
                parent_id=parent_id,
            )


class TestUpdateText:
    """Tests for update_text method."""

    @pytest.mark.asyncio
    async def test_update_text_updates_comment_text(self, unit_env):
        """Updating text should update comment text and timestamp."""
        # Arrange
        comment_service = await unit_env.get(CommentService)
        comment_repo = await unit_env.get(CommentRepository)

        comment_id = CommentId(uuid4())
        post_id = PostId(uuid4())
        original_time = datetime(2024, 1, 1, 12, 0, 0)
        original_text = "Original comment"
        new_text = "Updated comment"

        comment = Comment(
            id=comment_id,
            post_id=post_id,
            author_id=UserId(uuid4()),
            author_handle=Handle(root="author.bsky.social"),
            text=original_text,
            parent_id=None,
            depth=0,
            path="1",
            points=1,
            created_at=original_time,
            updated_at=original_time,
            deleted_at=None,
        )
        await comment_repo.save(comment)

        # Act
        result = await comment_service.update_text(comment_id, new_text)

        # Assert
        assert result is not None
        assert result.text == new_text
        assert result.updated_at > original_time

        # Verify it was saved
        saved_comment = await comment_repo.find_by_id(comment_id)
        assert saved_comment.text == new_text
        assert saved_comment.updated_at > original_time

    @pytest.mark.asyncio
    async def test_update_text_returns_none_when_comment_not_found(self, unit_env):
        """Updating text for non-existent comment should return None."""
        # Arrange
        comment_service = await unit_env.get(CommentService)
        comment_id = CommentId(uuid4())

        # Act
        result = await comment_service.update_text(comment_id, "New text")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_update_text_returns_none_when_comment_deleted(self, unit_env):
        """Updating text for deleted comment should return None."""
        # Arrange
        comment_service = await unit_env.get(CommentService)
        comment_repo = await unit_env.get(CommentRepository)

        comment_id = CommentId(uuid4())
        comment = Comment(
            id=comment_id,
            post_id=PostId(uuid4()),
            author_id=UserId(uuid4()),
            author_handle=Handle(root="author.bsky.social"),
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

        # Act
        result = await comment_service.update_text(comment_id, "New text")

        # Assert
        assert result is None
