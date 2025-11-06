"""In-memory user repository for testing."""

from typing import Optional

from talk.domain.model.user import User
from talk.domain.repository.user import UserRepository
from talk.domain.value import AuthProvider, UserId
from talk.domain.value.types import Handle


class InMemoryUserRepository(UserRepository):
    """In-memory implementation of UserRepository for testing."""

    def __init__(self) -> None:
        self._users: dict[UserId, User] = {}

    async def find_by_id(self, user_id: UserId) -> Optional[User]:
        """Find a user by ID."""
        return self._users.get(user_id)

    async def find_by_email(self, email: str) -> Optional[User]:
        """Find a user by their email."""
        for user in self._users.values():
            if user.email == email:
                return user
        return None

    async def find_by_handle(self, handle: Handle) -> Optional[User]:
        """Find a user by their handle."""
        for user in self._users.values():
            if user.handle == handle:
                return user
        return None

    async def find_by_provider_identity(
        self, provider: AuthProvider, provider_user_id: str
    ) -> Optional[User]:
        """Find a user by their external provider identity.

        Note: This is a convenience method that joins across UserIdentity.
        In-memory implementation searches all users and their identities.
        """
        # This requires joining with user identities which we don't have access to here
        # For in-memory implementation, we'll need to use UserIdentityRepository
        # This method should not be called directly in tests - use UserIdentityRepository instead
        raise NotImplementedError(
            "In-memory UserRepository does not support find_by_provider_identity. "
            "Use UserIdentityRepository.find_by_provider and then UserRepository.find_by_id"
        )

    async def save(self, user: User) -> User:
        """Save or update a user."""
        self._users[user.id] = user
        return user

    async def increment_karma(self, user_id: UserId) -> None:
        """Atomically increment user's karma by 1."""
        user = self._users.get(user_id)
        if user:
            updated_user = user.model_copy(update={"karma": user.karma + 1})
            self._users[user_id] = updated_user

    async def decrement_karma(self, user_id: UserId) -> None:
        """Atomically decrement user's karma by 1 (minimum 0)."""
        user = self._users.get(user_id)
        if user:
            updated_user = user.model_copy(update={"karma": max(0, user.karma - 1)})
            self._users[user_id] = updated_user

    async def find_all_for_tree(
        self, include_karma: bool = True
    ) -> list[tuple[UserId, Handle, int | None]]:
        """Find all users with minimal data for tree building."""
        return [
            (user.id, user.handle, user.karma if include_karma else None)
            for user in self._users.values()
        ]
