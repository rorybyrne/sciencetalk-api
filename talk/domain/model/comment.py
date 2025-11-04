"""Comment entity.

Comments are threaded/nested discussions on posts with unlimited depth.
They use a materialized path (ltree) for efficient tree queries.
"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from talk.domain.model.common import DomainModel
from talk.domain.value import CommentId, PostId, UserId
from talk.domain.value.types import Handle


class Comment(DomainModel):
    """Comment entity.

    Represents a comment on a post or a reply to another comment.
    Comments can be nested with unlimited depth.

    Threading is managed through:
    - parent_id: Direct parent comment (None for top-level)
    - depth: Nesting level (0 for top-level, increments with each reply)
    - path: Materialized path for efficient tree queries (managed by DB)
    """

    id: CommentId
    post_id: PostId
    author_id: UserId
    author_handle: Handle
    text: str = Field(min_length=1, max_length=10000)
    parent_id: Optional[CommentId] = None
    depth: int = Field(default=0, ge=0)
    path: Optional[str] = None  # Managed by database trigger
    points: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    deleted_at: Optional[datetime] = None
