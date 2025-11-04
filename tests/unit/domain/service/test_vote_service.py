"""Unit tests for VoteService."""

from datetime import datetime
from uuid import uuid4

import pytest

from talk.domain.model.post import Post
from talk.domain.model.comment import Comment
from talk.domain.service import VoteService
from talk.domain.value import CommentId, PostId, UserId, VotableType
from talk.domain.value.types import Handle, TagName
from talk.persistence.repository.vote import VoteRepository
from talk.persistence.repository.post import PostRepository
from talk.persistence.repository.comment import CommentRepository
from tests.harness import create_env_fixture

# Unit test fixture - everything mocked, no docker needed
unit_env = create_env_fixture()


class TestUpvotePost:
    """Tests for upvote_post method."""

    @pytest.mark.asyncio
    async def test_upvote_post_creates_vote_and_increments_points(self, unit_env):
        """Upvoting post should create vote and increment points."""
        # Arrange
        vote_service = await unit_env.get(VoteService)
        vote_repo = await unit_env.get(VoteRepository)
        post_repo = await unit_env.get(PostRepository)

        post_id = PostId(uuid4())
        user_id = UserId(uuid4())

        post = Post(
            id=post_id,
            tag_names=[TagName("discussion")],
            author_id=UserId(uuid4()),
            author_handle=Handle(root="author.bsky.social"),
            title="Test Post",
            url=None,
            text="Test content",
            points=1,
            comment_count=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            deleted_at=None,
        )
        await post_repo.save(post)

        # Act
        result = await vote_service.upvote_post(post_id, user_id)

        # Assert - verify vote was created
        saved_vote = await vote_repo.find_by_user_and_votable(
            user_id, VotableType.POST, post_id
        )
        assert saved_vote is not None
        assert saved_vote.user_id == user_id
        assert saved_vote.votable_type == VotableType.POST
        assert result == saved_vote

        # Verify points were incremented
        updated_post = await post_repo.find_by_id(post_id)
        assert updated_post.points == 2

    @pytest.mark.asyncio
    async def test_upvote_post_with_nonexistent_post_raises_error(self, unit_env):
        """Upvoting non-existent post should raise error."""
        # Arrange
        vote_service = await unit_env.get(VoteService)
        post_id = PostId(uuid4())
        user_id = UserId(uuid4())

        # Act & Assert
        with pytest.raises(ValueError, match="Post not found"):
            await vote_service.upvote_post(post_id, user_id)

    @pytest.mark.asyncio
    async def test_upvote_post_duplicate_raises_error(self, unit_env):
        """Duplicate upvote should raise error."""
        # Arrange
        vote_service = await unit_env.get(VoteService)
        post_repo = await unit_env.get(PostRepository)

        post_id = PostId(uuid4())
        user_id = UserId(uuid4())

        post = Post(
            id=post_id,
            tag_names=[TagName("discussion")],
            author_id=UserId(uuid4()),
            author_handle=Handle(root="author.bsky.social"),
            title="Test Post",
            url=None,
            text="Test content",
            points=1,
            comment_count=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            deleted_at=None,
        )
        await post_repo.save(post)

        # First upvote
        await vote_service.upvote_post(post_id, user_id)

        # Act & Assert - Second upvote should fail
        with pytest.raises(ValueError, match="Already voted"):
            await vote_service.upvote_post(post_id, user_id)


class TestUpvoteComment:
    """Tests for upvote_comment method."""

    @pytest.mark.asyncio
    async def test_upvote_comment_duplicate_raises_error(self, unit_env):
        """Duplicate comment upvote should raise error."""
        # Arrange
        vote_service = await unit_env.get(VoteService)
        comment_repo = await unit_env.get(CommentRepository)

        comment_id = CommentId(uuid4())
        user_id = UserId(uuid4())

        comment = Comment(
            id=comment_id,
            post_id=PostId(uuid4()),
            author_id=UserId(uuid4()),
            author_handle=Handle(root="author.bsky.social"),
            text="Test comment",
            parent_id=None,
            depth=0,
            path="1",
            points=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            deleted_at=None,
        )
        await comment_repo.save(comment)

        # First upvote
        await vote_service.upvote_comment(comment_id, user_id)

        # Act & Assert - Second upvote should fail
        with pytest.raises(ValueError, match="Already voted"):
            await vote_service.upvote_comment(comment_id, user_id)


class TestRemoveVote:
    """Tests for remove vote methods."""

    @pytest.mark.asyncio
    async def test_remove_vote_from_post_deletes_and_decrements(self, unit_env):
        """Removing vote should delete record and decrement points."""
        # Arrange
        vote_service = await unit_env.get(VoteService)
        post_repo = await unit_env.get(PostRepository)
        vote_repo = await unit_env.get(VoteRepository)

        post_id = PostId(uuid4())
        user_id = UserId(uuid4())

        post = Post(
            id=post_id,
            tag_names=[TagName("discussion")],
            author_id=UserId(uuid4()),
            author_handle=Handle(root="author.bsky.social"),
            title="Test Post",
            url=None,
            text="Test content",
            points=1,
            comment_count=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            deleted_at=None,
        )
        await post_repo.save(post)

        # Create a vote first
        await vote_service.upvote_post(post_id, user_id)

        # Act
        result = await vote_service.remove_vote_from_post(post_id, user_id)

        # Assert
        assert result is True

        # Verify vote was deleted
        saved_vote = await vote_repo.find_by_user_and_votable(
            user_id, VotableType.POST, post_id
        )
        assert saved_vote is None

        # Verify points were decremented back to original
        updated_post = await post_repo.find_by_id(post_id)
        assert updated_post.points == 1

    @pytest.mark.asyncio
    async def test_remove_vote_from_post_returns_false_when_no_vote(self, unit_env):
        """Removing non-existent vote should return False and not decrement."""
        # Arrange
        vote_service = await unit_env.get(VoteService)
        post_repo = await unit_env.get(PostRepository)

        post_id = PostId(uuid4())
        user_id = UserId(uuid4())

        post = Post(
            id=post_id,
            tag_names=[TagName("discussion")],
            author_id=UserId(uuid4()),
            author_handle=Handle(root="author.bsky.social"),
            title="Test Post",
            url=None,
            text="Test content",
            points=1,
            comment_count=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            deleted_at=None,
        )
        await post_repo.save(post)

        # Act - Try to remove vote that doesn't exist
        result = await vote_service.remove_vote_from_post(post_id, user_id)

        # Assert
        assert result is False

        # Verify points were not changed
        updated_post = await post_repo.find_by_id(post_id)
        assert updated_post.points == 1
