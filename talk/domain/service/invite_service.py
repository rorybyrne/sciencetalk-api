"""Invite domain service."""

import logfire
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
        with logfire.span(
            "invite_service.create_invite",
            inviter_id=str(inviter_id),
            provider=provider.value,
            invitee_handle=invitee_handle,
        ):
            # Check if pending invite already exists
            existing = (
                await self.invite_repository.exists_pending_for_provider_identity(
                    provider, invitee_provider_id
                )
            )
            if existing:
                logfire.warn(
                    "Invite already exists",
                    provider=provider.value,
                    invitee_provider_id=invitee_provider_id,
                )
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

            saved = await self.invite_repository.save(invite)
            logfire.info(
                "Invite created",
                invite_id=str(saved.id),
                inviter_id=str(inviter_id),
                invitee_handle=invitee_handle,
            )
            return saved

    async def get_invite_by_token(self, token: InviteToken) -> Invite | None:
        """Get invite by token.

        Args:
            token: Invite token

        Returns:
            Invite if found, None otherwise
        """
        with logfire.span(
            "invite_service.get_invite_by_token", token=token.root[:8] + "..."
        ):
            invite = await self.invite_repository.find_by_token(token)
            if invite:
                logfire.info(
                    "Invite found",
                    invite_id=str(invite.id),
                    status=invite.status.value,
                )
            else:
                logfire.warn("Invite not found", token=token.root[:8] + "...")
            return invite

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
        with logfire.span(
            "invite_service.accept_invite",
            invite_id=str(invite_id),
            new_user_id=str(new_user_id),
        ):
            invite = await self.invite_repository.find_by_id(invite_id)
            if not invite:
                logfire.error(
                    "Invite not found for acceptance", invite_id=str(invite_id)
                )
                raise ValueError(f"Invite {invite_id} not found")

            accepted_invite = invite.model_copy(
                update={
                    "status": InviteStatus.ACCEPTED,
                    "accepted_at": datetime.now(),
                    "accepted_by_user_id": new_user_id,
                }
            )

            saved = await self.invite_repository.save(accepted_invite)
            logfire.info(
                "Invite accepted",
                invite_id=str(invite_id),
                new_user_id=str(new_user_id),
            )
            return saved

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
        with logfire.span(
            "invite_service.check_invite_exists",
            provider=provider.value,
            provider_user_id=provider_user_id,
        ):
            exists = await self.invite_repository.exists_pending_for_provider_identity(
                provider, provider_user_id
            )
            logfire.info(
                "Invite existence check",
                provider=provider.value,
                provider_user_id=provider_user_id,
                exists=exists,
            )
            return exists

    async def get_pending_count(self, inviter_id: UserId) -> int:
        """Get count of pending invites for a user.

        Used for quota checking.

        Args:
            inviter_id: User ID

        Returns:
            Number of pending invites
        """
        with logfire.span(
            "invite_service.get_pending_count", inviter_id=str(inviter_id)
        ):
            count = await self.invite_repository.count_by_inviter(
                inviter_id, InviteStatus.PENDING
            )
            logfire.info(
                "Pending invite count retrieved",
                inviter_id=str(inviter_id),
                count=count,
            )
            return count

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
        with logfire.span(
            "invite_service.list_invites",
            inviter_id=str(inviter_id),
            status=status.value if status else None,
            limit=limit,
            offset=offset,
        ):
            invites = await self.invite_repository.find_by_inviter(
                inviter_id, status, limit, offset
            )
            logfire.info(
                "Invites listed",
                inviter_id=str(inviter_id),
                count=len(invites),
            )
            return invites

    async def get_available_quota(self, user_quota: int, inviter_id: UserId) -> int:
        """Calculate available invite quota for a user.

        Domain logic: available quota = user's total quota - total invites sent
        (counts both pending and accepted invites)

        Args:
            user_quota: User's total invite quota
            inviter_id: User ID

        Returns:
            Number of invites user can still create
        """
        with logfire.span(
            "invite_service.get_available_quota",
            user_quota=user_quota,
            inviter_id=str(inviter_id),
        ):
            # Count all invites (both pending and accepted)
            total_invites = await self.invite_repository.count_by_inviter(
                inviter_id, status=None
            )
            available = max(0, user_quota - total_invites)
            logfire.info(
                "Available quota calculated",
                inviter_id=str(inviter_id),
                user_quota=user_quota,
                total_invites=total_invites,
                available=available,
            )
            return available

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
        with logfire.span(
            "invite_service.find_pending_by_provider_identity",
            provider=provider.value,
            provider_user_id=provider_user_id,
        ):
            invite = await self.invite_repository.find_pending_by_provider_identity(
                provider, provider_user_id
            )
            if invite:
                logfire.info(
                    "Pending invite found",
                    provider=provider.value,
                    provider_user_id=provider_user_id,
                    invite_id=str(invite.id),
                )
            else:
                logfire.warn(
                    "Pending invite not found",
                    provider=provider.value,
                    provider_user_id=provider_user_id,
                )
            return invite
