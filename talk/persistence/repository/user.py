"""PostgreSQL implementation of User repository."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from talk.domain.model import User
from talk.domain.repository import UserRepository
from talk.domain.value import AuthProvider, UserId
from talk.domain.value.types import Handle
from talk.persistence.mappers import row_to_user, user_to_dict
from talk.persistence.tables import user_identities_table, users_table


class PostgresUserRepository(UserRepository):
    """PostgreSQL implementation of UserRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def find_by_id(self, user_id: UserId) -> Optional[User]:
        """Find a user by ID.

        Args:
            user_id: User ID to look up

        Returns:
            User if found, None otherwise
        """
        stmt = select(users_table).where(users_table.c.id == user_id)
        result = await self.session.execute(stmt)
        row = result.mappings().first()
        return row_to_user(dict(row)) if row else None

    async def find_by_handle(self, handle: Handle) -> Optional[User]:
        """Find a user by their handle.

        Args:
            handle: Handle to search for

        Returns:
            User if found, None otherwise
        """
        stmt = select(users_table).where(users_table.c.handle == handle.root)
        result = await self.session.execute(stmt)
        row = result.mappings().first()
        return row_to_user(dict(row)) if row else None

    async def find_by_email(self, email: str) -> Optional[User]:
        """Find a user by their email.

        Args:
            email: Email to search for

        Returns:
            User if found, None otherwise
        """
        stmt = select(users_table).where(users_table.c.email == email)
        result = await self.session.execute(stmt)
        row = result.mappings().first()
        return row_to_user(dict(row)) if row else None

    async def find_by_provider_identity(
        self, provider: AuthProvider, provider_user_id: str
    ) -> Optional[User]:
        """Find a user by their external provider identity.

        This is a convenience method that joins user_identities and users tables.

        Args:
            provider: The authentication provider
            provider_user_id: The user's ID on that provider

        Returns:
            User if found, None otherwise
        """
        stmt = (
            select(users_table)
            .select_from(
                users_table.join(
                    user_identities_table,
                    users_table.c.id == user_identities_table.c.user_id,
                )
            )
            .where(user_identities_table.c.provider == provider.value)
            .where(user_identities_table.c.provider_user_id == provider_user_id)
        )
        result = await self.session.execute(stmt)
        row = result.mappings().first()
        return row_to_user(dict(row)) if row else None

    async def save(self, user: User) -> User:
        """Save a user (create or update).

        Args:
            user: User to save

        Returns:
            Saved user
        """
        # Check if user exists
        existing = await self.find_by_id(user.id)

        user_dict = user_to_dict(user)

        if existing:
            # Update
            stmt = (
                users_table.update()
                .where(users_table.c.id == user.id)
                .values(**user_dict)
            )
            await self.session.execute(stmt)
        else:
            # Insert
            stmt = users_table.insert().values(**user_dict)
            await self.session.execute(stmt)

        await self.session.flush()
        return user

    async def increment_karma(self, user_id: UserId) -> None:
        """Atomically increment user's karma by 1.

        Args:
            user_id: User ID to update
        """
        stmt = (
            users_table.update()
            .where(users_table.c.id == user_id)
            .values(karma=users_table.c.karma + 1)
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def decrement_karma(self, user_id: UserId) -> None:
        """Atomically decrement user's karma by 1 (minimum 0).

        Args:
            user_id: User ID to update
        """
        from sqlalchemy import case

        stmt = (
            users_table.update()
            .where(users_table.c.id == user_id)
            .values(
                karma=case((users_table.c.karma > 0, users_table.c.karma - 1), else_=0)
            )
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def find_all_for_tree(
        self, include_karma: bool = True
    ) -> list[tuple[UserId, Handle, int | None]]:
        """Find all users with minimal data for tree building.

        Optimized query that fetches only id, handle, and optionally karma.
        This reduces data transfer and improves performance for tree building.

        Args:
            include_karma: Whether to include karma (default: True)

        Returns:
            List of (user_id, handle, karma) tuples
        """
        if include_karma:
            stmt = select(users_table.c.id, users_table.c.handle, users_table.c.karma)
        else:
            stmt = select(users_table.c.id, users_table.c.handle)

        result = await self.session.execute(stmt)
        rows = result.all()

        if include_karma:
            return [(UserId(row.id), Handle(row.handle), row.karma) for row in rows]
        else:
            return [(UserId(row.id), Handle(row.handle), None) for row in rows]
