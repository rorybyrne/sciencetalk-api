"""Create comment use case."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from talk.domain.service import CommentService, PostService
from talk.domain.value import CommentId, PostId, UserId
from talk.domain.value.types import Handle


class CreateCommentRequest(BaseModel):
    """Create comment request."""

    post_id: str  # UUID string
    text: str
    author_id: str  # User ID from authenticated user
    author_handle: Handle  # Handle from authenticated user
    parent_id: str | None = None  # Parent comment ID for replies


class CreateCommentResponse(BaseModel):
    """Create comment response."""

    comment_id: str
    post_id: str
    text: str
    parent_id: str | None
    depth: int
    created_at: datetime
    content_updated_at: datetime


class CreateCommentUseCase:
    """Use case for creating a comment on a post or replying to another comment."""

    def __init__(
        self,
        comment_service: CommentService,
        post_service: PostService,
    ) -> None:
        """Initialize create comment use case.

        Args:
            comment_service: Comment domain service
            post_service: Post domain service
        """
        self.comment_service = comment_service
        self.post_service = post_service

    async def execute(self, request: CreateCommentRequest) -> CreateCommentResponse:
        """Execute create comment flow.

        Steps:
        1. Verify post exists via post service
        2. Create comment via comment service (validates parent if replying)
        3. Update post's comment count via post service

        Args:
            request: Create comment request

        Returns:
            Create comment response with comment details

        Raises:
            ValueError: If post not found or parent comment invalid
        """
        post_id = PostId(UUID(request.post_id))

        # Verify post exists
        post = await self.post_service.get_post_by_id(post_id)
        if not post:
            raise ValueError("Post not found")

        # Create comment (service handles parent validation)
        parent_comment_id = (
            CommentId(UUID(request.parent_id)) if request.parent_id else None
        )
        comment = await self.comment_service.create_comment(
            post_id=post_id,
            author_id=UserId(UUID(request.author_id)),
            author_handle=request.author_handle,
            text=request.text,
            parent_id=parent_comment_id,
        )

        # Update post's comment count
        await self.post_service.increment_comment_count(post_id)

        return CreateCommentResponse(
            comment_id=str(comment.id),
            post_id=str(comment.post_id),
            text=comment.text,
            parent_id=str(comment.parent_id) if comment.parent_id else None,
            depth=comment.depth,
            created_at=comment.created_at,
            content_updated_at=comment.content_updated_at,
        )
