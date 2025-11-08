"""Vote routes."""

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Cookie, HTTPException, status

from talk.application.usecase.vote import (
    RemoveVoteRequest,
    RemoveVoteResponse,
    RemoveVoteUseCase,
    UpvoteRequest,
    UpvoteResponse,
    UpvoteUseCase,
)
from talk.domain.service import JWTService
from talk.domain.value import VotableType

router = APIRouter(tags=["votes"], route_class=DishkaRoute)


@router.post("/posts/{post_id}/vote", response_model=UpvoteResponse)
async def upvote_post(
    post_id: str,
    upvote_use_case: FromDishka[UpvoteUseCase],
    jwt_service: FromDishka[JWTService],
    auth_token: str | None = Cookie(default=None),
) -> UpvoteResponse:
    """Upvote a post.

    Requires authentication.

    Args:
        post_id: Post UUID
        upvote_use_case: Upvote use case from DI
        jwt_service: JWT service for token verification (injected)
        auth_token: JWT token from cookie

    Returns:
        Vote details

    Raises:
        HTTPException: If not authenticated, already voted, or post not found
    """
    # Verify authentication and get user ID
    user_id = jwt_service.get_user_id_from_token(auth_token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to vote",
        )

    # Upvote post
    try:
        request = UpvoteRequest(
            votable_type=VotableType.POST,
            votable_id=post_id,
            user_id=user_id,
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
    jwt_service: FromDishka[JWTService],
    auth_token: str | None = Cookie(default=None),
) -> RemoveVoteResponse:
    """Remove vote from a post.

    Requires authentication.

    Args:
        post_id: Post UUID
        remove_vote_use_case: Remove vote use case from DI
        jwt_service: JWT service for token verification (injected)
        auth_token: JWT token from cookie

    Returns:
        Success status

    Raises:
        HTTPException: If not authenticated or post not found
    """
    # Verify authentication and get user ID
    user_id = jwt_service.get_user_id_from_token(auth_token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to remove vote",
        )

    # Remove vote
    try:
        request = RemoveVoteRequest(
            votable_type=VotableType.POST,
            votable_id=post_id,
            user_id=user_id,
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
    jwt_service: FromDishka[JWTService],
    auth_token: str | None = Cookie(default=None),
) -> UpvoteResponse:
    """Upvote a comment.

    Requires authentication.

    Args:
        comment_id: Comment UUID
        upvote_use_case: Upvote use case from DI
        jwt_service: JWT service for token verification (injected)
        auth_token: JWT token from cookie

    Returns:
        Vote details

    Raises:
        HTTPException: If not authenticated, already voted, or comment not found
    """
    # Verify authentication and get user ID
    user_id = jwt_service.get_user_id_from_token(auth_token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to vote",
        )

    # Upvote comment
    try:
        request = UpvoteRequest(
            votable_type=VotableType.COMMENT,
            votable_id=comment_id,
            user_id=user_id,
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
    jwt_service: FromDishka[JWTService],
    auth_token: str | None = Cookie(default=None),
) -> RemoveVoteResponse:
    """Remove vote from a comment.

    Requires authentication.

    Args:
        comment_id: Comment UUID
        remove_vote_use_case: Remove vote use case from DI
        jwt_service: JWT service for token verification (injected)
        auth_token: JWT token from cookie

    Returns:
        Success status

    Raises:
        HTTPException: If not authenticated or comment not found
    """
    # Verify authentication and get user ID
    user_id = jwt_service.get_user_id_from_token(auth_token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to remove vote",
        )

    # Remove vote
    try:
        request = RemoveVoteRequest(
            votable_type=VotableType.COMMENT,
            votable_id=comment_id,
            user_id=user_id,
        )
        return await remove_vote_use_case.execute(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
