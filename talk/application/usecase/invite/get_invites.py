"""Get invites use case."""

from datetime import datetime

from pydantic import BaseModel, Field

from talk.domain.service import InviteService
from talk.domain.value import InviteStatus, UserId


class InviteItem(BaseModel):
    """Invite item in response."""

    invite_id: str
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


class GetInvitesUseCase:
    """Use case for getting invites created by a user."""

    def __init__(self, invite_service: InviteService) -> None:
        """Initialize get invites use case.

        Args:
            invite_service: Invite service
        """
        self.invite_service = invite_service

    async def execute(self, request: GetInvitesRequest) -> GetInvitesResponse:
        """Execute get invites flow.

        Args:
            request: Get invites request

        Returns:
            List of invites created by the user
        """
        from uuid import UUID

        user_id = UserId(UUID(request.inviter_id))

        # Get invites from service
        invites = await self.invite_service.list_invites(
            inviter_id=user_id,
            status=request.status,
            limit=request.limit,
            offset=request.offset,
        )

        # Convert to response items
        invite_items = [
            InviteItem(
                invite_id=str(invite.id),
                invitee_handle=str(invite.invitee_handle),
                status=invite.status,
                created_at=invite.created_at,
                accepted_at=invite.accepted_at,
            )
            for invite in invites
        ]

        return GetInvitesResponse(
            invites=invite_items,
            total=len(invite_items),  # TODO: Add count query if needed
        )
