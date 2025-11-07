"""Unit tests for UpvoteUseCase."""

from datetime import datetime
from uuid import uuid4

import pytest

from talk.application.usecase.vote.upvote import UpvoteRequest, UpvoteUseCase
from talk.domain.model.post import Post
from talk.domain.model.comment import Comment
from talk.domain.service import VoteService
from talk.domain.value import CommentId, PostId, UserId, VotableType
from talk.domain.value.types import Handle, TagName
from talk.persistence.repository.post import PostRepository
from talk.persistence.repository.comment import CommentRepository
from tests.conftest import make_slug
from tests.harness import create_env_fixture

# Unit test fixture
unit_env = create_env_fixture()


class TestUpvoteUseCase:
    """Tests for UpvoteUseCase."""

    @pytest.mark.asyncio
    async def test_upvote_post_routes_to_post_service(self, unit_env):
        """Upvoting post should route to upvote_post."""
        # Arrange
        vote_service = await unit_env.get(VoteService)
        post_repo = await unit_env.get(PostRepository)

        upvote_use_case = UpvoteUseCase(vote_service=vote_service)

        post_id = PostId(uuid4())
        user_id = UserId(uuid4())

        # Create post first
        now = datetime.now()
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
            comment_count=0,
            created_at=now,
            comments_updated_at=now,
            content_updated_at=now,
            deleted_at=None,
        )
        await post_repo.save(post)

        request = UpvoteRequest(
            votable_type=VotableType.POST,
            votable_id=str(post_id),
            user_id=str(user_id),
        )

        # Act
        response = await upvote_use_case.execute(request)

        # Assert
        assert response.vote_id is not None
        assert response.votable_type == VotableType.POST

        # Verify vote was created and points incremented
        updated_post = await post_repo.find_by_id(post_id)
        assert updated_post.points == 2

    @pytest.mark.asyncio
    async def test_upvote_comment_routes_to_comment_service(self, unit_env):
        """Upvoting comment should route to upvote_comment."""
        # Arrange
        vote_service = await unit_env.get(VoteService)
        comment_repo = await unit_env.get(CommentRepository)

        upvote_use_case = UpvoteUseCase(vote_service=vote_service)

        comment_id = CommentId(uuid4())
        user_id = UserId(uuid4())

        # Create comment first
        now = datetime.now()
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
            created_at=now,
            content_updated_at=now,
            deleted_at=None,
        )
        await comment_repo.save(comment)

        request = UpvoteRequest(
            votable_type=VotableType.COMMENT,
            votable_id=str(comment_id),
            user_id=str(user_id),
        )

        # Act
        response = await upvote_use_case.execute(request)

        # Assert
        assert response.vote_id is not None
        assert response.votable_type == VotableType.COMMENT

        # Verify vote was created and points incremented
        updated_comment = await comment_repo.find_by_id(comment_id)
        assert updated_comment.points == 2
