"""In-memory user repository for testing."""

from typing import Optional

from talk.domain.model.user import User
from talk.domain.repository.user import UserRepository
from talk.domain.value import BlueskyDID, Handle, UserId


class InMemoryUserRepository(UserRepository):
    """In-memory implementation of UserRepository for testing."""

    def __init__(self) -> None:
        self._users: dict[UserId, User] = {}

    async def find_by_id(self, user_id: UserId) -> Optional[User]:
        """Find a user by ID."""
        return self._users.get(user_id)

    async def find_by_bluesky_did(self, bluesky_did: BlueskyDID) -> Optional[User]:
        """Find a user by their Bluesky DID."""
        for user in self._users.values():
            if user.bluesky_did == bluesky_did:
                return user
        return None

    async def find_by_handle(self, handle: Handle) -> Optional[User]:
        """Find a user by their handle."""
        for user in self._users.values():
            if user.handle == handle:
                return user
        return None

    async def save(self, user: User) -> User:
        """Save or update a user."""
        self._users[user.id] = user
        return user

    async def exists_by_bluesky_did(self, bluesky_did: BlueskyDID) -> bool:
        """Check if a user exists with the given Bluesky DID."""
        for user in self._users.values():
            if user.bluesky_did == bluesky_did:
                return True
        return False

    async def delete(self, user_id: UserId) -> None:
        """Delete a user."""
        self._users.pop(user_id, None)
