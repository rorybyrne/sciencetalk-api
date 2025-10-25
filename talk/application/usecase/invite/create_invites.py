"""Create invites use case."""

from pydantic import BaseModel, Field

from talk.application.usecase.base import BaseUseCase
from talk.config import Settings
from talk.domain.repository import UserRepository
from talk.domain.service import InviteService
from talk.domain.value import UserId
from talk.domain.value.types import Handle


class CreateInvitesRequest(BaseModel):
    """Request to create invites."""

    inviter_id: str
    invitee_handles: list[str] = Field(max_length=10)  # Max 10 at once


class CreateInvitesResponse(BaseModel):
    """Response after creating invites."""

    created_count: int
    failed_handles: list[str]  # Handles that failed (already invited, invalid, etc.)


class CreateInvitesUseCase(BaseUseCase):
    """Use case for creating multiple invites."""

    def __init__(
        self,
        invite_service: InviteService,
        user_repository: UserRepository,
        settings: Settings,
    ) -> None:
        """Initialize use case.

        Args:
            invite_service: Invite domain service
            user_repository: User repository
            settings: Application settings
        """
        self.invite_service = invite_service
        self.user_repository = user_repository
        self.settings = settings

    async def execute(self, request: CreateInvitesRequest) -> CreateInvitesResponse:
        """Execute create invites use case.

        Args:
            request: Create invites request

        Returns:
            Response with created count and failures

        Raises:
            ValueError: If user not found or quota exceeded
        """
        from uuid import UUID

        inviter_id = UserId(UUID(request.inviter_id))

        # Get inviter
        inviter = await self.user_repository.find_by_id(inviter_id)
        if not inviter:
            raise ValueError("User not found")

        # Check if user has unlimited invites
        has_unlimited_invites = (
            inviter.handle in self.settings.invitations.unlimited_inviters
        )

        # Check quota (unless user has unlimited invites)
        if not has_unlimited_invites:
            pending_count = await self.invite_service.get_pending_count(inviter_id)
            available_quota = inviter.invite_quota - pending_count

            if len(request.invitee_handles) > available_quota:
                raise ValueError(
                    f"Insufficient invite quota. Available: {available_quota}, Requested: {len(request.invitee_handles)}"
                )

        # Create invites
        created_count = 0
        failed_handles = []

        for handle_str in request.invitee_handles:
            try:
                # Validate handle format
                handle = Handle(root=handle_str)

                # Create invite
                await self.invite_service.create_invite(inviter_id, handle)
                created_count += 1

            except Exception:
                # Handle validation error or duplicate invite
                failed_handles.append(handle_str)

        return CreateInvitesResponse(
            created_count=created_count,
            failed_handles=failed_handles,
        )
