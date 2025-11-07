"""Update comment use case."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from talk.domain.error import ContentDeletedException, NotAuthorizedError
from talk.domain.repository import VoteRepository
from talk.domain.service import CommentService, PostService
from talk.domain.value import CommentId, PostId, UserId, VotableType
from talk.domain.value.types import Handle


class UpdateCommentRequest(BaseModel):
    """Update comment request."""

    comment_id: str  # UUID string
    post_id: str  # UUID string (for validation)
    user_id: str  # Current user ID (must be author)
    text: str  # New text content (required, cannot be empty)


class UpdateCommentResponse(BaseModel):
    """Update comment response."""

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


class UpdateCommentUseCase:
    """Use case for updating a comment's text content."""

    def __init__(
        self,
        comment_service: CommentService,
        post_service: PostService,
        vote_repository: VoteRepository,
    ) -> None:
        """Initialize update comment use case.

        Args:
            comment_service: Comment service
            post_service: Post service
            vote_repository: Vote repository
        """
        self.comment_service = comment_service
        self.post_service = post_service
        self.vote_repository = vote_repository

    async def execute(self, request: UpdateCommentRequest) -> UpdateCommentResponse:
        """Execute update comment flow.

        Args:
            request: Update comment request with comment ID, post ID, user ID, and new text

        Returns:
            Updated comment details

        Raises:
            NotAuthorizedError: If user doesn't own the comment
            ContentDeletedException: If comment or post is deleted
        """
        comment_id = CommentId(UUID(request.comment_id))
        post_id = PostId(UUID(request.post_id))
        user_id = UserId(UUID(request.user_id))

        # 1. Retrieve existing comment
        comment = await self.comment_service.get_comment_by_id(comment_id)

        if comment is None:
            raise ValueError(f"Comment not found: {request.comment_id}")

        # 2. Validate comment belongs to specified post
        if comment.post_id != post_id:
            raise ValueError(
                f"Comment {request.comment_id} does not belong to post {request.post_id}"
            )

        # 3. Check authorization (user owns comment)
        if comment.author_id != user_id:
            raise NotAuthorizedError("comment", request.comment_id, request.user_id)

        # 4. Check not deleted
        if comment.deleted_at is not None:
            raise ContentDeletedException("comment", request.comment_id)

        # 5. Verify post exists and is not deleted
        post = await self.post_service.get_post_by_id(post_id)
        if post is None:
            raise ValueError(f"Post not found: {request.post_id}")
        if post.deleted_at is not None:
            raise ContentDeletedException("post", request.post_id)

        # 6. Update via service
        updated_comment = await self.comment_service.update_text(
            comment_id, request.text
        )

        # Should not happen since we checked above, but handle defensively
        if updated_comment is None:
            raise ContentDeletedException("comment", request.comment_id)

        # 7. Get user's vote status
        vote = await self.vote_repository.find_by_user_and_votable(
            user_id=user_id,
            votable_type=VotableType.COMMENT,
            votable_id=comment_id,
        )
        has_voted = vote is not None

        return UpdateCommentResponse(
            comment_id=str(updated_comment.id),
            post_id=str(updated_comment.post_id),
            author_id=str(updated_comment.author_id),
            author_handle=updated_comment.author_handle,
            text=updated_comment.text,
            parent_id=str(updated_comment.parent_id)
            if updated_comment.parent_id
            else None,
            depth=updated_comment.depth,
            path=updated_comment.path,
            points=updated_comment.points,
            created_at=updated_comment.created_at,
            content_updated_at=updated_comment.content_updated_at,
            has_voted=has_voted,
        )
