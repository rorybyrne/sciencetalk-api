"""Invite repository interface."""

from abc import ABC, abstractmethod

from talk.domain.model.invite import Invite
from talk.domain.value import AuthProvider, InviteId, InviteStatus, InviteToken, UserId


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
    async def find_by_token(self, token: InviteToken) -> Invite | None:
        """Find an invite by token.

        Used when user opens invite link.

        Args:
            token: The invite token

        Returns:
            The invite if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_pending_by_provider_identity(
        self, provider: AuthProvider, provider_user_id: str
    ) -> Invite | None:
        """Find a pending invite by provider and identity.

        Critical for login check - must be fast.

        Args:
            provider: The authentication provider
            provider_user_id: The provider-specific user ID

        Returns:
            The pending invite if found, None otherwise
        """
        pass

    @abstractmethod
    async def exists_pending_for_provider_identity(
        self, provider: AuthProvider, provider_user_id: str
    ) -> bool:
        """Check if a pending invite exists for provider/identity.

        Used during invite creation to prevent duplicates.

        Args:
            provider: The authentication provider
            provider_user_id: The provider-specific user ID

        Returns:
            True if pending invite exists, False otherwise
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
            IntegrityError: If pending invite already exists for this provider/identity
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
