"""Comment routes."""

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Cookie, HTTPException, status
from pydantic import BaseModel, Field

from talk.application.usecase.auth import GetCurrentUserUseCase
from talk.application.usecase.auth.get_current_user import GetCurrentUserRequest
from talk.application.usecase.comment import (
    CreateCommentRequest,
    CreateCommentResponse,
    CreateCommentUseCase,
    GetCommentsRequest,
    GetCommentsResponse,
    GetCommentsUseCase,
)
from talk.util.jwt import JWTError

router = APIRouter(prefix="/posts", tags=["comments"], route_class=DishkaRoute)


class CreateCommentAPIRequest(BaseModel):
    """API request for creating a comment."""

    text: str = Field(min_length=1, max_length=10000)
    parent_id: str | None = None  # Parent comment ID for replies


@router.post(
    "/{post_id}/comments",
    response_model=CreateCommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment(
    post_id: str,
    request: CreateCommentAPIRequest,
    create_comment_use_case: FromDishka[CreateCommentUseCase],
    get_current_user_use_case: FromDishka[GetCurrentUserUseCase],
    auth_token: str | None = Cookie(default=None),
) -> CreateCommentResponse:
    """Create a comment on a post or reply to another comment.

    Requires authentication.

    Args:
        post_id: Post UUID
        request: Comment creation data
        create_comment_use_case: Create comment use case from DI
        get_current_user_use_case: Get current user use case from DI
        auth_token: JWT token from cookie

    Returns:
        Created comment details

    Raises:
        HTTPException: If not authenticated or validation fails
    """
    # Verify authentication
    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to create comments",
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

    # Create comment
    try:
        use_case_request = CreateCommentRequest(
            post_id=post_id,
            text=request.text,
            author_id=user.user_id,
            author_handle=user.handle,
            parent_id=request.parent_id,
        )
        return await create_comment_use_case.execute(use_case_request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{post_id}/comments", response_model=GetCommentsResponse)
async def get_comments(
    post_id: str,
    get_comments_use_case: FromDishka[GetCommentsUseCase],
    auth_token: str | None = Cookie(default=None),
) -> GetCommentsResponse:
    """Get all comments for a post in tree order.

    Comments are returned in tree order (using ltree path)
    for efficient rendering of threaded discussions.

    If authenticated, includes vote state for each comment.

    Args:
        post_id: Post UUID
        get_comments_use_case: Get comments use case from DI
        auth_token: JWT token from cookie (optional)

    Returns:
        List of comments in tree order with vote state
    """
    request = GetCommentsRequest(post_id=post_id, auth_token=auth_token)
    return await get_comments_use_case.execute(request)
