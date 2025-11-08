"""Get current user use case."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from talk.domain.service import (
    InviteService,
    JWTService,
    UserIdentityService,
    UserService,
)
from talk.domain.value import AuthProvider, UserId
from talk.domain.value.types import Handle, InviteStatus


class GetCurrentUserRequest(BaseModel):
    """Get current user request."""

    token: str  # JWT token


class InviteInfo(BaseModel):
    """Invite information for response."""

    id: str
    provider: AuthProvider  # Target authentication provider
    invitee_handle: str
    status: InviteStatus  # "pending" or "accepted"
    created_at: datetime
    accepted_at: datetime | None


class UserIdentityInfo(BaseModel):
    """User identity information for response."""

    provider: AuthProvider
    provider_handle: str
    is_primary: bool


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
    identities: list[UserIdentityInfo]


class GetCurrentUserUseCase:
    """Use case for getting current authenticated user."""

    def __init__(
        self,
        jwt_service: JWTService,
        user_service: UserService,
        invite_service: InviteService,
        user_identity_service: UserIdentityService,
    ) -> None:
        """Initialize get current user use case.

        Args:
            jwt_service: JWT token domain service
            user_service: User domain service
            invite_service: Invite domain service
            user_identity_service: User identity domain service
        """
        self.jwt_service = jwt_service
        self.user_service = user_service
        self.invite_service = invite_service
        self.user_identity_service = user_identity_service

    async def execute(self, request: GetCurrentUserRequest) -> GetCurrentUserResponse:
        """Execute get current user flow.

        Steps:
        1. Verify JWT token via JWT service
        2. Extract user_id from token
        3. Load user from database
        4. Load user's invitations and identities
        5. Return user info

        Args:
            request: Request with JWT token

        Returns:
            User information if token is valid and user exists

        Raises:
            JWTError: If token is invalid or expired
            NotFoundError: If user not found
        """
        # Verify token (raises JWTError if invalid)
        payload = self.jwt_service.verify_token(request.token)

        # Load user from database (raises NotFoundError if not found)
        user = await self.user_service.get_by_id(UserId(UUID(payload.user_id)))

        # Load user's invitations
        invites = await self.invite_service.list_invites(user.id)

        # Load user's linked identities
        identities = await self.user_identity_service.get_all_identities_for_user(
            user.id
        )

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
                    provider=invite.provider,
                    invitee_handle=invite.invitee_handle,
                    status=invite.status,
                    created_at=invite.created_at,
                    accepted_at=invite.accepted_at,
                )
                for invite in invites
            ],
            identities=[
                UserIdentityInfo(
                    provider=identity.provider,
                    provider_handle=identity.provider_handle,
                    is_primary=identity.is_primary,
                )
                for identity in identities
            ],
        )
