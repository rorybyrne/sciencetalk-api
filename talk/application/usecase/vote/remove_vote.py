"""Remove vote use case."""

from uuid import UUID

from pydantic import BaseModel

from talk.domain.service import VoteService
from talk.domain.value import CommentId, PostId, UserId, VotableType


class RemoveVoteRequest(BaseModel):
    """Remove vote request."""

    votable_type: VotableType
    votable_id: str  # UUID string
    user_id: str  # User ID from authenticated user


class RemoveVoteResponse(BaseModel):
    """Remove vote response."""

    success: bool
    message: str


class RemoveVoteUseCase:
    """Use case for removing a vote from a post or comment."""

    def __init__(self, vote_service: VoteService) -> None:
        """Initialize remove vote use case.

        Args:
            vote_service: Vote domain service
        """
        self.vote_service = vote_service

    async def execute(self, request: RemoveVoteRequest) -> RemoveVoteResponse:
        """Execute remove vote flow.

        Args:
            request: Remove vote request

        Returns:
            Remove vote response

        Raises:
            ValueError: If item not found
        """
        user_id = UserId(UUID(request.user_id))

        if request.votable_type == VotableType.POST:
            post_id = PostId(UUID(request.votable_id))
            removed = await self.vote_service.remove_vote_from_post(post_id, user_id)
        else:  # VotableType.COMMENT
            comment_id = CommentId(UUID(request.votable_id))
            removed = await self.vote_service.remove_vote_from_comment(
                comment_id, user_id
            )

        if removed:
            return RemoveVoteResponse(
                success=True,
                message="Vote removed successfully",
            )
        else:
            return RemoveVoteResponse(
                success=False,
                message="No vote found to remove",
            )
