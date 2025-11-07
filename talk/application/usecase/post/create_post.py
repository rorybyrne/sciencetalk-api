"""Create post use case."""

import logfire
from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel

from talk.domain.error import DomainError
from talk.domain.model.post import Post
from talk.domain.service import PostService, TagService
from talk.domain.value import PostId, TagName, UserId
from talk.domain.value.types import Handle


class CreatePostRequest(BaseModel):
    """Create post request."""

    title: str
    tag_names: list[str]  # Tag names (1-5 required)
    author_id: str  # User ID from authenticated user
    author_handle: Handle  # Handle from authenticated user
    url: str | None = None
    text: str | None = None


class CreatePostResponse(BaseModel):
    """Create post response."""

    post_id: str
    title: str
    tag_names: list[str]
    points: int
    created_at: datetime
    comments_updated_at: datetime
    content_updated_at: datetime


class CreatePostUseCase:
    """Use case for creating a new post."""

    def __init__(self, post_service: PostService, tag_service: TagService) -> None:
        """Initialize create post use case.

        Args:
            post_service: Post domain service
            tag_service: Tag domain service
        """
        self.post_service = post_service
        self.tag_service = tag_service

    async def execute(self, request: CreatePostRequest) -> CreatePostResponse:
        """Execute create post flow.

        Steps:
        1. Validate that all tags exist (via TagService)
        2. Create Post entity (validation happens in domain model)
        3. Save post (via PostService)

        Args:
            request: Create post request

        Returns:
            Create post response with post details

        Raises:
            DomainError: If tags don't exist or post validation fails
        """
        with logfire.span(
            "create_post.execute",
            title=request.title,
            tags=request.tag_names,
            author=request.author_handle.root,
        ):
            # Validate tag names and ensure they exist
            tag_name_objs = [TagName(name) for name in request.tag_names]

            try:
                # Validate tags exist (raises ValueError if any missing)
                await self.tag_service.validate_tags_exist(tag_name_objs)
            except ValueError as e:
                raise DomainError(str(e))

            # Create post entity (Pydantic validation will enforce content rules)
            now = datetime.now()
            post = Post(
                id=PostId(uuid4()),
                title=request.title,
                author_id=UserId(UUID(request.author_id)),
                author_handle=request.author_handle,
                url=request.url,
                text=request.text,
                tag_names=tag_name_objs,
                points=1,  # New posts start with 1 point
                comment_count=0,
                created_at=now,
                comments_updated_at=now,  # Initially same as created_at
                content_updated_at=now,  # Initially same as created_at
                deleted_at=None,
            )

            # Save post via service
            saved_post = await self.post_service.save_post(post)

            logfire.info("Post created successfully", post_id=str(saved_post.id))

            return CreatePostResponse(
                post_id=str(saved_post.id),
                title=saved_post.title,
                tag_names=[tag.root for tag in saved_post.tag_names],
                points=saved_post.points,
                created_at=saved_post.created_at,
                comments_updated_at=saved_post.comments_updated_at,
                content_updated_at=saved_post.content_updated_at,
            )
