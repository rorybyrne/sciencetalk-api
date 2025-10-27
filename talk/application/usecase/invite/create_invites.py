"""Create invites use case."""

from datetime import datetime

from pydantic import BaseModel, Field

from talk.application.usecase.base import BaseUseCase
from talk.config import Settings
from talk.domain.service import InviteService, UserService
from talk.domain.value import InviteStatus, UserId
from talk.domain.value.types import Handle


class CreateInvitesRequest(BaseModel):
    """Request to create invites."""

    inviter_id: str
    inviter_handle: str
    invitee_handles: list[str] = Field(max_length=10)  # Max 10 at once


class InviteItem(BaseModel):
    """Invite item in response."""

    invite_id: str
    inviter_handle: str
    invitee_handle: str
    status: InviteStatus
    created_at: datetime
    accepted_at: datetime | None = None


class CreateInvitesResponse(BaseModel):
    """Response after creating invites."""

    invites: list[InviteItem]
    failed_handles: list[str]  # Handles that failed (already invited, invalid, etc.)
    remaining_quota: int


class CreateInvitesUseCase(BaseUseCase):
    """Use case for creating multiple invites."""

    def __init__(
        self,
        invite_service: InviteService,
        user_service: UserService,
        settings: Settings,
    ) -> None:
        """Initialize use case.

        Args:
            invite_service: Invite domain service
            user_service: User domain service
            settings: Application settings
        """
        self.invite_service = invite_service
        self.user_service = user_service
        self.settings = settings

    async def execute(self, request: CreateInvitesRequest) -> CreateInvitesResponse:
        """Execute create invites use case.

        Args:
            request: Create invites request

        Returns:
            Response with created invites, failures, and remaining quota

        Raises:
            ValueError: If user not found or quota exceeded
        """
        from uuid import UUID

        inviter_id = UserId(UUID(request.inviter_id))

        # Get inviter
        inviter = await self.user_service.get_user_by_id(inviter_id)
        if not inviter:
            raise ValueError("User not found")

        # Check if user has unlimited invites
        has_unlimited_invites = (
            inviter.handle in self.settings.invitations.unlimited_inviters
        )

        # Check quota (unless user has unlimited invites)
        if not has_unlimited_invites:
            available_quota = await self.invite_service.get_available_quota(
                inviter.invite_quota, inviter_id
            )

            if len(request.invitee_handles) > available_quota:
                raise ValueError(
                    f"Insufficient invite quota. Available: {available_quota}, Requested: {len(request.invitee_handles)}"
                )

        # Create invites
        created_invites = []
        failed_handles = []

        for handle_str in request.invitee_handles:
            try:
                # Validate handle format
                handle = Handle(root=handle_str)

                # Create invite
                invite = await self.invite_service.create_invite(inviter_id, handle)
                created_invites.append(invite)

            except Exception:
                # Handle validation error or duplicate invite
                failed_handles.append(handle_str)

        # Calculate remaining quota after creating invites
        remaining_quota = await self.invite_service.get_available_quota(
            inviter.invite_quota, inviter_id
        )

        # Convert invites to response items
        invite_items = [
            InviteItem(
                invite_id=str(invite.id),
                inviter_handle=request.inviter_handle,
                invitee_handle=str(invite.invitee_handle),
                status=invite.status,
                created_at=invite.created_at,
                accepted_at=invite.accepted_at,
            )
            for invite in created_invites
        ]

        return CreateInvitesResponse(
            invites=invite_items,
            failed_handles=failed_handles,
            remaining_quota=remaining_quota,
        )
