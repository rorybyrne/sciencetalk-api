"""List posts use case."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from talk.domain.repository import VoteRepository
from talk.domain.repository.post import PostRepository, PostSortOrder
from talk.domain.value import PostType, UserId, VotableType
from talk.domain.value.types import Handle


class PostListItem(BaseModel):
    """Post list item in response."""

    post_id: str
    title: str
    type: PostType
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
    post_type: PostType | None = None
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
        # Fetch posts with filters
        posts = await self.post_repository.find_all(
            sort=request.sort,
            post_type=request.post_type,
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
                type=post.type,
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

        return ListPostsResponse(
            posts=post_items,
            total=len(post_items),  # TODO: Add count query to repository
            limit=request.limit,
            offset=request.offset,
        )
