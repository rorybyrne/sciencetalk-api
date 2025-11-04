"""User profile routes."""

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, HTTPException, status

from talk.application.usecase.user import GetUserProfileUseCase
from talk.application.usecase.user.get_user_profile import (
    GetUserProfileRequest,
    GetUserProfileResponse,
)
from talk.domain.value.types import Handle

router = APIRouter(prefix="/users", tags=["users"], route_class=DishkaRoute)


@router.get("/{handle}", response_model=GetUserProfileResponse)
async def get_user_profile(
    handle: str,
    get_user_profile_use_case: FromDishka[GetUserProfileUseCase],
) -> GetUserProfileResponse:
    """Get user profile by handle.

    Args:
        handle: Bluesky handle (e.g., "alice.bsky.social")
        get_user_profile_use_case: Get user profile use case from DI

    Returns:
        User profile information

    Raises:
        HTTPException: If user not found

    Example:
        GET /users/alice.bsky.social

        Response:
        {
            "user_id": "123e4567-e89b-12d3-a456-426614174000",
            "handle": "alice.bsky.social",
            "display_name": "Alice",
            "avatar_url": "https://...",
            "karma": 42,
            "created_at": "2025-01-15T12:34:56Z"
        }
    """
    # Execute use case
    user_profile = await get_user_profile_use_case.execute(
        GetUserProfileRequest(handle=Handle(handle))
    )

    if not user_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with handle '{handle}' not found",
        )

    return user_profile
