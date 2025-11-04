"""User identity repository interface."""

from abc import ABC, abstractmethod
from typing import Optional

from talk.domain.model.user_identity import UserIdentity
from talk.domain.value import AuthProvider, UserId, UserIdentityId


class UserIdentityRepository(ABC):
    """Repository for UserIdentity entity.

    Manages the relationship between users and their external
    authentication provider identities.
    """

    @abstractmethod
    async def find_by_id(self, identity_id: UserIdentityId) -> Optional[UserIdentity]:
        """Find an identity by ID.

        Args:
            identity_id: The identity's unique identifier

        Returns:
            The identity if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_by_provider(
        self, provider: AuthProvider, provider_user_id: str
    ) -> Optional[UserIdentity]:
        """Find an identity by provider and provider user ID.

        Args:
            provider: The authentication provider
            provider_user_id: The user's ID on that provider

        Returns:
            The identity if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_all_by_user_id(self, user_id: UserId) -> list[UserIdentity]:
        """Get all identities linked to a user.

        Args:
            user_id: The user's unique identifier

        Returns:
            List of identities (may be empty)
        """
        pass

    @abstractmethod
    async def find_primary_by_user_id(self, user_id: UserId) -> Optional[UserIdentity]:
        """Get the primary identity for a user.

        Args:
            user_id: The user's unique identifier

        Returns:
            The primary identity if found, None otherwise
        """
        pass

    @abstractmethod
    async def save(self, identity: UserIdentity) -> UserIdentity:
        """Save an identity (create or update).

        Args:
            identity: The identity to save

        Returns:
            The saved identity
        """
        pass

    @abstractmethod
    async def delete(self, identity_id: UserIdentityId) -> None:
        """Delete an identity.

        Args:
            identity_id: The identity to delete
        """
        pass

    @abstractmethod
    async def exists_by_provider(
        self, provider: AuthProvider, provider_user_id: str
    ) -> bool:
        """Check if an identity exists for the given provider and ID.

        Args:
            provider: The authentication provider
            provider_user_id: The user's ID on that provider

        Returns:
            True if identity exists, False otherwise
        """
        pass
