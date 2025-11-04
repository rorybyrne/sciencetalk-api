"""List posts use case."""

import logfire
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from talk.domain.repository import VoteRepository
from talk.domain.repository.post import PostRepository, PostSortOrder
from talk.domain.value import TagName, UserId, VotableType
from talk.domain.value.types import Handle


class PostListItem(BaseModel):
    """Post list item in response."""

    post_id: str
    title: str
    tag_names: list[str]
    author_id: str
    author_handle: Handle
    url: str | None
    points: int
    comment_count: int
    created_at: datetime
    has_voted: bool


class ListPostsRequest(BaseModel):
    """List posts request."""

    sort: PostSortOrder = PostSortOrder.RECENT
    tag: str | None = None  # Filter by tag name
    limit: int = Field(default=30, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    user_id: str | None = None  # Current user ID (if authenticated)


class ListPostsResponse(BaseModel):
    """List posts response."""

    posts: list[PostListItem]
    total: int
    limit: int
    offset: int


class ListPostsUseCase:
    """Use case for listing posts with filtering and pagination."""

    def __init__(
        self, post_repository: PostRepository, vote_repository: VoteRepository
    ) -> None:
        """Initialize list posts use case.

        Args:
            post_repository: Post repository
            vote_repository: Vote repository
        """
        self.post_repository = post_repository
        self.vote_repository = vote_repository

    async def execute(self, request: ListPostsRequest) -> ListPostsResponse:
        """Execute list posts flow.

        Args:
            request: List posts request with filters and pagination

        Returns:
            List of posts matching criteria
        """
        with logfire.span(
            "list_posts.execute",
            sort=request.sort.value,
            tag=request.tag,
            limit=request.limit,
            offset=request.offset,
        ):
            # Convert tag string to TagName if provided
            tag_filter = TagName(request.tag) if request.tag else None

            # Fetch total count and posts in parallel
            total = await self.post_repository.count(
                tag=tag_filter,
                include_deleted=False,  # Never show deleted posts
            )

            posts = await self.post_repository.find_all(
                sort=request.sort,
                tag=tag_filter,
                include_deleted=False,  # Never show deleted posts
                limit=request.limit,
                offset=request.offset,
            )

            # Get user's votes for these posts (if authenticated)
            user_votes = {}
            if request.user_id:
                user_id = UserId(UUID(request.user_id))
                for post in posts:
                    vote = await self.vote_repository.find_by_user_and_votable(
                        user_id=user_id,
                        votable_type=VotableType.POST,
                        votable_id=post.id,
                    )
                    user_votes[str(post.id)] = vote is not None

            # Convert to response items
            post_items = [
                PostListItem(
                    post_id=str(post.id),
                    title=post.title,
                    tag_names=[tag.root for tag in post.tag_names],
                    author_id=str(post.author_id),
                    author_handle=post.author_handle,
                    url=post.url,
                    points=post.points,
                    comment_count=post.comment_count,
                    created_at=post.created_at,
                    has_voted=user_votes.get(str(post.id), False),
                )
                for post in posts
            ]

            logfire.info("Posts listed", count=len(post_items), total=total)

            return ListPostsResponse(
                posts=post_items,
                total=total,
                limit=request.limit,
                offset=request.offset,
            )
