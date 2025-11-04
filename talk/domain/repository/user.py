"""User repository interface."""

from abc import ABC, abstractmethod
from typing import Optional

from talk.domain.model.user import User
from talk.domain.value import AuthProvider, UserId
from talk.domain.value.types import Handle


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
    async def find_by_handle(self, handle: Handle) -> Optional[User]:
        """Find a user by their handle.

        Args:
            handle: The user's handle

        Returns:
            The user if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_by_email(self, email: str) -> Optional[User]:
        """Find a user by their email.

        Args:
            email: The user's email address

        Returns:
            The user if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_by_provider_identity(
        self, provider: AuthProvider, provider_user_id: str
    ) -> Optional[User]:
        """Find a user by their external provider identity.

        Args:
            provider: The authentication provider
            provider_user_id: The user's ID on that provider

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
    async def increment_karma(self, user_id: UserId) -> None:
        """Atomically increment user's karma by 1.

        Args:
            user_id: The user's unique identifier
        """
        pass

    @abstractmethod
    async def decrement_karma(self, user_id: UserId) -> None:
        """Atomically decrement user's karma by 1 (minimum 0).

        Args:
            user_id: The user's unique identifier
        """
        pass
