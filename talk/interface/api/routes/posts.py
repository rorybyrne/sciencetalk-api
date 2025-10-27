"""Post routes."""

import logging
from uuid import UUID

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

logger = logging.getLogger(__name__)

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
        logger.info(
            f"Creating post: title='{request.title}', type={request.type}, "
            f"author={user.handle}"
        )

        use_case_request = CreatePostRequest(
            title=request.title,
            type=request.type,
            author_id=user.user_id,
            author_handle=user.handle,
            url=request.url,
            text=request.text,
        )

        result = await create_post_use_case.execute(use_case_request)
        logger.info(f"Post created successfully: post_id={result.post_id}")
        return result

    except ValueError as e:
        logger.error(f"Post creation validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(f"Unexpected error creating post: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create post",
        )


@router.get("/{post_id}", response_model=GetPostResponse)
async def get_post(
    post_id: UUID,
    get_post_use_case: FromDishka[GetPostUseCase],
    get_current_user_use_case: FromDishka[GetCurrentUserUseCase],
    auth_token: str | None = Cookie(default=None),
) -> GetPostResponse:
    """Get a post by ID.

    Args:
        post_id: Post UUID
        get_post_use_case: Get post use case from DI
        get_current_user_use_case: Get current user use case from DI
        auth_token: JWT token from cookie (optional)

    Returns:
        Post details

    Raises:
        HTTPException: If post not found or invalid UUID
    """
    logger.info(f"Fetching post: post_id={post_id}")

    # Get current user ID if authenticated
    user_id = None
    if auth_token:
        try:
            user = await get_current_user_use_case.execute(
                GetCurrentUserRequest(token=auth_token)
            )
            if user:
                user_id = user.user_id
        except JWTError:
            # Invalid token, treat as unauthenticated
            pass

    try:
        post = await get_post_use_case.execute(
            GetPostRequest(post_id=str(post_id), user_id=user_id)
        )

        if not post:
            logger.warning(f"Post not found: post_id={post_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found",
            )

        logger.debug(f"Post found: post_id={post_id}, title='{post.title}'")
        return post

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error fetching post {post_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch post",
        )


@router.get("/", response_model=ListPostsResponse)
async def list_posts(
    list_posts_use_case: FromDishka[ListPostsUseCase],
    get_current_user_use_case: FromDishka[GetCurrentUserUseCase],
    sort: PostSortOrder = PostSortOrder.RECENT,
    post_type: PostType | None = None,
    limit: int = 30,
    offset: int = 0,
    auth_token: str | None = Cookie(default=None),
) -> ListPostsResponse:
    """List posts with filtering and pagination.

    Args:
        list_posts_use_case: List posts use case from DI
        get_current_user_use_case: Get current user use case from DI
        sort: Sort order (recent or active)
        post_type: Filter by post type (optional)
        limit: Maximum number of posts to return (1-100)
        offset: Number of posts to skip
        auth_token: JWT token from cookie (optional)

    Returns:
        List of posts
    """
    logger.info(
        f"Listing posts: sort={sort}, post_type={post_type}, "
        f"limit={limit}, offset={offset}"
    )

    # Get current user ID if authenticated
    user_id = None
    if auth_token:
        try:
            user = await get_current_user_use_case.execute(
                GetCurrentUserRequest(token=auth_token)
            )
            if user:
                user_id = user.user_id
        except JWTError:
            # Invalid token, treat as unauthenticated
            pass

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
        user_id=user_id,
    )

    try:
        result = await list_posts_use_case.execute(request)
        has_more = (result.offset + len(result.posts)) < result.total
        logger.info(
            f"Listed posts: returned {len(result.posts)} posts, "
            f"total={result.total}, offset={result.offset}, has_more={has_more}"
        )
        return result

    except Exception as e:
        logger.exception(f"Unexpected error listing posts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list posts",
        )
