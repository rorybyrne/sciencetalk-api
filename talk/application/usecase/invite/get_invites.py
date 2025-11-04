"""Get invites use case."""

from datetime import datetime

from pydantic import BaseModel, Field

from talk.domain.service import InviteService, UserService
from talk.domain.value import InviteStatus, UserId


class InviteItem(BaseModel):
    """Invite item in response."""

    invite_id: str
    inviter_handle: str
    invitee_handle: str
    status: InviteStatus
    created_at: datetime
    accepted_at: datetime | None = None


class GetInvitesRequest(BaseModel):
    """Get invites request."""

    inviter_id: str  # User ID from auth
    status: InviteStatus | None = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class GetInvitesResponse(BaseModel):
    """Get invites response."""

    invites: list[InviteItem]
    total: int
    remaining_quota: int


class GetInvitesUseCase:
    """Use case for getting invites created by a user."""

    def __init__(
        self, invite_service: InviteService, user_service: UserService
    ) -> None:
        """Initialize get invites use case.

        Args:
            invite_service: Invite service
            user_service: User service
        """
        self.invite_service = invite_service
        self.user_service = user_service

    async def execute(self, request: GetInvitesRequest) -> GetInvitesResponse:
        """Execute get invites flow.

        Args:
            request: Get invites request

        Returns:
            List of invites created by the user with remaining quota
        """
        from uuid import UUID

        user_id = UserId(UUID(request.inviter_id))

        # Get user to calculate remaining quota
        user = await self.user_service.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        # Get invites from service
        invites = await self.invite_service.list_invites(
            inviter_id=user_id,
            status=request.status,
            limit=request.limit,
            offset=request.offset,
        )

        # Calculate remaining quota using domain service
        remaining_quota = await self.invite_service.get_available_quota(
            user.invite_quota, user_id
        )

        # Convert to response items
        invite_items = [
            InviteItem(
                invite_id=str(invite.id),
                inviter_handle=user.handle.root,
                invitee_handle=str(invite.invitee_handle),
                status=invite.status,
                created_at=invite.created_at,
                accepted_at=invite.accepted_at,
            )
            for invite in invites
        ]

        return GetInvitesResponse(
            invites=invite_items,
            total=len(invite_items),
            remaining_quota=remaining_quota,
        )
