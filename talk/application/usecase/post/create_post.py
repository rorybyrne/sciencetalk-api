"""Create post use case."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel

from talk.domain.model.post import Post
from talk.domain.repository import PostRepository
from talk.domain.value import PostId, PostType, UserId
from talk.domain.value.types import Handle


class CreatePostRequest(BaseModel):
    """Create post request."""

    title: str
    type: PostType
    author_id: str  # User ID from authenticated user
    author_handle: Handle  # Handle from authenticated user
    url: str | None = None
    text: str | None = None


class CreatePostResponse(BaseModel):
    """Create post response."""

    post_id: str
    title: str
    type: PostType
    points: int
    created_at: datetime


class CreatePostUseCase:
    """Use case for creating a new post."""

    def __init__(self, post_repository: PostRepository) -> None:
        """Initialize create post use case.

        Args:
            post_repository: Post repository
        """
        self.post_repository = post_repository

    async def execute(self, request: CreatePostRequest) -> CreatePostResponse:
        """Execute create post flow.

        Steps:
        1. Create Post entity (validation happens in domain model)
        2. Save post to repository

        Args:
            request: Create post request

        Returns:
            Create post response with post details

        Raises:
            ValueError: If post validation fails (type-content mismatch)
        """
        # Create post entity (Pydantic validation will enforce type-content rules)
        post = Post(
            id=PostId(uuid4()),
            title=request.title,
            type=request.type,
            author_id=UserId(UUID(request.author_id)),
            author_handle=request.author_handle,
            url=request.url,
            text=request.text,
            points=1,  # New posts start with 1 point
            comment_count=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            deleted_at=None,
        )

        # Save post
        saved_post = await self.post_repository.save(post)

        return CreatePostResponse(
            post_id=str(saved_post.id),
            title=saved_post.title,
            type=saved_post.type,
            points=saved_post.points,
            created_at=saved_post.created_at,
        )
