"""Upvote use case."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from talk.domain.service import VoteService
from talk.domain.value import CommentId, PostId, UserId, VotableType


class UpvoteRequest(BaseModel):
    """Upvote request."""

    votable_type: VotableType
    votable_id: str  # UUID string
    user_id: str  # User ID from authenticated user


class UpvoteResponse(BaseModel):
    """Upvote response."""

    vote_id: str
    votable_type: VotableType
    votable_id: str
    created_at: datetime


class UpvoteUseCase:
    """Use case for upvoting a post or comment."""

    def __init__(self, vote_service: VoteService) -> None:
        """Initialize upvote use case.

        Args:
            vote_service: Vote domain service
        """
        self.vote_service = vote_service

    async def execute(self, request: UpvoteRequest) -> UpvoteResponse:
        """Execute upvote flow.

        Args:
            request: Upvote request

        Returns:
            Upvote response with vote details

        Raises:
            ValueError: If already voted or item not found
        """
        user_id = UserId(UUID(request.user_id))

        if request.votable_type == VotableType.POST:
            post_id = PostId(UUID(request.votable_id))
            vote = await self.vote_service.upvote_post(post_id, user_id)
        else:  # VotableType.COMMENT
            comment_id = CommentId(UUID(request.votable_id))
            vote = await self.vote_service.upvote_comment(comment_id, user_id)

        return UpvoteResponse(
            vote_id=str(vote.id),
            votable_type=vote.votable_type,
            votable_id=str(vote.votable_id),
            created_at=vote.created_at,
        )
