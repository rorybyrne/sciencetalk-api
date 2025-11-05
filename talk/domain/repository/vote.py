"""Vote repository interface."""

from abc import ABC, abstractmethod
from typing import List, Optional, Sequence, Union

from talk.domain.model.vote import Vote
from talk.domain.value import CommentId, PostId, UserId, VotableType, VoteId


class VoteRepository(ABC):
    """Repository for Vote entity.

    Defines the contract for vote persistence operations.
    Implementations live in the infrastructure layer.
    """

    @abstractmethod
    async def find_by_id(self, vote_id: VoteId) -> Optional[Vote]:
        """Find a vote by ID.

        Args:
            vote_id: The vote's unique identifier

        Returns:
            The vote if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_by_user_and_votable(
        self,
        user_id: UserId,
        votable_type: VotableType,
        votable_id: Union[PostId, CommentId],
    ) -> Optional[Vote]:
        """Find a user's vote on a specific item.

        Args:
            user_id: The user's ID
            votable_type: Type of item (post or comment)
            votable_id: ID of the item

        Returns:
            The vote if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_by_user(self, user_id: UserId) -> List[Vote]:
        """Find all votes by a user.

        Args:
            user_id: The user's ID

        Returns:
            List of votes by the user
        """
        pass

    @abstractmethod
    async def find_by_votable(
        self,
        votable_type: VotableType,
        votable_id: Union[PostId, CommentId],
    ) -> List[Vote]:
        """Find all votes on a specific item.

        Args:
            votable_type: Type of item (post or comment)
            votable_id: ID of the item

        Returns:
            List of votes on the item
        """
        pass

    @abstractmethod
    async def save(self, vote: Vote) -> Vote:
        """Save a vote (create).

        This may raise an error if a vote already exists for this
        user/votable combination (unique constraint violation).

        Args:
            vote: The vote to save

        Returns:
            The saved vote

        Raises:
            IntegrityError: If vote already exists (duplicate)
        """
        pass

    @abstractmethod
    async def delete(self, vote_id: VoteId) -> None:
        """Delete a vote.

        Used when a user removes their upvote.

        Args:
            vote_id: The vote ID to delete
        """
        pass

    @abstractmethod
    async def delete_by_user_and_votable(
        self,
        user_id: UserId,
        votable_type: VotableType,
        votable_id: Union[PostId, CommentId],
    ) -> bool:
        """Delete a vote by user and votable.

        Args:
            user_id: The user's ID
            votable_type: Type of item (post or comment)
            votable_id: ID of the item

        Returns:
            True if a vote was deleted, False if no vote existed
        """
        pass

    @abstractmethod
    async def count_by_votable(
        self,
        votable_type: VotableType,
        votable_id: Union[PostId, CommentId],
    ) -> int:
        """Count votes on a specific item.

        Args:
            votable_type: Type of item (post or comment)
            votable_id: ID of the item

        Returns:
            Number of votes
        """
        pass

    @abstractmethod
    async def find_by_user_and_votables(
        self,
        user_id: UserId,
        votable_type: VotableType,
        votable_ids: Sequence[Union[PostId, CommentId]],
    ) -> List[Vote]:
        """Find a user's votes on multiple items (batch query).

        Args:
            user_id: The user's ID
            votable_type: Type of items (post or comment)
            votable_ids: List of item IDs to check

        Returns:
            List of votes by the user on the specified items
        """
        pass
