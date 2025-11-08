"""Create post use case."""

import logfire
from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel

from talk.domain.error import DomainError
from talk.domain.model.post import Post
from talk.domain.service import PostService, TagService, UserService
from talk.domain.value import PostId, TagName, UserId


class CreatePostRequest(BaseModel):
    """Create post request."""

    title: str
    tag_names: list[str]  # Tag names (1-5 required)
    author_id: str  # User ID from authenticated user
    url: str | None = None
    text: str | None = None


class CreatePostResponse(BaseModel):
    """Create post response."""

    post_id: str
    slug: str
    title: str
    tag_names: list[str]
    points: int
    created_at: datetime
    comments_updated_at: datetime
    content_updated_at: datetime


class CreatePostUseCase:
    """Use case for creating a new post."""

    def __init__(
        self,
        post_service: PostService,
        tag_service: TagService,
        user_service: UserService,
    ) -> None:
        """Initialize create post use case.

        Args:
            post_service: Post domain service
            tag_service: Tag domain service
            user_service: User domain service
        """
        self.post_service = post_service
        self.tag_service = tag_service
        self.user_service = user_service

    async def execute(self, request: CreatePostRequest) -> CreatePostResponse:
        """Execute create post flow.

        Steps:
        1. Load user to get handle (via UserService)
        2. Validate that all tags exist (via TagService)
        3. Generate unique slug from title (via PostService)
        4. Create Post entity (validation happens in domain model)
        5. Save post (via PostService)

        Args:
            request: Create post request

        Returns:
            Create post response with post details

        Raises:
            NotFoundError: If user not found
            DomainError: If tags don't exist or post validation fails
        """
        # Load user to get handle
        author_id = UserId(UUID(request.author_id))
        user = await self.user_service.get_by_id(author_id)  # Raises NotFoundError

        with logfire.span(
            "create_post.execute",
            title=request.title,
            tags=request.tag_names,
            author=user.handle.root,
        ):
            # Validate tag names and ensure they exist
            tag_name_objs = [TagName(name) for name in request.tag_names]

            try:
                # Validate tags exist (raises ValueError if any missing)
                await self.tag_service.validate_tags_exist(tag_name_objs)
            except ValueError as e:
                raise DomainError(str(e))

            # Generate unique slug from title
            post_id = PostId(uuid4())
            slug = await self.post_service.generate_unique_slug(request.title, post_id)
            logfire.info(
                "Generated slug for post", slug=str(slug), post_id=str(post_id)
            )

            # Create post entity (Pydantic validation will enforce content rules)
            now = datetime.now()
            post = Post(
                id=post_id,
                slug=slug,
                title=request.title,
                author_id=author_id,
                author_handle=user.handle,
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

            logfire.info(
                "Post created successfully",
                post_id=str(saved_post.id),
                slug=str(saved_post.slug),
            )

            return CreatePostResponse(
                post_id=str(saved_post.id),
                slug=str(saved_post.slug),
                title=saved_post.title,
                tag_names=[tag.root for tag in saved_post.tag_names],
                points=saved_post.points,
                created_at=saved_post.created_at,
                comments_updated_at=saved_post.comments_updated_at,
                content_updated_at=saved_post.content_updated_at,
            )
