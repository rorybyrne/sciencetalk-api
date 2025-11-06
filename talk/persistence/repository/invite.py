"""PostgreSQL implementation of Invite repository."""

from typing import Optional

from sqlalchemy import and_, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from talk.domain.model import Invite
from talk.domain.repository import InviteRepository
from talk.domain.value import AuthProvider, InviteId, InviteStatus, InviteToken, UserId
from talk.persistence.mappers import invite_to_dict, row_to_invite
from talk.persistence.tables import invites_table


class PostgresInviteRepository(InviteRepository):
    """PostgreSQL implementation of InviteRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def find_by_id(self, invite_id: InviteId) -> Optional[Invite]:
        """Find an invite by ID.

        Args:
            invite_id: Invite ID to look up

        Returns:
            Invite if found, None otherwise
        """
        stmt = select(invites_table).where(invites_table.c.id == invite_id)
        result = await self.session.execute(stmt)
        row = result.mappings().first()
        return row_to_invite(dict(row)) if row else None

    async def find_by_token(self, token: InviteToken) -> Optional[Invite]:
        """Find an invite by its token.

        Args:
            token: Invite token to look up

        Returns:
            Invite if found, None otherwise
        """
        stmt = select(invites_table).where(invites_table.c.invite_token == token.root)
        result = await self.session.execute(stmt)
        row = result.mappings().first()
        return row_to_invite(dict(row)) if row else None

    async def find_pending_by_provider_identity(
        self, provider: AuthProvider, provider_user_id: str
    ) -> Optional[Invite]:
        """Find a pending invite by provider and provider user ID.

        Critical path for login check - indexed for performance.

        Args:
            provider: Authentication provider
            provider_user_id: Provider-specific user ID (DID, username, etc.)

        Returns:
            Invite if found, None otherwise
        """
        stmt = select(invites_table).where(
            and_(
                invites_table.c.provider == provider.value,
                invites_table.c.invitee_provider_id == provider_user_id,
                invites_table.c.status == InviteStatus.PENDING.value,
            )
        )
        result = await self.session.execute(stmt)
        row = result.mappings().first()
        return row_to_invite(dict(row)) if row else None

    async def exists_pending_for_provider_identity(
        self, provider: AuthProvider, provider_user_id: str
    ) -> bool:
        """Check if a pending invite exists for provider identity.

        Fast check without loading full invite data.

        Args:
            provider: Authentication provider
            provider_user_id: Provider-specific user ID

        Returns:
            True if pending invite exists, False otherwise
        """
        stmt = select(invites_table.c.id).where(
            and_(
                invites_table.c.provider == provider.value,
                invites_table.c.invitee_provider_id == provider_user_id,
                invites_table.c.status == InviteStatus.PENDING.value,
            )
        )
        result = await self.session.execute(stmt)
        return result.first() is not None

    async def save(self, invite: Invite) -> Invite:
        """Save an invite (create or update).

        Args:
            invite: Invite to save

        Returns:
            Saved invite
        """
        invite_dict = invite_to_dict(invite)

        # Check if invite exists
        existing = await self.find_by_id(invite.id)

        if existing:
            # Update existing
            stmt = (
                update(invites_table)
                .where(invites_table.c.id == invite.id)
                .values(**invite_dict)
            )
            await self.session.execute(stmt)
        else:
            # Insert new
            stmt = insert(invites_table).values(**invite_dict)
            await self.session.execute(stmt)

        await self.session.flush()
        return invite

    async def count_by_inviter(
        self, inviter_id: UserId, status: Optional[InviteStatus] = None
    ) -> int:
        """Count invites by inviter.

        Args:
            inviter_id: Inviter user ID
            status: Optional filter by status

        Returns:
            Count of matching invites
        """
        stmt = (
            select(func.count())
            .select_from(invites_table)
            .where(invites_table.c.inviter_id == inviter_id)
        )

        if status:
            stmt = stmt.where(invites_table.c.status == status.value)

        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def find_by_inviter(
        self,
        inviter_id: UserId,
        status: Optional[InviteStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Invite]:
        """Find invites by inviter with pagination.

        Args:
            inviter_id: Inviter user ID
            status: Optional filter by status
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of matching invites
        """
        stmt = (
            select(invites_table)
            .where(invites_table.c.inviter_id == inviter_id)
            .order_by(invites_table.c.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        if status:
            stmt = stmt.where(invites_table.c.status == status.value)

        result = await self.session.execute(stmt)
        rows = result.mappings().all()
        return [row_to_invite(dict(row)) for row in rows]

    async def find_all_accepted_relationships(self) -> list[tuple[UserId, UserId]]:
        """Find all accepted invite relationships for tree building.

        Optimized query using composite index idx_invites_tree_relationships
        to efficiently fetch only the parent-child ID pairs needed for
        building the user invitation tree.

        Returns:
            List of (inviter_id, accepted_by_user_id) tuples
        """
        stmt = select(
            invites_table.c.inviter_id, invites_table.c.accepted_by_user_id
        ).where(
            and_(
                invites_table.c.status == InviteStatus.ACCEPTED.value,
                invites_table.c.accepted_by_user_id.is_not(None),
            )
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            (UserId(row.inviter_id), UserId(row.accepted_by_user_id)) for row in rows
        ]
