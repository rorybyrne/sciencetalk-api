"""Invite domain service."""

from datetime import datetime
from uuid import uuid4

from talk.domain.model.invite import Invite
from talk.domain.repository import InviteRepository
from talk.domain.value import InviteId, InviteStatus, UserId
from talk.domain.value.types import Handle

from .base import Service


class InviteService(Service):
    """Domain service for invite operations."""

    def __init__(self, invite_repository: InviteRepository) -> None:
        """Initialize invite service.

        Args:
            invite_repository: Invite repository
        """
        self.invite_repository = invite_repository

    async def create_invite(self, inviter_id: UserId, invitee_handle: Handle) -> Invite:
        """Create a new invite.

        Args:
            inviter_id: User creating the invite
            invitee_handle: Handle being invited

        Returns:
            Created invite

        Raises:
            ValueError: If pending invite already exists for this handle
        """
        # Check if pending invite already exists
        existing = await self.invite_repository.find_pending_by_handle(invitee_handle)
        if existing:
            raise ValueError(f"Invite already exists for {invitee_handle}")

        invite = Invite(
            id=InviteId(uuid4()),
            inviter_id=inviter_id,
            invitee_handle=invitee_handle,
            status=InviteStatus.PENDING,
            created_at=datetime.now(),
        )

        return await self.invite_repository.save(invite)

    async def accept_invite(
        self, invitee_handle: Handle, new_user_id: UserId
    ) -> Invite:
        """Mark an invite as accepted.

        Args:
            invitee_handle: Handle of the user accepting
            new_user_id: ID of the newly created user

        Returns:
            Updated invite

        Raises:
            ValueError: If no pending invite found
        """
        invite = await self.invite_repository.find_pending_by_handle(invitee_handle)
        if not invite:
            raise ValueError(f"No pending invite found for {invitee_handle}")

        accepted_invite = invite.model_copy(
            update={
                "status": InviteStatus.ACCEPTED,
                "accepted_at": datetime.now(),
                "accepted_by_user_id": new_user_id,
            }
        )

        return await self.invite_repository.save(accepted_invite)

    async def check_invite_exists(self, handle: Handle) -> bool:
        """Check if a pending invite exists for a handle.

        Critical path for login check.

        Args:
            handle: Handle to check

        Returns:
            True if pending invite exists, False otherwise
        """
        invite = await self.invite_repository.find_pending_by_handle(handle)
        return invite is not None

    async def get_pending_count(self, inviter_id: UserId) -> int:
        """Get count of pending invites for a user.

        Used for quota checking.

        Args:
            inviter_id: User ID

        Returns:
            Number of pending invites
        """
        return await self.invite_repository.count_by_inviter(
            inviter_id, InviteStatus.PENDING
        )

    async def list_invites(
        self,
        inviter_id: UserId,
        status: InviteStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Invite]:
        """List invites created by a user.

        Args:
            inviter_id: User ID
            status: Optional status filter
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of invites
        """
        return await self.invite_repository.find_by_inviter(
            inviter_id, status, limit, offset
        )
