"""Post routes."""

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Cookie, HTTPException, status
from pydantic import BaseModel, Field

from talk.application.usecase.auth import GetCurrentUserUseCase
from talk.application.usecase.auth.get_current_user import GetCurrentUserRequest
from talk.application.usecase.post import (
    CreatePostRequest,
    CreatePostResponse,
    CreatePostUseCase,
    GetPostRequest,
    GetPostResponse,
    GetPostUseCase,
    ListPostsRequest,
    ListPostsResponse,
    ListPostsUseCase,
)
from talk.domain.repository.post import PostSortOrder
from talk.domain.value import PostType
from talk.util.jwt import JWTError

router = APIRouter(prefix="/posts", tags=["posts"], route_class=DishkaRoute)


class CreatePostAPIRequest(BaseModel):
    """API request for creating a post."""

    title: str = Field(min_length=1, max_length=300)
    type: PostType
    url: str | None = None
    text: str | None = Field(default=None, max_length=10000)


@router.post(
    "/", response_model=CreatePostResponse, status_code=status.HTTP_201_CREATED
)
async def create_post(
    request: CreatePostAPIRequest,
    create_post_use_case: FromDishka[CreatePostUseCase],
    get_current_user_use_case: FromDishka[GetCurrentUserUseCase],
    auth_token: str | None = Cookie(default=None),
) -> CreatePostResponse:
    """Create a new post.

    Requires authentication.

    Args:
        request: Post creation data
        create_post_use_case: Create post use case from DI
        get_current_user_use_case: Get current user use case from DI
        auth_token: JWT token from cookie

    Returns:
        Created post details

    Raises:
        HTTPException: If not authenticated or validation fails
    """
    # Verify authentication
    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to create posts",
        )

    try:
        user = await get_current_user_use_case.execute(
            GetCurrentUserRequest(token=auth_token)
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    # Create post
    try:
        use_case_request = CreatePostRequest(
            title=request.title,
            type=request.type,
            author_id=user.user_id,
            author_handle=user.handle,
            url=request.url,
            text=request.text,
        )
        return await create_post_use_case.execute(use_case_request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{post_id}", response_model=GetPostResponse)
async def get_post(
    post_id: str,
    get_post_use_case: FromDishka[GetPostUseCase],
) -> GetPostResponse:
    """Get a post by ID.

    Args:
        post_id: Post UUID
        get_post_use_case: Get post use case from DI

    Returns:
        Post details

    Raises:
        HTTPException: If post not found
    """
    post = await get_post_use_case.execute(GetPostRequest(post_id=post_id))

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    return post


@router.get("/", response_model=ListPostsResponse)
async def list_posts(
    list_posts_use_case: FromDishka[ListPostsUseCase],
    sort: PostSortOrder = PostSortOrder.RECENT,
    post_type: PostType | None = None,
    limit: int = 30,
    offset: int = 0,
) -> ListPostsResponse:
    """List posts with filtering and pagination.

    Args:
        list_posts_use_case: List posts use case from DI
        sort: Sort order (recent or active)
        post_type: Filter by post type (optional)
        limit: Maximum number of posts to return (1-100)
        offset: Number of posts to skip

    Returns:
        List of posts
    """
    # Validate pagination
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be between 1 and 100",
        )
    if offset < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Offset must be non-negative",
        )

    request = ListPostsRequest(
        sort=sort,
        post_type=post_type,
        limit=limit,
        offset=offset,
    )

    return await list_posts_use_case.execute(request)
