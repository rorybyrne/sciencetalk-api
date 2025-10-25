"""Vote domain service."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError

from talk.domain.model.vote import Vote
from talk.domain.repository import VoteRepository
from talk.domain.value import CommentId, PostId, UserId, VotableType, VoteId, VoteType

from .base import Service
from .comment_service import CommentService
from .post_service import PostService


class VoteService(Service):
    """Domain service for vote operations."""

    def __init__(
        self,
        vote_repository: VoteRepository,
        post_service: PostService,
        comment_service: CommentService,
    ) -> None:
        """Initialize vote service.

        Args:
            vote_repository: Vote repository
            post_service: Post domain service
            comment_service: Comment domain service
        """
        self.vote_repository = vote_repository
        self.post_service = post_service
        self.comment_service = comment_service

    async def upvote_post(self, post_id: PostId, user_id: UserId) -> Vote:
        """Upvote a post.

        Creates vote record and atomically increments post points.

        Args:
            post_id: Post ID
            user_id: User ID

        Returns:
            Created vote

        Raises:
            ValueError: If user already voted or post not found
        """
        # Check if post exists
        post = await self.post_service.get_post_by_id(post_id)
        if not post:
            raise ValueError("Post not found")

        # Create vote (will raise IntegrityError if duplicate)
        vote = Vote(
            id=VoteId(uuid4()),
            user_id=user_id,
            votable_type=VotableType.POST,
            votable_id=UUID(str(post_id)),
            vote_type=VoteType.UP,
            created_at=datetime.now(),
        )

        try:
            saved_vote = await self.vote_repository.save(vote)
        except IntegrityError:
            raise ValueError("Already voted on this post")

        # Atomically increment post points
        await self.post_service.increment_points(post_id)

        return saved_vote

    async def upvote_comment(self, comment_id: CommentId, user_id: UserId) -> Vote:
        """Upvote a comment.

        Creates vote record and atomically increments comment points.

        Args:
            comment_id: Comment ID
            user_id: User ID

        Returns:
            Created vote

        Raises:
            ValueError: If user already voted or comment not found
        """
        # Check if comment exists
        comment = await self.comment_service.get_comment_by_id(comment_id)
        if not comment:
            raise ValueError("Comment not found")

        # Create vote (will raise IntegrityError if duplicate)
        vote = Vote(
            id=VoteId(uuid4()),
            user_id=user_id,
            votable_type=VotableType.COMMENT,
            votable_id=UUID(str(comment_id)),
            vote_type=VoteType.UP,
            created_at=datetime.now(),
        )

        try:
            saved_vote = await self.vote_repository.save(vote)
        except IntegrityError:
            raise ValueError("Already voted on this comment")

        # Atomically increment comment points
        await self.comment_service.increment_points(comment_id)

        return saved_vote

    async def remove_vote_from_post(self, post_id: PostId, user_id: UserId) -> bool:
        """Remove a vote from a post.

        Deletes vote record and atomically decrements post points.

        Args:
            post_id: Post ID
            user_id: User ID

        Returns:
            True if vote was removed, False if no vote existed
        """
        # Delete vote
        deleted = await self.vote_repository.delete_by_user_and_votable(
            user_id=user_id,
            votable_type=VotableType.POST,
            votable_id=post_id,
        )

        if deleted:
            # Atomically decrement post points
            await self.post_service.decrement_points(post_id)

        return deleted

    async def remove_vote_from_comment(
        self, comment_id: CommentId, user_id: UserId
    ) -> bool:
        """Remove a vote from a comment.

        Deletes vote record and atomically decrements comment points.

        Args:
            comment_id: Comment ID
            user_id: User ID

        Returns:
            True if vote was removed, False if no vote existed
        """
        # Delete vote
        deleted = await self.vote_repository.delete_by_user_and_votable(
            user_id=user_id,
            votable_type=VotableType.COMMENT,
            votable_id=comment_id,
        )

        if deleted:
            # Atomically decrement comment points
            await self.comment_service.decrement_points(comment_id)

        return deleted
