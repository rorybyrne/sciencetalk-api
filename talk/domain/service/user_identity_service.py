"""User identity domain service."""

from talk.domain.model.user_identity import UserIdentity
from talk.domain.repository.user_identity import UserIdentityRepository
from talk.domain.value import AuthProvider, UserId, UserIdentityId


class UserIdentityService:
    """Domain service for user identity operations."""

    def __init__(self, user_identity_repository: UserIdentityRepository) -> None:
        """Initialize user identity service.

        Args:
            user_identity_repository: User identity repository
        """
        self.user_identity_repository = user_identity_repository

    async def get_identity_by_id(
        self, identity_id: UserIdentityId
    ) -> UserIdentity | None:
        """Get identity by ID.

        Args:
            identity_id: Identity ID

        Returns:
            Identity if found, None otherwise
        """
        return await self.user_identity_repository.find_by_id(identity_id)

    async def get_identity_by_provider(
        self, provider: AuthProvider, provider_user_id: str
    ) -> UserIdentity | None:
        """Get identity by provider and provider user ID.

        Args:
            provider: Authentication provider
            provider_user_id: Provider-specific user ID

        Returns:
            Identity if found, None otherwise
        """
        return await self.user_identity_repository.find_by_provider(
            provider, provider_user_id
        )

    async def get_all_identities_for_user(self, user_id: UserId) -> list[UserIdentity]:
        """Get all identities linked to a user.

        Args:
            user_id: User ID

        Returns:
            List of identities (may be empty)
        """
        return await self.user_identity_repository.find_all_by_user_id(user_id)

    async def get_primary_identity(self, user_id: UserId) -> UserIdentity | None:
        """Get the primary identity for a user.

        Args:
            user_id: User ID

        Returns:
            Primary identity if found, None otherwise
        """
        return await self.user_identity_repository.find_primary_by_user_id(user_id)

    async def identity_exists(
        self, provider: AuthProvider, provider_user_id: str
    ) -> bool:
        """Check if an identity exists.

        Args:
            provider: Authentication provider
            provider_user_id: Provider-specific user ID

        Returns:
            True if identity exists, False otherwise
        """
        return await self.user_identity_repository.exists_by_provider(
            provider, provider_user_id
        )

    async def save(self, identity: UserIdentity) -> UserIdentity:
        """Save identity (create or update).

        Args:
            identity: Identity to save

        Returns:
            Saved identity
        """
        return await self.user_identity_repository.save(identity)
