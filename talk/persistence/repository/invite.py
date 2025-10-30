"""PostgreSQL implementation of Invite repository."""

from sqlalchemy import and_, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from talk.domain.model import Invite
from talk.domain.repository import InviteRepository
from talk.domain.value import InviteId, InviteStatus, UserId
from talk.domain.value.types import BlueskyDID
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

    async def find_by_id(self, invite_id: InviteId) -> Invite | None:
        """Find an invite by ID."""
        stmt = select(invites_table).where(invites_table.c.id == invite_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        return row_to_invite(row._asdict()) if row else None

    async def find_pending_by_did(self, did: BlueskyDID) -> Invite | None:
        """Find a pending invite by DID.

        Critical path for login check - indexed for performance.
        DID is the primary matching identifier (handles can change).
        """
        stmt = select(invites_table).where(
            and_(
                invites_table.c.invitee_did == str(did),
                invites_table.c.status == InviteStatus.PENDING.value,
            )
        )
        result = await self.session.execute(stmt)
        row = result.fetchone()
        return row_to_invite(row._asdict()) if row else None

    async def save(self, invite: Invite) -> Invite:
        """Save an invite (create or update)."""
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
        self, inviter_id: UserId, status: InviteStatus | None = None
    ) -> int:
        """Count invites by inviter."""
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
        status: InviteStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Invite]:
        """Find invites by inviter with pagination."""
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
        return [row_to_invite(row._asdict()) for row in result.fetchall()]
