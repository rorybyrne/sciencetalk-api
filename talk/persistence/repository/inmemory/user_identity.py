"""In-memory user identity repository for testing."""

from typing import Optional

from talk.domain.model.user_identity import UserIdentity
from talk.domain.repository.user_identity import UserIdentityRepository
from talk.domain.value import AuthProvider, UserId, UserIdentityId


class InMemoryUserIdentityRepository(UserIdentityRepository):
    """In-memory implementation of UserIdentityRepository for testing."""

    def __init__(self) -> None:
        self._identities: list[UserIdentity] = []

    async def save(self, identity: UserIdentity) -> UserIdentity:
        """Save user identity."""
        # Check for existing identity with same ID (update case)
        for i, existing in enumerate(self._identities):
            if existing.id == identity.id:
                self._identities[i] = identity
                return identity

        self._identities.append(identity)
        return identity

    async def find_by_id(self, identity_id: UserIdentityId) -> Optional[UserIdentity]:
        """Find user identity by ID."""
        for identity in self._identities:
            if identity.id == identity_id:
                return identity
        return None

    async def find_by_provider(
        self, provider: AuthProvider, provider_user_id: str
    ) -> Optional[UserIdentity]:
        """Find user identity by provider and provider user ID."""
        for identity in self._identities:
            if (
                identity.provider == provider
                and identity.provider_user_id == provider_user_id
            ):
                return identity
        return None

    async def find_all_by_user_id(self, user_id: UserId) -> list[UserIdentity]:
        """Find all identities for a user."""
        matches = []
        for identity in self._identities:
            if identity.user_id == user_id:
                matches.append(identity)
        # Sort by created_at
        matches.sort(key=lambda i: i.created_at)
        return matches

    async def find_primary_by_user_id(self, user_id: UserId) -> Optional[UserIdentity]:
        """Get primary identity for a user."""
        for identity in self._identities:
            if identity.user_id == user_id and identity.is_primary:
                return identity
        return None

    async def exists_by_provider(
        self, provider: AuthProvider, provider_user_id: str
    ) -> bool:
        """Check if an identity exists for the given provider and ID."""
        for identity in self._identities:
            if (
                identity.provider == provider
                and identity.provider_user_id == provider_user_id
            ):
                return True
        return False

    async def delete(self, identity_id: UserIdentityId) -> None:
        """Delete user identity."""
        self._identities = [i for i in self._identities if i.id != identity_id]
