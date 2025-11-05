"""Get user profile use case."""

from datetime import datetime

from pydantic import BaseModel

from talk.domain.service import UserIdentityService, UserService
from talk.domain.value import AuthProvider
from talk.domain.value.types import Handle


class GetUserProfileRequest(BaseModel):
    """Get user profile request."""

    handle: Handle


class UserIdentityInfo(BaseModel):
    """User identity information for response."""

    provider: AuthProvider
    provider_handle: str
    is_primary: bool


class GetUserProfileResponse(BaseModel):
    """Get user profile response."""

    user_id: str
    handle: Handle
    avatar_url: str | None
    email: str | None
    bio: str | None
    karma: int
    created_at: datetime
    identities: list[UserIdentityInfo]


class GetUserProfileUseCase:
    """Use case for getting a user's public profile by handle."""

    def __init__(
        self,
        user_service: UserService,
        user_identity_service: UserIdentityService,
    ) -> None:
        """Initialize get user profile use case.

        Args:
            user_service: User domain service
            user_identity_service: User identity domain service
        """
        self.user_service = user_service
        self.user_identity_service = user_identity_service

    async def execute(
        self, request: GetUserProfileRequest
    ) -> GetUserProfileResponse | None:
        """Execute get user profile flow.

        Steps:
        1. Get user by handle via user service
        2. Get user's linked identities
        3. Return public profile info with identities

        Args:
            request: Request with user handle

        Returns:
            User profile information if user exists, None otherwise
        """
        # Get user by handle
        user = await self.user_service.get_user_by_handle(request.handle)

        if not user:
            return None

        # Get user's linked identities
        identities = await self.user_identity_service.get_all_identities_for_user(
            user.id
        )

        return GetUserProfileResponse(
            user_id=str(user.id),
            handle=user.handle,
            avatar_url=user.avatar_url,
            email=user.email,
            bio=user.bio,
            karma=user.karma,
            created_at=user.created_at,
            identities=[
                UserIdentityInfo(
                    provider=identity.provider,
                    provider_handle=identity.provider_handle,
                    is_primary=identity.is_primary,
                )
                for identity in identities
            ],
        )
