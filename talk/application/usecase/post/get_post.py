"""Get post use case."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from talk.domain.repository import PostRepository
from talk.domain.value import PostId, PostType


class GetPostRequest(BaseModel):
    """Get post request."""

    post_id: str  # UUID string


class GetPostResponse(BaseModel):
    """Get post response."""

    post_id: str
    title: str
    type: PostType
    author_id: str
    author_handle: str
    url: str | None
    text: str | None
    points: int
    comment_count: int
    created_at: datetime
    updated_at: datetime


class GetPostUseCase:
    """Use case for retrieving a post by ID."""

    def __init__(self, post_repository: PostRepository) -> None:
        """Initialize get post use case.

        Args:
            post_repository: Post repository
        """
        self.post_repository = post_repository

    async def execute(self, request: GetPostRequest) -> Optional[GetPostResponse]:
        """Execute get post flow.

        Args:
            request: Get post request with post ID

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

        return GetPostResponse(
            post_id=str(post.id),
            title=post.title,
            type=post.type,
            author_id=str(post.author_id),
            author_handle=post.author_handle.value,
            url=post.url,
            text=post.text,
            points=post.points,
            comment_count=post.comment_count,
            created_at=post.created_at,
            updated_at=post.updated_at,
        )
