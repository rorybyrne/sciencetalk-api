"""Invite repository interface."""

from abc import ABC, abstractmethod

from talk.domain.model.invite import Invite
from talk.domain.value import InviteId, InviteStatus, UserId
from talk.domain.value.types import BlueskyDID


class InviteRepository(ABC):
    """Repository for Invite entity.

    Defines the contract for invite persistence operations.
    Implementations live in the infrastructure layer.
    """

    @abstractmethod
    async def find_by_id(self, invite_id: InviteId) -> Invite | None:
        """Find an invite by ID.

        Args:
            invite_id: The invite's unique identifier

        Returns:
            The invite if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_pending_by_did(self, did: BlueskyDID) -> Invite | None:
        """Find a pending invite by DID.

        Critical for login check - must be fast.
        DID is the primary matching identifier (handles can change).

        Args:
            did: The invitee's DID

        Returns:
            The pending invite if found, None otherwise
        """
        pass

    @abstractmethod
    async def save(self, invite: Invite) -> Invite:
        """Save an invite (create or update).

        Args:
            invite: The invite to save

        Returns:
            The saved invite

        Raises:
            IntegrityError: If pending invite already exists for this handle
        """
        pass

    @abstractmethod
    async def count_by_inviter(
        self, inviter_id: UserId, status: InviteStatus | None = None
    ) -> int:
        """Count invites by inviter.

        Used for quota checking.

        Args:
            inviter_id: The inviter's ID
            status: Optional status filter

        Returns:
            Number of invites
        """
        pass

    @abstractmethod
    async def find_by_inviter(
        self,
        inviter_id: UserId,
        status: InviteStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Invite]:
        """Find invites by inviter with pagination.

        Args:
            inviter_id: The inviter's ID
            status: Optional status filter
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of invites
        """
        pass
