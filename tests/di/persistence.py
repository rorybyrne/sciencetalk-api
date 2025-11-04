"""Mock persistence providers for testing."""

from dishka import Scope, provide

from talk.domain.repository import (
    CommentRepository,
    InviteRepository,
    PostRepository,
    UserIdentityRepository,
    UserRepository,
    VoteRepository,
)
from talk.domain.repository.tag import TagRepository
from talk.persistence.repository.inmemory import (
    InMemoryCommentRepository,
    InMemoryInviteRepository,
    InMemoryPostRepository,
    InMemoryUserIdentityRepository,
    InMemoryUserRepository,
    InMemoryVoteRepository,
)
from talk.persistence.repository.inmemory.tag import InMemoryTagRepository
from talk.util.di.infrastructure.persistence import PersistenceProvider


class MockPersistenceProvider(PersistenceProvider):
    """Mock persistence provider using in-memory repositories.

    Uses REQUEST scope to ensure test isolation - each test gets fresh repositories.
    """

    __is_mock__ = True

    @provide(scope=Scope.REQUEST)
    def get_user_repository(self) -> UserRepository:
        """Provide in-memory user repository."""
        return InMemoryUserRepository()

    @provide(scope=Scope.REQUEST)
    def get_user_identity_repository(self) -> UserIdentityRepository:
        """Provide in-memory user identity repository."""
        return InMemoryUserIdentityRepository()

    @provide(scope=Scope.REQUEST)
    def get_post_repository(self) -> PostRepository:
        """Provide in-memory post repository."""
        return InMemoryPostRepository()

    @provide(scope=Scope.REQUEST)
    def get_comment_repository(self) -> CommentRepository:
        """Provide in-memory comment repository."""
        return InMemoryCommentRepository()

    @provide(scope=Scope.REQUEST)
    def get_vote_repository(self) -> VoteRepository:
        """Provide in-memory vote repository."""
        return InMemoryVoteRepository()

    @provide(scope=Scope.REQUEST)
    def get_invite_repository(self) -> InviteRepository:
        """Provide in-memory invite repository."""
        return InMemoryInviteRepository()

    @provide(scope=Scope.REQUEST)
    def get_tag_repository(self) -> TagRepository:
        """Provide in-memory tag repository."""
        return InMemoryTagRepository()
