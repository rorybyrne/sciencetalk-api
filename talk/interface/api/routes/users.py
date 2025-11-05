"""User profile routes."""

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Cookie, HTTPException, status
from pydantic import BaseModel, Field

from talk.application.usecase.user import (
    GetUserProfileUseCase,
    UpdateUserProfileUseCase,
)
from talk.application.usecase.user.get_user_profile import (
    GetUserProfileRequest,
    GetUserProfileResponse,
)
from talk.application.usecase.user.update_user_profile import (
    UpdateUserProfileRequest,
    UpdateUserProfileResponse,
)
from talk.domain.service import JWTService
from talk.domain.value.types import Handle
from talk.util.jwt import JWTError

router = APIRouter(prefix="/users", tags=["users"], route_class=DishkaRoute)


class UpdateUserProfileAPIRequest(BaseModel):
    """API request for updating user profile."""

    bio: str | None = Field(None, max_length=500)
    avatar_url: str | None = None
    email: str | None = None


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


@router.patch("/me", response_model=UpdateUserProfileResponse)
async def update_my_profile(
    request: UpdateUserProfileAPIRequest,
    update_user_profile_use_case: FromDishka[UpdateUserProfileUseCase],
    jwt_service: FromDishka[JWTService],
    auth_token: str | None = Cookie(default=None),
) -> UpdateUserProfileResponse:
    """Update current user's profile.

    Allows updating bio, avatar_url, and email.
    Handle and karma cannot be changed.

    Args:
        request: Profile update request with optional fields
        update_user_profile_use_case: Update user profile use case from DI
        jwt_service: JWT service from DI
        auth_token: JWT token from cookie

    Returns:
        Updated user profile information

    Raises:
        HTTPException: If not authenticated or update fails

    Example:
        PATCH /users/me
        Cookie: auth_token=...

        Request:
        {
            "bio": "Researcher in computational biology",
            "avatar_url": "https://example.com/avatar.jpg",
            "email": "researcher@example.com"
        }

        Response:
        {
            "user_id": "123e4567-e89b-12d3-a456-426614174000",
            "handle": "alice.bsky.social",
            "avatar_url": "https://example.com/avatar.jpg",
            "email": "researcher@example.com",
            "bio": "Researcher in computational biology",
            "karma": 42,
            "updated_at": "2025-01-15T12:34:56Z"
        }
    """
    # Authenticate user
    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        payload = jwt_service.verify_token(auth_token)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    # Execute use case
    try:
        use_case_request = UpdateUserProfileRequest(
            user_id=payload.user_id,
            bio=request.bio,
            avatar_url=request.avatar_url,
            email=request.email,
        )
        return await update_user_profile_use_case.execute(use_case_request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile",
        )
