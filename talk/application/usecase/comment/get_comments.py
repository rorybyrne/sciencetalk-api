"""Get comments use case."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from talk.domain.service import CommentService
from talk.domain.value import PostId
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


class GetCommentsRequest(BaseModel):
    """Get comments request."""

    post_id: str  # UUID string


class GetCommentsResponse(BaseModel):
    """Get comments response."""

    post_id: str
    comments: list[CommentItem]
    total: int


class GetCommentsUseCase:
    """Use case for getting all comments for a post in tree order."""

    def __init__(self, comment_service: CommentService) -> None:
        """Initialize get comments use case.

        Args:
            comment_service: Comment domain service
        """
        self.comment_service = comment_service

    async def execute(self, request: GetCommentsRequest) -> GetCommentsResponse:
        """Execute get comments flow.

        Comments are returned in tree order (using ltree path)
        for efficient rendering of threaded discussions.

        Args:
            request: Get comments request with post ID

        Returns:
            List of comments in tree order
        """
        post_id = PostId(UUID(request.post_id))

        # Fetch comments via service
        comments = await self.comment_service.get_comments_for_post(
            post_id=post_id,
            include_deleted=False,
        )

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
            )
            for comment in comments
        ]

        return GetCommentsResponse(
            post_id=request.post_id,
            comments=comment_items,
            total=len(comment_items),
        )
