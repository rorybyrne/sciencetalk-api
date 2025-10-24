"""Repository interfaces for Science Talk domain.

Repository interfaces are defined in the domain layer (dependency inversion).
Implementations live in the infrastructure layer.
"""

from talk.domain.repository.comment import CommentRepository
from talk.domain.repository.post import PostRepository
from talk.domain.repository.user import UserRepository
from talk.domain.repository.vote import VoteRepository

__all__ = [
    "UserRepository",
    "PostRepository",
    "CommentRepository",
    "VoteRepository",
]
