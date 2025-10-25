"""PostgreSQL repository implementations."""

from talk.persistence.repository.comment import PostgresCommentRepository
from talk.persistence.repository.invite import PostgresInviteRepository
from talk.persistence.repository.post import PostgresPostRepository
from talk.persistence.repository.user import PostgresUserRepository
from talk.persistence.repository.vote import PostgresVoteRepository

__all__ = [
    "PostgresUserRepository",
    "PostgresPostRepository",
    "PostgresCommentRepository",
    "PostgresVoteRepository",
    "PostgresInviteRepository",
]
