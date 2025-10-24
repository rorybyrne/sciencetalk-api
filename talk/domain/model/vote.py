"""Vote entity.

Votes represent community curation through an upvote-only system.
Each user can cast one vote per item (post or comment).
"""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from talk.domain.model.common import DomainModel
from talk.domain.value import UserId, VotableType, VoteId, VoteType


class Vote(DomainModel):
    """Vote entity.

    Represents an upvote on a post or comment.
    Business rules:
    - One vote per user per item (enforced by database unique constraint)
    - Only upvotes (no downvotes) to encourage positive engagement
    - Polymorphic reference to votable (post or comment)
    """

    id: VoteId
    user_id: UserId
    votable_type: VotableType
    votable_id: UUID  # PostId or CommentId (both are UUIDs)
    vote_type: VoteType = VoteType.UP
    created_at: datetime = Field(default_factory=datetime.now)
