"""Get post use case."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from talk.domain.repository import PostRepository, VoteRepository
from talk.domain.value import PostId, UserId, VotableType
from talk.domain.value.types import Handle


class GetPostRequest(BaseModel):
    """Get post request."""

    post_id: str  # UUID string
    user_id: str | None = None  # Current user ID (if authenticated)


class GetPostResponse(BaseModel):
    """Get post response."""

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
    comments_updated_at: datetime
    content_updated_at: datetime
    has_voted: bool


class GetPostUseCase:
    """Use case for retrieving a post by ID."""

    def __init__(
        self, post_repository: PostRepository, vote_repository: VoteRepository
    ) -> None:
        """Initialize get post use case.

        Args:
            post_repository: Post repository
            vote_repository: Vote repository
        """
        self.post_repository = post_repository
        self.vote_repository = vote_repository

    async def execute(self, request: GetPostRequest) -> Optional[GetPostResponse]:
        """Execute get post flow.

        Args:
            request: Get post request with post ID and optional user ID

        Returns:
            Post details if found, None otherwise
        """
        # Find post by ID
        post = await self.post_repository.find_by_id(PostId(UUID(request.post_id)))

        if not post:
            return None

        # Don't return deleted posts
        if post.deleted_at is not None:
            return None

        # Check if user has voted (if authenticated)
        has_voted = False
        if request.user_id:
            vote = await self.vote_repository.find_by_user_and_votable(
                user_id=UserId(UUID(request.user_id)),
                votable_type=VotableType.POST,
                votable_id=post.id,
            )
            has_voted = vote is not None

        return GetPostResponse(
            post_id=str(post.id),
            title=post.title,
            tag_names=[tag.root for tag in post.tag_names],
            author_id=str(post.author_id),
            author_handle=post.author_handle,
            url=post.url,
            text=post.text,
            points=post.points,
            comment_count=post.comment_count,
            created_at=post.created_at,
            comments_updated_at=post.comments_updated_at,
            content_updated_at=post.content_updated_at,
            has_voted=has_voted,
        )
