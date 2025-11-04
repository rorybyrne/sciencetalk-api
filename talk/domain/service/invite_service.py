"""Invite domain service."""

from datetime import datetime
from uuid import uuid4

from talk.domain.model.invite import Invite
from talk.domain.repository import InviteRepository
from talk.domain.value import AuthProvider, InviteId, InviteStatus, InviteToken, UserId

from .base import Service


class InviteService(Service):
    """Domain service for multi-provider invite operations."""

    def __init__(self, invite_repository: InviteRepository) -> None:
        """Initialize invite service.

        Args:
            invite_repository: Invite repository
        """
        self.invite_repository = invite_repository

    async def create_invite(
        self,
        inviter_id: UserId,
        provider: AuthProvider,
        invitee_handle: str,
        invitee_provider_id: str,
        invitee_name: str | None,
        invite_token: InviteToken,
    ) -> Invite:
        """Create a new invite.

        Args:
            inviter_id: User creating the invite
            provider: Authentication provider
            invitee_handle: Display handle
            invitee_provider_id: Permanent provider ID
            invitee_name: Optional display name
            invite_token: Unique invite token

        Returns:
            Created invite

        Raises:
            ValueError: If pending invite already exists
        """
        # Check if pending invite already exists
        existing = await self.invite_repository.exists_pending_for_provider_identity(
            provider, invitee_provider_id
        )
        if existing:
            raise ValueError(
                f"Invite already exists for {provider}:{invitee_provider_id}"
            )

        invite = Invite(
            id=InviteId(uuid4()),
            inviter_id=inviter_id,
            provider=provider,
            invitee_handle=invitee_handle,
            invitee_provider_id=invitee_provider_id,
            invitee_name=invitee_name,
            invite_token=invite_token,
            status=InviteStatus.PENDING,
            created_at=datetime.now(),
        )

        return await self.invite_repository.save(invite)

    async def get_invite_by_token(self, token: InviteToken) -> Invite | None:
        """Get invite by token.

        Args:
            token: Invite token

        Returns:
            Invite if found, None otherwise
        """
        return await self.invite_repository.find_by_token(token)

    async def accept_invite(self, invite_id: InviteId, new_user_id: UserId) -> Invite:
        """Mark an invite as accepted.

        Args:
            invite_id: ID of the invite to accept
            new_user_id: ID of the newly created user

        Returns:
            Updated invite

        Raises:
            ValueError: If invite not found
        """
        invite = await self.invite_repository.find_by_id(invite_id)
        if not invite:
            raise ValueError(f"Invite {invite_id} not found")

        accepted_invite = invite.model_copy(
            update={
                "status": InviteStatus.ACCEPTED,
                "accepted_at": datetime.now(),
                "accepted_by_user_id": new_user_id,
            }
        )

        return await self.invite_repository.save(accepted_invite)

    async def check_invite_exists(
        self, provider: AuthProvider, provider_user_id: str
    ) -> bool:
        """Check if a pending invite exists for a provider identity.

        Critical path for login check.

        Args:
            provider: Authentication provider
            provider_user_id: Provider-specific user ID

        Returns:
            True if pending invite exists, False otherwise
        """
        return await self.invite_repository.exists_pending_for_provider_identity(
            provider, provider_user_id
        )

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

    async def find_pending_by_provider_identity(
        self, provider: AuthProvider, provider_user_id: str
    ):
        """Find pending invite by provider identity.

        Args:
            provider: Authentication provider
            provider_user_id: Provider-specific user ID

        Returns:
            Pending invite if found, None otherwise
        """
        return await self.invite_repository.find_pending_by_provider_identity(
            provider, provider_user_id
        )
