"""Domain model entities for Science Talk."""

from talk.domain.model.comment import Comment
from talk.domain.model.post import Post
from talk.domain.model.user import User
from talk.domain.model.vote import Vote

__all__ = [
    "User",
    "Post",
    "Comment",
    "Vote",
]
