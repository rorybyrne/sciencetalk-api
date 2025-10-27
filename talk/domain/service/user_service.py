"""User domain service."""

from talk.domain.model import User
from talk.domain.repository import UserRepository
from talk.domain.value import UserId
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
