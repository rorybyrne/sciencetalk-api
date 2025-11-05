"""Get current user use case."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from talk.domain.repository import UserRepository
from talk.domain.service import InviteService, JWTService
from talk.domain.value import UserId
from talk.domain.value.types import Handle, InviteStatus


class GetCurrentUserRequest(BaseModel):
    """Get current user request."""

    token: str  # JWT token


class InviteInfo(BaseModel):
    """Invite information for response."""

    id: str
    invitee_handle: str
    status: InviteStatus  # "pending" or "accepted"
    created_at: datetime
    accepted_at: datetime | None


class GetCurrentUserResponse(BaseModel):
    """Get current user response."""

    user_id: str
    handle: Handle
    avatar_url: str | None
    email: str | None
    bio: str | None
    karma: int
    created_at: datetime
    invite_quota: int
    invitations: list[InviteInfo]


class GetCurrentUserUseCase:
    """Use case for getting current authenticated user."""

    def __init__(
        self,
        jwt_service: JWTService,
        user_repository: UserRepository,
        invite_service: InviteService,
    ) -> None:
        """Initialize get current user use case.

        Args:
            jwt_service: JWT token domain service
            user_repository: User repository
            invite_service: Invite domain service
        """
        self.jwt_service = jwt_service
        # TODO: use service, not repository
        self.user_repository = user_repository
        self.invite_service = invite_service

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

        # Load user's invitations
        invites = await self.invite_service.list_invites(user.id)

        return GetCurrentUserResponse(
            user_id=str(user.id),
            handle=user.handle,
            avatar_url=user.avatar_url,
            email=user.email,
            bio=user.bio,
            karma=user.karma,
            created_at=user.created_at,
            invite_quota=user.invite_quota,
            invitations=[
                InviteInfo(
                    id=str(invite.id),
                    invitee_handle=invite.invitee_handle,
                    status=invite.status,
                    created_at=invite.created_at,
                    accepted_at=invite.accepted_at,
                )
                for invite in invites
            ],
        )
