"""Vote routes."""

from dishka.integrations.fastapi import FromDishka
from fastapi import APIRouter, Cookie, HTTPException, status

from talk.application.usecase.auth import GetCurrentUserUseCase
from talk.application.usecase.auth.get_current_user import GetCurrentUserRequest
from talk.application.usecase.vote import (
    RemoveVoteRequest,
    RemoveVoteResponse,
    RemoveVoteUseCase,
    UpvoteRequest,
    UpvoteResponse,
    UpvoteUseCase,
)
from talk.domain.value import VotableType
from talk.util.jwt import JWTError

router = APIRouter(tags=["votes"])


@router.post("/posts/{post_id}/vote", response_model=UpvoteResponse)
async def upvote_post(
    post_id: str,
    upvote_use_case: FromDishka[UpvoteUseCase],
    get_current_user_use_case: FromDishka[GetCurrentUserUseCase],
    auth_token: str | None = Cookie(default=None),
) -> UpvoteResponse:
    """Upvote a post.

    Requires authentication.

    Args:
        post_id: Post UUID
        upvote_use_case: Upvote use case from DI
        get_current_user_use_case: Get current user use case from DI
        auth_token: JWT token from cookie

    Returns:
        Vote details

    Raises:
        HTTPException: If not authenticated, already voted, or post not found
    """
    # Verify authentication
    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to vote",
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

    # Upvote post
    try:
        request = UpvoteRequest(
            votable_type=VotableType.POST,
            votable_id=post_id,
            user_id=user.user_id,
        )
        return await upvote_use_case.execute(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/posts/{post_id}/vote", response_model=RemoveVoteResponse)
async def remove_vote_from_post(
    post_id: str,
    remove_vote_use_case: FromDishka[RemoveVoteUseCase],
    get_current_user_use_case: FromDishka[GetCurrentUserUseCase],
    auth_token: str | None = Cookie(default=None),
) -> RemoveVoteResponse:
    """Remove vote from a post.

    Requires authentication.

    Args:
        post_id: Post UUID
        remove_vote_use_case: Remove vote use case from DI
        get_current_user_use_case: Get current user use case from DI
        auth_token: JWT token from cookie

    Returns:
        Success status

    Raises:
        HTTPException: If not authenticated or post not found
    """
    # Verify authentication
    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to remove vote",
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

    # Remove vote
    try:
        request = RemoveVoteRequest(
            votable_type=VotableType.POST,
            votable_id=post_id,
            user_id=user.user_id,
        )
        return await remove_vote_use_case.execute(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/comments/{comment_id}/vote", response_model=UpvoteResponse)
async def upvote_comment(
    comment_id: str,
    upvote_use_case: FromDishka[UpvoteUseCase],
    get_current_user_use_case: FromDishka[GetCurrentUserUseCase],
    auth_token: str | None = Cookie(default=None),
) -> UpvoteResponse:
    """Upvote a comment.

    Requires authentication.

    Args:
        comment_id: Comment UUID
        upvote_use_case: Upvote use case from DI
        get_current_user_use_case: Get current user use case from DI
        auth_token: JWT token from cookie

    Returns:
        Vote details

    Raises:
        HTTPException: If not authenticated, already voted, or comment not found
    """
    # Verify authentication
    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to vote",
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

    # Upvote comment
    try:
        request = UpvoteRequest(
            votable_type=VotableType.COMMENT,
            votable_id=comment_id,
            user_id=user.user_id,
        )
        return await upvote_use_case.execute(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/comments/{comment_id}/vote", response_model=RemoveVoteResponse)
async def remove_vote_from_comment(
    comment_id: str,
    remove_vote_use_case: FromDishka[RemoveVoteUseCase],
    get_current_user_use_case: FromDishka[GetCurrentUserUseCase],
    auth_token: str | None = Cookie(default=None),
) -> RemoveVoteResponse:
    """Remove vote from a comment.

    Requires authentication.

    Args:
        comment_id: Comment UUID
        remove_vote_use_case: Remove vote use case from DI
        get_current_user_use_case: Get current user use case from DI
        auth_token: JWT token from cookie

    Returns:
        Success status

    Raises:
        HTTPException: If not authenticated or comment not found
    """
    # Verify authentication
    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to remove vote",
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

    # Remove vote
    try:
        request = RemoveVoteRequest(
            votable_type=VotableType.COMMENT,
            votable_id=comment_id,
            user_id=user.user_id,
        )
        return await remove_vote_use_case.execute(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
