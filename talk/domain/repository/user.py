"""User repository interface."""

from abc import ABC, abstractmethod
from typing import Optional

from talk.domain.model.user import User
from talk.domain.value import BlueskyDID, Handle, UserId


class UserRepository(ABC):
    """Repository for User aggregate.

    Defines the contract for user persistence operations.
    Implementations live in the infrastructure layer.
    """

    @abstractmethod
    async def find_by_id(self, user_id: UserId) -> Optional[User]:
        """Find a user by ID.

        Args:
            user_id: The user's unique identifier

        Returns:
            The user if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_by_bluesky_did(self, bluesky_did: BlueskyDID) -> Optional[User]:
        """Find a user by their Bluesky DID.

        Args:
            bluesky_did: The user's AT Protocol DID

        Returns:
            The user if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_by_handle(self, handle: Handle) -> Optional[User]:
        """Find a user by their handle.

        Args:
            handle: The user's Bluesky handle

        Returns:
            The user if found, None otherwise
        """
        pass

    @abstractmethod
    async def save(self, user: User) -> User:
        """Save a user (create or update).

        Args:
            user: The user to save

        Returns:
            The saved user
        """
        pass

    @abstractmethod
    async def exists_by_bluesky_did(self, bluesky_did: BlueskyDID) -> bool:
        """Check if a user exists with the given Bluesky DID.

        Args:
            bluesky_did: The AT Protocol DID to check

        Returns:
            True if a user exists, False otherwise
        """
        pass
