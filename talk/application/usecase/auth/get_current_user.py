"""Get current user use case."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from talk.domain.repository import UserRepository
from talk.domain.service import JWTService
from talk.domain.value import UserId


class GetCurrentUserRequest(BaseModel):
    """Get current user request."""

    token: str  # JWT token


class GetCurrentUserResponse(BaseModel):
    """Get current user response."""

    user_id: str
    bluesky_did: str
    handle: str
    display_name: str | None
    avatar_url: str | None
    karma: int


class GetCurrentUserUseCase:
    """Use case for getting current authenticated user."""

    def __init__(
        self,
        jwt_service: JWTService,
        user_repository: UserRepository,
    ) -> None:
        """Initialize get current user use case.

        Args:
            jwt_service: JWT token domain service
            user_repository: User repository
        """
        self.jwt_service = jwt_service
        self.user_repository = user_repository

    async def execute(
        self, request: GetCurrentUserRequest
    ) -> Optional[GetCurrentUserResponse]:
        """Execute get current user flow.

        Steps:
        1. Verify JWT token via JWT service
        2. Extract user_id from token
        3. Load user from database
        4. Return user info

        Args:
            request: Request with JWT token

        Returns:
            User information if token is valid and user exists, None otherwise

        Raises:
            JWTError: If token is invalid or expired
        """
        # Verify token (raises JWTError if invalid)
        payload = self.jwt_service.verify_token(request.token)

        # Load user from database
        user = await self.user_repository.find_by_id(UserId(UUID(payload.user_id)))

        if not user:
            return None

        return GetCurrentUserResponse(
            user_id=str(user.id),
            bluesky_did=user.bluesky_did.value,
            handle=user.handle.value,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            karma=user.karma,
        )
