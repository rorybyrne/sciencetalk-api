"""PostgreSQL implementation of User repository."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from talk.domain.model import User
from talk.domain.repository import UserRepository
from talk.domain.value import BlueskyDID, Handle, UserId
from talk.persistence.mappers import row_to_user, user_to_dict
from talk.persistence.tables import users_table


class PostgresUserRepository(UserRepository):
    """PostgreSQL implementation of UserRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def find_by_id(self, user_id: UserId) -> Optional[User]:
        """Find a user by ID."""
        stmt = select(users_table).where(users_table.c.id == user_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        return row_to_user(row._asdict()) if row else None

    async def find_by_bluesky_did(self, bluesky_did: BlueskyDID) -> Optional[User]:
        """Find a user by their Bluesky DID."""
        stmt = select(users_table).where(users_table.c.bluesky_did == str(bluesky_did))
        result = await self.session.execute(stmt)
        row = result.fetchone()
        return row_to_user(row._asdict()) if row else None

    async def find_by_handle(self, handle: Handle) -> Optional[User]:
        """Find a user by their handle."""
        stmt = select(users_table).where(users_table.c.handle == str(handle))
        result = await self.session.execute(stmt)
        row = result.fetchone()
        return row_to_user(row._asdict()) if row else None

    async def save(self, user: User) -> User:
        """Save a user (create or update)."""
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

    async def exists_by_bluesky_did(self, bluesky_did: BlueskyDID) -> bool:
        """Check if a user exists with the given Bluesky DID."""
        stmt = select(users_table.c.id).where(
            users_table.c.bluesky_did == str(bluesky_did)
        )
        result = await self.session.execute(stmt)
        return result.first() is not None

    async def increment_karma(self, user_id: UserId) -> None:
        """Atomically increment user's karma by 1."""
        stmt = (
            users_table.update()
            .where(users_table.c.id == user_id)
            .values(karma=users_table.c.karma + 1)
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def decrement_karma(self, user_id: UserId) -> None:
        """Atomically decrement user's karma by 1 (minimum 0)."""
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
