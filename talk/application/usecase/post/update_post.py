"""Update post use case."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from talk.domain.error import (
    ContentDeletedException,
    InvalidEditOperationError,
    NotAuthorizedError,
)
from talk.domain.repository import VoteRepository
from talk.domain.service import PostService
from talk.domain.value import PostId, UserId, VotableType
from talk.domain.value.types import Handle


class UpdatePostRequest(BaseModel):
    """Update post request."""

    post_id: str  # UUID string
    user_id: str  # Current user ID (must be author)
    text: str | None  # New text content (None to clear)


class UpdatePostResponse(BaseModel):
    """Update post response."""

    post_id: str
    title: str
    tag_names: list[str]
    author_id: str
    author_handle: Handle
    url: str | None
    text: str | None
    points: int
    comment_count: int
    created_at: datetime
    updated_at: datetime
    has_voted: bool


class UpdatePostUseCase:
    """Use case for updating a post's text content."""

    def __init__(
        self, post_service: PostService, vote_repository: VoteRepository
    ) -> None:
        """Initialize update post use case.

        Args:
            post_service: Post service
            vote_repository: Vote repository
        """
        self.post_service = post_service
        self.vote_repository = vote_repository

    async def execute(self, request: UpdatePostRequest) -> UpdatePostResponse:
        """Execute update post flow.

        Args:
            request: Update post request with post ID, user ID, and new text

        Returns:
            Updated post details

        Raises:
            NotAuthorizedError: If user doesn't own the post
            ContentDeletedException: If post is deleted
            InvalidEditOperationError: If trying to edit text on URL-based post
        """
        post_id = PostId(UUID(request.post_id))
        user_id = UserId(UUID(request.user_id))

        # 1. Retrieve existing post
        post = await self.post_service.get_post_by_id(post_id)

        if post is None:
            raise ValueError(f"Post not found: {request.post_id}")

        # 2. Check authorization (user owns post)
        if post.author_id != user_id:
            raise NotAuthorizedError("post", request.post_id, request.user_id)

        # 3. Check not deleted
        if post.deleted_at is not None:
            raise ContentDeletedException("post", request.post_id)

        # 4. Validate edit operation
        # Cannot edit text on URL-based posts
        if post.url is not None:
            raise InvalidEditOperationError(
                "Cannot edit text on URL-based posts (Result, Method, Review, Tool)"
            )

        # 5. Update via service
        updated_post = await self.post_service.update_text(post_id, request.text)

        # Should not happen since we checked above, but handle defensively
        if updated_post is None:
            raise ContentDeletedException("post", request.post_id)

        # 6. Get user's vote status
        vote = await self.vote_repository.find_by_user_and_votable(
            user_id=user_id,
            votable_type=VotableType.POST,
            votable_id=post_id,
        )
        has_voted = vote is not None

        return UpdatePostResponse(
            post_id=str(updated_post.id),
            title=updated_post.title,
            tag_names=[tag.root for tag in updated_post.tag_names],
            author_id=str(updated_post.author_id),
            author_handle=updated_post.author_handle,
            url=updated_post.url,
            text=updated_post.text,
            points=updated_post.points,
            comment_count=updated_post.comment_count,
            created_at=updated_post.created_at,
            updated_at=updated_post.updated_at,
            has_voted=has_voted,
        )
