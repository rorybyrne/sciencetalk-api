"""In-memory invite repository for testing."""

from typing import Optional

from sqlalchemy.exc import IntegrityError

from talk.domain.model.invite import Invite
from talk.domain.repository.invite import InviteRepository
from talk.domain.value import AuthProvider, InviteId, InviteStatus, InviteToken, UserId


class InMemoryInviteRepository(InviteRepository):
    """In-memory implementation of InviteRepository for testing."""

    def __init__(self) -> None:
        self._invites: list[Invite] = []

    async def find_by_id(self, invite_id: InviteId) -> Optional[Invite]:
        """Find an invite by ID."""
        for invite in self._invites:
            if invite.id == invite_id:
                return invite
        return None

    async def find_by_token(self, token: InviteToken) -> Optional[Invite]:
        """Find an invite by its token."""
        for invite in self._invites:
            if invite.invite_token == token:
                return invite
        return None

    async def find_pending_by_provider_identity(
        self, provider: AuthProvider, provider_user_id: str
    ) -> Optional[Invite]:
        """Find a pending invite by provider and provider user ID."""
        for invite in self._invites:
            if (
                invite.provider == provider
                and invite.invitee_provider_id == provider_user_id
                and invite.status == InviteStatus.PENDING
            ):
                return invite
        return None

    async def exists_pending_for_provider_identity(
        self, provider: AuthProvider, provider_user_id: str
    ) -> bool:
        """Check if a pending invite exists for provider identity."""
        for invite in self._invites:
            if (
                invite.provider == provider
                and invite.invitee_provider_id == provider_user_id
                and invite.status == InviteStatus.PENDING
            ):
                return True
        return False

    async def save(self, invite: Invite) -> Invite:
        """Save an invite (create or update).

        Raises:
            IntegrityError: If pending invite already exists for this provider identity
        """
        # Check for existing invite with same ID (update case)
        for i, existing in enumerate(self._invites):
            if existing.id == invite.id:
                self._invites[i] = invite
                return invite

        # Check for duplicate pending invite by provider identity (create case)
        existing_pending = await self.find_pending_by_provider_identity(
            invite.provider, invite.invitee_provider_id
        )
        if existing_pending:
            raise IntegrityError("Duplicate pending invite", None, Exception())

        self._invites.append(invite)
        return invite

    async def count_by_inviter(
        self, inviter_id: UserId, status: Optional[InviteStatus] = None
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
        status: Optional[InviteStatus] = None,
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

    async def find_all_accepted_relationships(self) -> list[tuple[UserId, UserId]]:
        """Find all accepted invite relationships for tree building."""
        relationships = []
        for invite in self._invites:
            if invite.status == InviteStatus.ACCEPTED and invite.accepted_by_user_id:
                relationships.append((invite.inviter_id, invite.accepted_by_user_id))
        return relationships
