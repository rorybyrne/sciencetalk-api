"""Vote domain service."""

from datetime import datetime
from uuid import UUID, uuid4

import logfire
from sqlalchemy.exc import IntegrityError

from talk.domain.model.vote import Vote
from talk.domain.repository import VoteRepository
from talk.domain.value import CommentId, PostId, UserId, VotableType, VoteId, VoteType

from .base import Service
from .comment_service import CommentService
from .post_service import PostService
from .user_service import UserService


class VoteService(Service):
    """Domain service for vote operations."""

    def __init__(
        self,
        vote_repository: VoteRepository,
        post_service: PostService,
        comment_service: CommentService,
        user_service: UserService,
    ) -> None:
        """Initialize vote service.

        Args:
            vote_repository: Vote repository
            post_service: Post domain service
            comment_service: Comment domain service
            user_service: User domain service
        """
        self.vote_repository = vote_repository
        self.post_service = post_service
        self.comment_service = comment_service
        self.user_service = user_service

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
        with logfire.span("upvote_post", post_id=str(post_id), user_id=str(user_id)):
            # Check if post exists
            post = await self.post_service.get_post_by_id(post_id)
            if not post:
                logfire.warn("Vote on non-existent post", post_id=str(post_id))
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
                logfire.warn(
                    "Duplicate vote attempt", user_id=str(user_id), post_id=str(post_id)
                )
                raise ValueError("Already voted on this post")

            # Atomically increment post points
            await self.post_service.increment_points(post_id)

            # Increment post author's karma
            await self.user_service.increment_karma(post.author_id)

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
        with logfire.span(
            "upvote_comment", comment_id=str(comment_id), user_id=str(user_id)
        ):
            # Check if comment exists
            comment = await self.comment_service.get_comment_by_id(comment_id)
            if not comment:
                logfire.warn("Vote on non-existent comment", comment_id=str(comment_id))
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
                logfire.warn(
                    "Duplicate vote attempt",
                    user_id=str(user_id),
                    comment_id=str(comment_id),
                )
                raise ValueError("Already voted on this comment")

            # Atomically increment comment points
            await self.comment_service.increment_points(comment_id)

            # Increment comment author's karma
            await self.user_service.increment_karma(comment.author_id)

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
        with logfire.span(
            "remove_vote_from_post", post_id=str(post_id), user_id=str(user_id)
        ):
            # Get post to find author before deleting vote
            post = await self.post_service.get_post_by_id(post_id)
            if not post:
                logfire.warn("Vote removal on non-existent post", post_id=str(post_id))
                return False

            # Delete vote
            deleted = await self.vote_repository.delete_by_user_and_votable(
                user_id=user_id,
                votable_type=VotableType.POST,
                votable_id=post_id,
            )

            if deleted:
                # Atomically decrement post points
                await self.post_service.decrement_points(post_id)

                # Decrement post author's karma
                await self.user_service.decrement_karma(post.author_id)

                logfire.info(
                    "Vote removed from post", post_id=str(post_id), user_id=str(user_id)
                )
            else:
                logfire.info(
                    "No vote to remove from post",
                    post_id=str(post_id),
                    user_id=str(user_id),
                )

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
        with logfire.span(
            "remove_vote_from_comment", comment_id=str(comment_id), user_id=str(user_id)
        ):
            # Get comment to find author before deleting vote
            comment = await self.comment_service.get_comment_by_id(comment_id)
            if not comment:
                logfire.warn(
                    "Vote removal on non-existent comment", comment_id=str(comment_id)
                )
                return False

            # Delete vote
            deleted = await self.vote_repository.delete_by_user_and_votable(
                user_id=user_id,
                votable_type=VotableType.COMMENT,
                votable_id=comment_id,
            )

            if deleted:
                # Atomically decrement comment points
                await self.comment_service.decrement_points(comment_id)

                # Decrement comment author's karma
                await self.user_service.decrement_karma(comment.author_id)

                logfire.info(
                    "Vote removed from comment",
                    comment_id=str(comment_id),
                    user_id=str(user_id),
                )
            else:
                logfire.info(
                    "No vote to remove from comment",
                    comment_id=str(comment_id),
                    user_id=str(user_id),
                )

            return deleted

    async def get_user_votes_for_comments(
        self, user_id: UserId, comment_ids: list[CommentId]
    ) -> dict[CommentId, bool]:
        """Check which comments a user has voted on.

        Args:
            user_id: User ID
            comment_ids: List of comment IDs to check

        Returns:
            Dictionary mapping comment ID to whether user has voted
        """
        if not comment_ids:
            return {}

        # Batch query to fetch all votes at once (avoid N+1)
        votes_list = await self.vote_repository.find_by_user_and_votables(
            user_id=user_id,
            votable_type=VotableType.COMMENT,
            votable_ids=comment_ids,
        )

        # Convert list of votes to set of voted IDs for O(1) lookup
        voted_ids = {UUID(str(vote.votable_id)) for vote in votes_list}

        # Map each comment ID to boolean (True if voted, False otherwise)
        return {cid: UUID(str(cid)) in voted_ids for cid in comment_ids}
