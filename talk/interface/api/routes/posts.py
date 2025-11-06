"""Post routes."""

import logfire
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
    UpdatePostRequest,
    UpdatePostResponse,
    UpdatePostUseCase,
)
from talk.domain.error import (
    ContentDeletedException,
    DomainError,
    InvalidEditOperationError,
    NotAuthorizedError,
)
from talk.domain.repository.post import PostSortOrder
from talk.util.jwt import JWTError

router = APIRouter(prefix="/posts", tags=["posts"], route_class=DishkaRoute)


class CreatePostAPIRequest(BaseModel):
    """API request for creating a post."""

    title: str = Field(min_length=1, max_length=300)
    tag_names: list[str] = Field(min_length=1, max_length=5)
    url: str | None = None
    text: str | None = Field(default=None, max_length=10000)


@router.post("", response_model=CreatePostResponse, status_code=status.HTTP_201_CREATED)
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
            tag_names=request.tag_names,
            author_id=user.user_id,
            author_handle=user.handle,
            url=request.url,
            text=request.text,
        )

        result = await create_post_use_case.execute(use_case_request)
        return result

    except DomainError as e:
        logfire.warn("Post creation domain error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except ValueError as e:
        logfire.warn("Post creation validation error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logfire.error("Unexpected error creating post", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create post",
        )


class UpdatePostAPIRequest(BaseModel):
    """API request for updating a post."""

    text: str | None = Field(default=None, max_length=10000)


@router.patch("/{post_id}", response_model=UpdatePostResponse)
async def update_post(
    post_id: UUID,
    request: UpdatePostAPIRequest,
    update_post_use_case: FromDishka[UpdatePostUseCase],
    get_current_user_use_case: FromDishka[GetCurrentUserUseCase],
    auth_token: str | None = Cookie(default=None),
) -> UpdatePostResponse:
    """Update a post's text content.

    Only the post author can edit. Only text-based posts (Discussion, Ask) can have text edited.

    Args:
        post_id: Post UUID
        request: Update data (text content)
        update_post_use_case: Update post use case from DI
        get_current_user_use_case: Get current user use case from DI
        auth_token: JWT token from cookie

    Returns:
        Updated post details

    Raises:
        HTTPException: If not authenticated, not authorized, or validation fails
    """
    # Verify authentication
    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to edit posts",
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

    # Update post
    try:
        use_case_request = UpdatePostRequest(
            post_id=str(post_id),
            user_id=user.user_id,
            text=request.text,
        )

        result = await update_post_use_case.execute(use_case_request)
        return result

    except NotAuthorizedError as e:
        logfire.warn("Unauthorized post update attempt", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to edit this post",
        )
    except ContentDeletedException as e:
        logfire.warn("Attempt to edit deleted post", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found or has been deleted",
        )
    except InvalidEditOperationError as e:
        logfire.warn("Invalid edit operation", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except ValueError as e:
        logfire.warn("Post update validation error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logfire.error("Unexpected error updating post", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update post",
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
            logfire.warn("Post not found", post_id=str(post_id))
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found",
            )

        return post

    except HTTPException:
        raise
    except Exception as e:
        logfire.error(
            "Unexpected error fetching post", post_id=str(post_id), error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch post",
        )


@router.get("", response_model=ListPostsResponse)
async def list_posts(
    list_posts_use_case: FromDishka[ListPostsUseCase],
    get_current_user_use_case: FromDishka[GetCurrentUserUseCase],
    sort: PostSortOrder = PostSortOrder.RECENT,
    tag: str | None = None,
    limit: int = 30,
    offset: int = 0,
    auth_token: str | None = Cookie(default=None),
) -> ListPostsResponse:
    """List posts with filtering and pagination.

    Args:
        list_posts_use_case: List posts use case from DI
        get_current_user_use_case: Get current user use case from DI
        sort: Sort order (recent or active)
        tag: Filter by tag name (optional)
        limit: Maximum number of posts to return (1-100)
        offset: Number of posts to skip
        auth_token: JWT token from cookie (optional)

    Returns:
        List of posts
    """

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
        tag=tag,
        limit=limit,
        offset=offset,
        user_id=user_id,
    )

    try:
        result = await list_posts_use_case.execute(request)
        return result

    except ValueError as e:
        logfire.warn("List posts validation error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logfire.error("Unexpected error listing posts", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list posts",
        )
