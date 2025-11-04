"""UserIdentity repository implementation using PostgreSQL."""

from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from talk.domain.model.user_identity import UserIdentity
from talk.domain.repository.user_identity import UserIdentityRepository
from talk.domain.value import AuthProvider, UserId, UserIdentityId
from talk.persistence.mappers import row_to_user_identity, user_identity_to_dict
from talk.persistence.tables import user_identities_table


class PostgresUserIdentityRepository(UserIdentityRepository):
    """PostgreSQL implementation of UserIdentityRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def save(self, identity: UserIdentity) -> UserIdentity:
        """Save user identity to database.

        Args:
            identity: UserIdentity to save

        Returns:
            Saved UserIdentity
        """
        identity_dict = user_identity_to_dict(identity)

        # Check if identity exists
        existing = await self.find_by_id(identity.id)

        if existing:
            # Update existing identity
            stmt = (
                user_identities_table.update()
                .where(user_identities_table.c.id == identity.id)
                .values(**identity_dict)
            )
            await self.session.execute(stmt)
        else:
            # Insert new identity
            stmt = user_identities_table.insert().values(**identity_dict)
            await self.session.execute(stmt)

        await self.session.flush()
        return identity

    async def find_by_id(self, identity_id: UserIdentityId) -> Optional[UserIdentity]:
        """Get user identity by ID.

        Args:
            identity_id: Identity ID to look up

        Returns:
            UserIdentity if found, None otherwise
        """
        stmt = select(user_identities_table).where(
            user_identities_table.c.id == identity_id
        )
        result = await self.session.execute(stmt)
        row = result.mappings().first()

        if not row:
            return None

        return row_to_user_identity(dict(row))

    async def find_by_provider(
        self, provider: AuthProvider, provider_user_id: str
    ) -> Optional[UserIdentity]:
        """Get user identity by provider and provider user ID.

        Args:
            provider: Authentication provider
            provider_user_id: Provider-specific user ID (DID, username, etc.)

        Returns:
            UserIdentity if found, None otherwise
        """
        stmt = select(user_identities_table).where(
            user_identities_table.c.provider == provider.value,
            user_identities_table.c.provider_user_id == provider_user_id,
        )
        result = await self.session.execute(stmt)
        row = result.mappings().first()

        if not row:
            return None

        return row_to_user_identity(dict(row))

    async def find_all_by_user_id(self, user_id: UserId) -> list[UserIdentity]:
        """Find all identities for a user.

        Args:
            user_id: User ID to find identities for

        Returns:
            List of UserIdentity objects (may be empty)
        """
        stmt = (
            select(user_identities_table)
            .where(user_identities_table.c.user_id == user_id)
            .order_by(user_identities_table.c.created_at)
        )
        result = await self.session.execute(stmt)
        rows = result.mappings().all()

        return [row_to_user_identity(dict(row)) for row in rows]

    async def find_primary_by_user_id(self, user_id: UserId) -> Optional[UserIdentity]:
        """Get primary identity for a user.

        Args:
            user_id: User ID to find primary identity for

        Returns:
            Primary UserIdentity if found, None otherwise
        """
        stmt = select(user_identities_table).where(
            user_identities_table.c.user_id == user_id,
            user_identities_table.c.is_primary == True,  # noqa: E712
        )
        result = await self.session.execute(stmt)
        row = result.mappings().first()

        if not row:
            return None

        return row_to_user_identity(dict(row))

    async def exists_by_provider(
        self, provider: AuthProvider, provider_user_id: str
    ) -> bool:
        """Check if an identity exists for the given provider and ID.

        Args:
            provider: The authentication provider
            provider_user_id: The user's ID on that provider

        Returns:
            True if identity exists, False otherwise
        """
        stmt = select(user_identities_table.c.id).where(
            and_(
                user_identities_table.c.provider == provider.value,
                user_identities_table.c.provider_user_id == provider_user_id,
            )
        )
        result = await self.session.execute(stmt)
        row = result.first()
        return row is not None

    async def delete(self, identity_id: UserIdentityId) -> None:
        """Delete user identity.

        Args:
            identity_id: Identity ID to delete
        """
        stmt = user_identities_table.delete().where(
            user_identities_table.c.id == identity_id
        )
        await self.session.execute(stmt)
        await self.session.flush()
