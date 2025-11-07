"""Get comments use case."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from talk.domain.service import CommentService, JWTService, VoteService
from talk.domain.value import PostId, UserId
from talk.domain.value.types import Handle


class CommentItem(BaseModel):
    """Comment item in response."""

    comment_id: str
    post_id: str
    author_id: str
    author_handle: Handle
    text: str
    parent_id: str | None
    depth: int
    path: str | None
    points: int
    created_at: datetime
    content_updated_at: datetime
    has_voted: bool


class GetCommentsRequest(BaseModel):
    """Get comments request."""

    post_id: str  # UUID string
    auth_token: str | None = None  # JWT token for authentication (optional)


class GetCommentsResponse(BaseModel):
    """Get comments response."""

    post_id: str
    comments: list[CommentItem]
    total: int


class GetCommentsUseCase:
    """Use case for getting all comments for a post in tree order."""

    def __init__(
        self,
        comment_service: CommentService,
        vote_service: VoteService,
        jwt_service: JWTService,
    ) -> None:
        """Initialize get comments use case.

        Args:
            comment_service: Comment domain service
            vote_service: Vote service for checking user votes
            jwt_service: JWT service for decoding auth tokens
        """
        self.comment_service = comment_service
        self.vote_service = vote_service
        self.jwt_service = jwt_service

    async def execute(self, request: GetCommentsRequest) -> GetCommentsResponse:
        """Execute get comments flow.

        Comments are returned in tree order (using ltree path)
        for efficient rendering of threaded discussions.

        Args:
            request: Get comments request with post ID and optional auth token

        Returns:
            List of comments in tree order with vote state
        """
        post_id = PostId(UUID(request.post_id))

        # Fetch comments via service
        comments = await self.comment_service.get_comments_for_post(
            post_id=post_id,
            include_deleted=False,
        )

        # Check which comments the user has voted on (if authenticated)
        user_votes: dict[str, bool] = {}
        if request.auth_token and comments:
            try:
                # Verify token to get user ID
                payload = self.jwt_service.verify_token(request.auth_token)
                user_id = UserId(UUID(payload.user_id))

                # Batch query for all votes
                comment_ids = [comment.id for comment in comments]
                votes_map = await self.vote_service.get_user_votes_for_comments(
                    user_id=user_id,
                    comment_ids=comment_ids,
                )
                # Convert CommentId keys to string keys for easy lookup
                user_votes = {
                    str(cid): has_voted for cid, has_voted in votes_map.items()
                }
            except Exception:
                # Invalid or expired token - treat as unauthenticated
                pass

        # Convert to response items
        comment_items = [
            CommentItem(
                comment_id=str(comment.id),
                post_id=str(comment.post_id),
                author_id=str(comment.author_id),
                author_handle=comment.author_handle,
                text=comment.text,
                parent_id=str(comment.parent_id) if comment.parent_id else None,
                depth=comment.depth,
                path=comment.path,
                points=comment.points,
                created_at=comment.created_at,
                content_updated_at=comment.content_updated_at,
                has_voted=user_votes.get(str(comment.id), False),
            )
            for comment in comments
        ]

        return GetCommentsResponse(
            post_id=request.post_id,
            comments=comment_items,
            total=len(comment_items),
        )
