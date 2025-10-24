"""PostgreSQL implementation of Vote repository."""

from typing import List, Optional, Union

from sqlalchemy import and_, delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from talk.domain.model import Vote
from talk.domain.repository import VoteRepository
from talk.domain.value import CommentId, PostId, UserId, VotableType, VoteId
from talk.persistence.mappers import row_to_vote, vote_to_dict
from talk.persistence.tables import votes_table


class PostgresVoteRepository(VoteRepository):
    """PostgreSQL implementation of VoteRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def find_by_id(self, vote_id: VoteId) -> Optional[Vote]:
        """Find a vote by ID."""
        stmt = select(votes_table).where(votes_table.c.id == vote_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        return row_to_vote(row._asdict()) if row else None

    async def find_by_user_and_votable(
        self,
        user_id: UserId,
        votable_type: VotableType,
        votable_id: Union[PostId, CommentId],
    ) -> Optional[Vote]:
        """Find a user's vote on a specific item."""
        stmt = select(votes_table).where(
            and_(
                votes_table.c.user_id == user_id,
                votes_table.c.votable_type == votable_type.value,
                votes_table.c.votable_id == votable_id,
            )
        )
        result = await self.session.execute(stmt)
        row = result.fetchone()
        return row_to_vote(row._asdict()) if row else None

    async def find_by_user(self, user_id: UserId) -> List[Vote]:
        """Find all votes by a user."""
        stmt = select(votes_table).where(votes_table.c.user_id == user_id)
        result = await self.session.execute(stmt)
        return [row_to_vote(row._asdict()) for row in result.fetchall()]

    async def find_by_votable(
        self,
        votable_type: VotableType,
        votable_id: Union[PostId, CommentId],
    ) -> List[Vote]:
        """Find all votes on a specific item."""
        stmt = select(votes_table).where(
            and_(
                votes_table.c.votable_type == votable_type.value,
                votes_table.c.votable_id == votable_id,
            )
        )
        result = await self.session.execute(stmt)
        return [row_to_vote(row._asdict()) for row in result.fetchall()]

    async def save(self, vote: Vote) -> Vote:
        """Save a vote (create)."""
        vote_dict = vote_to_dict(vote)
        stmt = insert(votes_table).values(**vote_dict)
        await self.session.execute(stmt)
        await self.session.flush()
        return vote

    async def delete(self, vote_id: VoteId) -> None:
        """Delete a vote."""
        stmt = delete(votes_table).where(votes_table.c.id == vote_id)
        await self.session.execute(stmt)
        await self.session.flush()

    async def delete_by_user_and_votable(
        self,
        user_id: UserId,
        votable_type: VotableType,
        votable_id: Union[PostId, CommentId],
    ) -> bool:
        """Delete a vote by user and votable."""
        stmt = delete(votes_table).where(
            and_(
                votes_table.c.user_id == user_id,
                votes_table.c.votable_type == votable_type.value,
                votes_table.c.votable_id == votable_id,
            )
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0  # type: ignore[attr-defined]

    async def count_by_votable(
        self,
        votable_type: VotableType,
        votable_id: Union[PostId, CommentId],
    ) -> int:
        """Count votes on a specific item."""
        stmt = (
            select(func.count())
            .select_from(votes_table)
            .where(
                and_(
                    votes_table.c.votable_type == votable_type.value,
                    votes_table.c.votable_id == votable_id,
                )
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
