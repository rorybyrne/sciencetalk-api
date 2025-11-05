"""User identity domain service."""

import logfire

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
        with logfire.span(
            "user_identity_service.get_identity_by_id", identity_id=str(identity_id)
        ):
            identity = await self.user_identity_repository.find_by_id(identity_id)
            if identity:
                logfire.info(
                    "Identity found",
                    identity_id=str(identity_id),
                    provider=identity.provider.value,
                )
            else:
                logfire.warn("Identity not found", identity_id=str(identity_id))
            return identity

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
        with logfire.span(
            "user_identity_service.get_identity_by_provider",
            provider=provider.value,
            provider_user_id=provider_user_id,
        ):
            identity = await self.user_identity_repository.find_by_provider(
                provider, provider_user_id
            )
            if identity:
                logfire.info(
                    "Identity found",
                    provider=provider.value,
                    provider_user_id=provider_user_id,
                    user_id=str(identity.user_id),
                )
            else:
                logfire.warn(
                    "Identity not found",
                    provider=provider.value,
                    provider_user_id=provider_user_id,
                )
            return identity

    async def get_all_identities_for_user(self, user_id: UserId) -> list[UserIdentity]:
        """Get all identities linked to a user.

        Args:
            user_id: User ID

        Returns:
            List of identities (may be empty)
        """
        with logfire.span(
            "user_identity_service.get_all_identities_for_user", user_id=str(user_id)
        ):
            identities = await self.user_identity_repository.find_all_by_user_id(
                user_id
            )
            logfire.info(
                "Identities retrieved for user",
                user_id=str(user_id),
                count=len(identities),
            )
            return identities

    async def get_primary_identity(self, user_id: UserId) -> UserIdentity | None:
        """Get the primary identity for a user.

        Args:
            user_id: User ID

        Returns:
            Primary identity if found, None otherwise
        """
        with logfire.span(
            "user_identity_service.get_primary_identity", user_id=str(user_id)
        ):
            identity = await self.user_identity_repository.find_primary_by_user_id(
                user_id
            )
            if identity:
                logfire.info(
                    "Primary identity found",
                    user_id=str(user_id),
                    provider=identity.provider.value,
                )
            else:
                logfire.warn("Primary identity not found", user_id=str(user_id))
            return identity

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
        with logfire.span(
            "user_identity_service.identity_exists",
            provider=provider.value,
            provider_user_id=provider_user_id,
        ):
            exists = await self.user_identity_repository.exists_by_provider(
                provider, provider_user_id
            )
            logfire.info(
                "Identity existence check",
                provider=provider.value,
                provider_user_id=provider_user_id,
                exists=exists,
            )
            return exists

    async def save(self, identity: UserIdentity) -> UserIdentity:
        """Save identity (create or update).

        Args:
            identity: Identity to save

        Returns:
            Saved identity
        """
        with logfire.span(
            "user_identity_service.save",
            identity_id=str(identity.id),
            provider=identity.provider.value,
            user_id=str(identity.user_id),
        ):
            saved = await self.user_identity_repository.save(identity)
            logfire.info(
                "Identity saved",
                identity_id=str(saved.id),
                provider=saved.provider.value,
                user_id=str(saved.user_id),
            )
            return saved
