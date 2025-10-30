"""Invite domain service."""

from datetime import datetime
from uuid import uuid4

from talk.domain.model.invite import Invite
from talk.domain.repository import InviteRepository
from talk.domain.value import InviteId, InviteStatus, UserId
from talk.domain.value.types import BlueskyDID, Handle

from .base import Service


class InviteService(Service):
    """Domain service for invite operations."""

    def __init__(self, invite_repository: InviteRepository) -> None:
        """Initialize invite service.

        Args:
            invite_repository: Invite repository
        """
        self.invite_repository = invite_repository

    async def create_invite(
        self, inviter_id: UserId, invitee_handle: Handle, invitee_did: BlueskyDID
    ) -> Invite:
        """Create a new invite.

        Args:
            inviter_id: User creating the invite
            invitee_handle: Handle being invited
            invitee_did: DID resolved from handle

        Returns:
            Created invite

        Raises:
            ValueError: If pending invite already exists for this DID
        """
        # Check if pending invite already exists by DID (primary check)
        existing = await self.invite_repository.find_pending_by_did(invitee_did)
        if existing:
            raise ValueError(f"Invite already exists for {invitee_did}")

        invite = Invite(
            id=InviteId(uuid4()),
            inviter_id=inviter_id,
            invitee_handle=invitee_handle,
            invitee_did=invitee_did,
            status=InviteStatus.PENDING,
            created_at=datetime.now(),
        )

        return await self.invite_repository.save(invite)

    async def accept_invite(
        self, invitee_did: BlueskyDID, new_user_id: UserId
    ) -> Invite:
        """Mark an invite as accepted.

        Args:
            invitee_did: DID of the user accepting
            new_user_id: ID of the newly created user

        Returns:
            Updated invite

        Raises:
            ValueError: If no pending invite found
        """
        invite = await self.invite_repository.find_pending_by_did(invitee_did)
        if not invite:
            raise ValueError(f"No pending invite found for {invitee_did}")

        accepted_invite = invite.model_copy(
            update={
                "status": InviteStatus.ACCEPTED,
                "accepted_at": datetime.now(),
                "accepted_by_user_id": new_user_id,
            }
        )

        return await self.invite_repository.save(accepted_invite)

    async def check_invite_exists(self, did: BlueskyDID) -> bool:
        """Check if a pending invite exists for a DID.

        Critical path for login check.

        Args:
            did: DID to check

        Returns:
            True if pending invite exists, False otherwise
        """
        invite = await self.invite_repository.find_pending_by_did(did)
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

    async def get_available_quota(self, user_quota: int, inviter_id: UserId) -> int:
        """Calculate available invite quota for a user.

        Domain logic: available quota = user's total quota - pending invites

        Args:
            user_quota: User's total invite quota
            inviter_id: User ID

        Returns:
            Number of invites user can still create
        """
        pending_count = await self.get_pending_count(inviter_id)
        return max(0, user_quota - pending_count)
