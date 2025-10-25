"""Unit tests for RemoveVoteUseCase."""

from datetime import datetime
from uuid import uuid4

import pytest

from talk.application.usecase.vote.remove_vote import (
    RemoveVoteRequest,
    RemoveVoteUseCase,
)
from talk.domain.model.post import Post
from talk.domain.model.comment import Comment
from talk.domain.service import VoteService
from talk.domain.value import CommentId, PostId, UserId, VotableType
from talk.domain.value.types import Handle, PostType
from talk.persistence.repository.post import PostRepository
from talk.persistence.repository.comment import CommentRepository
from tests.harness import create_env_fixture

# Unit test fixture
unit_env = create_env_fixture()


class TestRemoveVoteUseCase:
    """Tests for RemoveVoteUseCase."""

    @pytest.mark.asyncio
    async def test_remove_vote_from_post_routes_correctly(self, unit_env):
        """Removing post vote should route to remove_vote_from_post."""
        # Arrange
        vote_service = await unit_env.get(VoteService)
        post_repo = await unit_env.get(PostRepository)

        remove_vote_use_case = RemoveVoteUseCase(vote_service=vote_service)

        post_id = PostId(uuid4())
        user_id = UserId(uuid4())

        # Create post first
        post = Post(
            id=post_id,
            type=PostType.DISCUSSION,
            author_id=UserId(uuid4()),
            author_handle=Handle(value="author.bsky.social"),
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

        # Create upvote first
        await vote_service.upvote_post(post_id, user_id)

        request = RemoveVoteRequest(
            votable_type=VotableType.POST,
            votable_id=str(post_id),
            user_id=str(user_id),
        )

        # Act
        response = await remove_vote_use_case.execute(request)

        # Assert
        assert response.success is True
        assert "successfully" in response.message

        # Verify vote was removed and points decremented
        updated_post = await post_repo.find_by_id(post_id)
        assert updated_post.points == 1

    @pytest.mark.asyncio
    async def test_remove_vote_from_comment_routes_correctly(self, unit_env):
        """Removing comment vote should route to remove_vote_from_comment."""
        # Arrange
        vote_service = await unit_env.get(VoteService)
        comment_repo = await unit_env.get(CommentRepository)

        remove_vote_use_case = RemoveVoteUseCase(vote_service=vote_service)

        comment_id = CommentId(uuid4())
        user_id = UserId(uuid4())

        # Create comment first
        comment = Comment(
            id=comment_id,
            post_id=PostId(uuid4()),
            author_id=UserId(uuid4()),
            author_handle=Handle(value="author.bsky.social"),
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

        # Create upvote first
        await vote_service.upvote_comment(comment_id, user_id)

        request = RemoveVoteRequest(
            votable_type=VotableType.COMMENT,
            votable_id=str(comment_id),
            user_id=str(user_id),
        )

        # Act
        response = await remove_vote_use_case.execute(request)

        # Assert
        assert response.success is True

        # Verify vote was removed and points decremented
        updated_comment = await comment_repo.find_by_id(comment_id)
        assert updated_comment.points == 1

    @pytest.mark.asyncio
    async def test_remove_vote_returns_false_when_no_vote(self, unit_env):
        """Removing non-existent vote should return success=False."""
        # Arrange
        vote_service = await unit_env.get(VoteService)
        post_repo = await unit_env.get(PostRepository)

        remove_vote_use_case = RemoveVoteUseCase(vote_service=vote_service)

        post_id = PostId(uuid4())
        user_id = UserId(uuid4())

        # Create post but don't create vote
        post = Post(
            id=post_id,
            type=PostType.DISCUSSION,
            author_id=UserId(uuid4()),
            author_handle=Handle(value="author.bsky.social"),
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

        request = RemoveVoteRequest(
            votable_type=VotableType.POST,
            votable_id=str(post_id),
            user_id=str(user_id),
        )

        # Act
        response = await remove_vote_use_case.execute(request)

        # Assert
        assert response.success is False
        assert "No vote found" in response.message
