"""Get post use case."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from talk.domain.repository import PostRepository, VoteRepository
from talk.domain.value import PostId, Slug, UserId, VotableType
from talk.domain.value.types import Handle


class GetPostRequest(BaseModel):
    """Get post request.

    Accepts either post_id (UUID) or slug for lookup.
    """

    post_id: str | None = None  # UUID string (legacy)
    slug: str | None = None  # URL slug (preferred)
    user_id: str | None = None  # Current user ID (if authenticated)

    def model_post_init(self, __context):
        """Validate that either post_id or slug is provided."""
        if not self.post_id and not self.slug:
            raise ValueError("Either post_id or slug must be provided")
        if self.post_id and self.slug:
            raise ValueError("Provide either post_id or slug, not both")


class GetPostResponse(BaseModel):
    """Get post response."""

    post_id: str
    slug: str
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

        Supports lookups by both UUID (legacy) and slug (preferred).

        Args:
            request: Get post request with post ID or slug, and optional user ID

        Returns:
            Post details if found, None otherwise
        """
        # Find post by slug (preferred) or ID (legacy)
        if request.slug:
            post = await self.post_repository.find_by_slug(Slug(request.slug))
        else:
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
            slug=str(post.slug),
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
