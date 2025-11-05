"""In-memory vote repository for testing."""

from typing import Optional, Sequence, Union
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from talk.domain.model.vote import Vote
from talk.domain.repository.vote import VoteRepository
from talk.domain.value import CommentId, PostId, UserId, VotableType, VoteId


class InMemoryVoteRepository(VoteRepository):
    """In-memory implementation of VoteRepository for testing."""

    def __init__(self) -> None:
        self._votes: list[Vote] = []

    async def find_by_id(self, vote_id: VoteId) -> Optional[Vote]:
        """Find a vote by ID."""
        for vote in self._votes:
            if vote.id == vote_id:
                return vote
        return None

    async def find_by_user_and_votable(
        self,
        user_id: UserId,
        votable_type: VotableType,
        votable_id: PostId | CommentId,
    ) -> Optional[Vote]:
        """Find a vote by user and votable item."""
        votable_uuid = UUID(str(votable_id))
        for vote in self._votes:
            if (
                vote.user_id == user_id
                and vote.votable_type == votable_type
                and vote.votable_id == votable_uuid
            ):
                return vote
        return None

    async def find_by_user(self, user_id: UserId) -> list[Vote]:
        """Find all votes by a user."""
        return [v for v in self._votes if v.user_id == user_id]

    async def find_by_votable(
        self,
        votable_type: VotableType,
        votable_id: PostId | CommentId,
    ) -> list[Vote]:
        """Find all votes for a votable item."""
        votable_uuid = UUID(str(votable_id))
        return [
            v
            for v in self._votes
            if v.votable_type == votable_type and v.votable_id == votable_uuid
        ]

    async def save(self, vote: Vote) -> Vote:
        """Save a vote.

        Raises:
            IntegrityError: If vote already exists (duplicate)
        """
        # Check for duplicate
        votable_id = (
            PostId(vote.votable_id)
            if vote.votable_type == VotableType.POST
            else CommentId(vote.votable_id)
        )
        existing = await self.find_by_user_and_votable(
            vote.user_id, vote.votable_type, votable_id
        )
        if existing:
            raise IntegrityError("Duplicate vote", None, Exception())

        self._votes.append(vote)
        return vote

    async def delete(self, vote_id: VoteId) -> None:
        """Delete a vote by ID."""
        self._votes = [v for v in self._votes if v.id != vote_id]

    async def delete_by_user_and_votable(
        self,
        user_id: UserId,
        votable_type: VotableType,
        votable_id: PostId | CommentId,
    ) -> bool:
        """Delete a vote by user and votable item."""
        votable_uuid = UUID(str(votable_id))
        for i, vote in enumerate(self._votes):
            if (
                vote.user_id == user_id
                and vote.votable_type == votable_type
                and vote.votable_id == votable_uuid
            ):
                self._votes.pop(i)
                return True
        return False

    async def count_by_votable(
        self,
        votable_type: VotableType,
        votable_id: PostId | CommentId,
    ) -> int:
        """Count votes for a votable item."""
        votable_uuid = UUID(str(votable_id))
        return sum(
            1
            for v in self._votes
            if v.votable_type == votable_type and v.votable_id == votable_uuid
        )

    async def find_by_user_and_votables(
        self,
        user_id: UserId,
        votable_type: VotableType,
        votable_ids: Sequence[Union[PostId, CommentId]],
    ) -> list[Vote]:
        """Find a user's votes on multiple items (batch query)."""
        if not votable_ids:
            return []

        votable_uuids = {UUID(str(vid)) for vid in votable_ids}
        return [
            v
            for v in self._votes
            if v.user_id == user_id
            and v.votable_type == votable_type
            and v.votable_id in votable_uuids
        ]
