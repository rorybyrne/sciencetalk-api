"""Comment routes."""

import logfire
from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Cookie, HTTPException, status
from pydantic import BaseModel, Field

from talk.application.usecase.comment import (
    CreateCommentRequest,
    CreateCommentResponse,
    CreateCommentUseCase,
    GetCommentsRequest,
    GetCommentsResponse,
    GetCommentsUseCase,
    UpdateCommentRequest,
    UpdateCommentResponse,
    UpdateCommentUseCase,
)
from talk.domain.error import ContentDeletedException, NotAuthorizedError, NotFoundError
from talk.domain.service import JWTService

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
    jwt_service: FromDishka[JWTService],
    auth_token: str | None = Cookie(default=None),
) -> CreateCommentResponse:
    """Create a comment on a post or reply to another comment.

    Requires authentication.

    Args:
        post_id: Post UUID
        request: Comment creation data
        create_comment_use_case: Create comment use case from DI
        jwt_service: JWT service for token verification (injected)
        auth_token: JWT token from cookie

    Returns:
        Created comment details

    Raises:
        HTTPException: If not authenticated or validation fails
    """
    # Verify authentication and get user ID
    user_id = jwt_service.get_user_id_from_token(auth_token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to create comments",
        )

    # Create comment
    try:
        use_case_request = CreateCommentRequest(
            post_id=post_id,
            text=request.text,
            author_id=user_id,
            parent_id=request.parent_id,
        )
        return await create_comment_use_case.execute(use_case_request)
    except NotFoundError as e:
        logfire.warn("Comment creation failed - user not found", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


class UpdateCommentAPIRequest(BaseModel):
    """API request for updating a comment."""

    text: str = Field(min_length=1, max_length=10000)


@router.patch("/{post_id}/comments/{comment_id}", response_model=UpdateCommentResponse)
async def update_comment(
    post_id: str,
    comment_id: str,
    request: UpdateCommentAPIRequest,
    update_comment_use_case: FromDishka[UpdateCommentUseCase],
    jwt_service: FromDishka[JWTService],
    auth_token: str | None = Cookie(default=None),
) -> UpdateCommentResponse:
    """Update a comment's text content.

    Only the comment author can edit.

    Args:
        post_id: Post UUID
        comment_id: Comment UUID
        request: Update data (text content)
        update_comment_use_case: Update comment use case from DI
        jwt_service: JWT service for token verification (injected)
        auth_token: JWT token from cookie

    Returns:
        Updated comment details

    Raises:
        HTTPException: If not authenticated, not authorized, or validation fails
    """
    # Verify authentication and get user ID
    user_id = jwt_service.get_user_id_from_token(auth_token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to edit comments",
        )

    # Update comment
    try:
        use_case_request = UpdateCommentRequest(
            comment_id=comment_id,
            post_id=post_id,
            user_id=user_id,
            text=request.text,
        )

        result = await update_comment_use_case.execute(use_case_request)
        return result

    except NotAuthorizedError as e:
        logfire.warn("Unauthorized comment update attempt", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to edit this comment",
        )
    except ContentDeletedException as e:
        logfire.warn("Attempt to edit deleted comment", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment or post not found or has been deleted",
        )
    except ValueError as e:
        logfire.warn("Comment update validation error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logfire.error("Unexpected error updating comment", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update comment",
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
