"""User domain service."""

from talk.domain.model import User
from talk.domain.repository import UserRepository
from talk.domain.value import AuthProvider, UserId
from talk.domain.value.types import Handle


class UserService:
    """Domain service for user operations."""

    def __init__(self, user_repository: UserRepository) -> None:
        """Initialize user service.

        Args:
            user_repository: User repository
        """
        self.user_repository = user_repository

    async def get_user_by_id(self, user_id: UserId) -> User | None:
        """Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User if found, None otherwise
        """
        return await self.user_repository.find_by_id(user_id)

    async def get_user_by_handle(self, handle: Handle) -> User | None:
        """Get user by handle.

        Args:
            handle: User handle

        Returns:
            User if found, None otherwise
        """
        return await self.user_repository.find_by_handle(handle)

    async def get_user_by_email(self, email: str) -> User | None:
        """Get user by email.

        Args:
            email: User email

        Returns:
            User if found, None otherwise
        """
        return await self.user_repository.find_by_email(email)

    async def get_user_by_provider_identity(
        self, provider: AuthProvider, provider_user_id: str
    ) -> User | None:
        """Get user by provider identity.

        Args:
            provider: Authentication provider
            provider_user_id: Provider-specific user ID

        Returns:
            User if found, None otherwise
        """
        return await self.user_repository.find_by_provider_identity(
            provider, provider_user_id
        )

    async def increment_karma(self, user_id: UserId) -> None:
        """Atomically increment user's karma by 1.

        Called when someone upvotes the user's post or comment.
        Uses atomic database operation to avoid race conditions.

        Args:
            user_id: User ID
        """
        await self.user_repository.increment_karma(user_id)

    async def decrement_karma(self, user_id: UserId) -> None:
        """Atomically decrement user's karma by 1.

        Called when someone removes their upvote from the user's post or comment.
        Uses atomic database operation to avoid race conditions.

        Args:
            user_id: User ID
        """
        await self.user_repository.decrement_karma(user_id)

    async def save(self, user: User) -> User:
        """Save user (create or update).

        Args:
            user: User to save

        Returns:
            Saved user
        """
        return await self.user_repository.save(user)
