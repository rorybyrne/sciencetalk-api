"""Update user profile use case."""

from datetime import datetime

from pydantic import BaseModel, Field

from talk.domain.service import UserService
from talk.domain.value import UserId


class UpdateUserProfileRequest(BaseModel):
    """Update user profile request."""

    user_id: str  # From authenticated user
    bio: str | None = Field(default=None, max_length=500)
    avatar_url: str | None = Field(default=None)
    email: str | None = Field(default=None)


class UpdateUserProfileResponse(BaseModel):
    """Update user profile response."""

    user_id: str
    handle: str
    avatar_url: str | None
    email: str | None
    bio: str | None
    karma: int
    updated_at: datetime


class UpdateUserProfileUseCase:
    """Use case for updating a user's profile.

    Users can update their bio, avatar URL, and email.
    Handle and karma cannot be changed through this endpoint.
    """

    def __init__(
        self,
        user_service: UserService,
    ) -> None:
        """Initialize update user profile use case.

        Args:
            user_service: User domain service
        """
        self.user_service = user_service

    async def execute(
        self, request: UpdateUserProfileRequest
    ) -> UpdateUserProfileResponse:
        """Execute update user profile flow.

        Steps:
        1. Get user by ID
        2. Update allowed fields
        3. Save updated user
        4. Return updated profile

        Args:
            request: Request with user ID and fields to update

        Returns:
            Updated user profile information

        Raises:
            ValueError: If user not found
        """
        from uuid import UUID

        user_id = UserId(UUID(request.user_id))

        # Get current user
        user = await self.user_service.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        # Update allowed fields (create new instance since Pydantic models are immutable)
        updated_user = user.model_copy(
            update={
                "bio": request.bio if request.bio is not None else user.bio,
                "avatar_url": request.avatar_url
                if request.avatar_url is not None
                else user.avatar_url,
                "email": request.email if request.email is not None else user.email,
                "updated_at": datetime.now(),
            }
        )

        # Save updated user
        saved_user = await self.user_service.save(updated_user)

        return UpdateUserProfileResponse(
            user_id=str(saved_user.id),
            handle=saved_user.handle.root,
            avatar_url=saved_user.avatar_url,
            email=saved_user.email,
            bio=saved_user.bio,
            karma=saved_user.karma,
            updated_at=saved_user.updated_at,
        )
