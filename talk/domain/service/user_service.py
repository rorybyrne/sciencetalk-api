"""User domain service."""

import logfire

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
        with logfire.span("user_service.get_user_by_id", user_id=str(user_id)):
            user = await self.user_repository.find_by_id(user_id)
            if user:
                logfire.info(
                    "User found", user_id=str(user_id), handle=user.handle.root
                )
            else:
                logfire.warn("User not found", user_id=str(user_id))
            return user

    async def get_user_by_handle(self, handle: Handle) -> User | None:
        """Get user by handle.

        Args:
            handle: User handle

        Returns:
            User if found, None otherwise
        """
        with logfire.span("user_service.get_user_by_handle", handle=handle.root):
            user = await self.user_repository.find_by_handle(handle)
            if user:
                logfire.info("User found", handle=handle.root, user_id=str(user.id))
            else:
                logfire.warn("User not found", handle=handle.root)
            return user

    async def get_user_by_email(self, email: str) -> User | None:
        """Get user by email.

        Args:
            email: User email

        Returns:
            User if found, None otherwise
        """
        with logfire.span("user_service.get_user_by_email", email=email):
            user = await self.user_repository.find_by_email(email)
            if user:
                logfire.info("User found", email=email, user_id=str(user.id))
            else:
                logfire.warn("User not found", email=email)
            return user

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
        with logfire.span(
            "user_service.get_user_by_provider_identity",
            provider=provider.value,
            provider_user_id=provider_user_id,
        ):
            user = await self.user_repository.find_by_provider_identity(
                provider, provider_user_id
            )
            if user:
                logfire.info(
                    "User found",
                    provider=provider.value,
                    provider_user_id=provider_user_id,
                    user_id=str(user.id),
                )
            else:
                logfire.warn(
                    "User not found",
                    provider=provider.value,
                    provider_user_id=provider_user_id,
                )
            return user

    async def increment_karma(self, user_id: UserId) -> None:
        """Atomically increment user's karma by 1.

        Called when someone upvotes the user's post or comment.
        Uses atomic database operation to avoid race conditions.

        Args:
            user_id: User ID
        """
        with logfire.span("user_service.increment_karma", user_id=str(user_id)):
            await self.user_repository.increment_karma(user_id)
            logfire.info("Karma incremented", user_id=str(user_id))

    async def decrement_karma(self, user_id: UserId) -> None:
        """Atomically decrement user's karma by 1.

        Called when someone removes their upvote from the user's post or comment.
        Uses atomic database operation to avoid race conditions.

        Args:
            user_id: User ID
        """
        with logfire.span("user_service.decrement_karma", user_id=str(user_id)):
            await self.user_repository.decrement_karma(user_id)
            logfire.info("Karma decremented", user_id=str(user_id))

    async def save(self, user: User) -> User:
        """Save user (create or update).

        Args:
            user: User to save

        Returns:
            Saved user
        """
        with logfire.span(
            "user_service.save", user_id=str(user.id), handle=user.handle.root
        ):
            saved = await self.user_repository.save(user)
            logfire.info("User saved", user_id=str(saved.id), handle=saved.handle.root)
            return saved
