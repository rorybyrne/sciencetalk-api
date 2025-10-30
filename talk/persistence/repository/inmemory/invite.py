"""In-memory invite repository for testing."""

from sqlalchemy.exc import IntegrityError

from talk.domain.model.invite import Invite
from talk.domain.repository.invite import InviteRepository
from talk.domain.value import InviteId, InviteStatus, UserId
from talk.domain.value.types import BlueskyDID


class InMemoryInviteRepository(InviteRepository):
    """In-memory implementation of InviteRepository for testing."""

    def __init__(self) -> None:
        self._invites: list[Invite] = []

    async def find_by_id(self, invite_id: InviteId) -> Invite | None:
        """Find an invite by ID."""
        for invite in self._invites:
            if invite.id == invite_id:
                return invite
        return None

    async def find_pending_by_did(self, did: BlueskyDID) -> Invite | None:
        """Find a pending invite by DID."""
        for invite in self._invites:
            if (
                str(invite.invitee_did) == str(did)
                and invite.status == InviteStatus.PENDING
            ):
                return invite
        return None

    async def save(self, invite: Invite) -> Invite:
        """Save an invite (create or update).

        Raises:
            IntegrityError: If pending invite already exists for this DID
        """
        # Check for existing invite with same ID (update case)
        for i, existing in enumerate(self._invites):
            if existing.id == invite.id:
                self._invites[i] = invite
                return invite

        # Check for duplicate pending invite by DID (create case)
        existing_pending = await self.find_pending_by_did(invite.invitee_did)
        if existing_pending:
            raise IntegrityError("Duplicate pending invite", None, Exception())

        self._invites.append(invite)
        return invite

    async def count_by_inviter(
        self, inviter_id: UserId, status: InviteStatus | None = None
    ) -> int:
        """Count invites by inviter."""
        count = 0
        for invite in self._invites:
            if invite.inviter_id != inviter_id:
                continue
            if status is None or invite.status == status:
                count += 1
        return count

    async def find_by_inviter(
        self,
        inviter_id: UserId,
        status: InviteStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Invite]:
        """Find invites by inviter with pagination."""
        matches = []
        for invite in self._invites:
            if invite.inviter_id != inviter_id:
                continue
            if status is None or invite.status == status:
                matches.append(invite)

        # Sort by created_at descending
        matches.sort(key=lambda inv: inv.created_at, reverse=True)

        # Apply pagination
        return matches[offset : offset + limit]
