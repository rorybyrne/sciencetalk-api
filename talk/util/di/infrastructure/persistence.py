"""Persistence infrastructure providers."""

from collections.abc import AsyncIterator

from dishka import Scope, provide
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from talk.config import Settings
from talk.domain.repository import (
    CommentRepository,
    PostRepository,
    UserRepository,
    VoteRepository,
)
from talk.persistence.database import create_engine, create_session_factory
from talk.persistence.repository import (
    PostgresCommentRepository,
    PostgresPostRepository,
    PostgresUserRepository,
    PostgresVoteRepository,
)
from talk.util.di.base import ProviderBase


class PersistenceProvider(ProviderBase):
    """Persistence component base."""

    __mock_component__ = "persistence"


class ProdPersistenceProvider(PersistenceProvider):
    """Production persistence provider using PostgreSQL."""

    __is_mock__ = False

    scope = Scope.APP

    @provide(scope=Scope.APP)
    def get_engine(self, settings: Settings) -> AsyncEngine:
        """Provide database engine."""
        return create_engine(settings)

    @provide(scope=Scope.APP)
    def get_session_factory(
        self, engine: AsyncEngine
    ) -> async_sessionmaker[AsyncSession]:
        """Provide session factory."""
        return create_session_factory(engine)

    @provide(scope=Scope.REQUEST)
    async def get_session(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> AsyncIterator[AsyncSession]:
        """Provide database session for request scope."""
        async with session_factory() as session:
            yield session

    @provide(scope=Scope.REQUEST)
    def get_user_repository(self, session: AsyncSession) -> UserRepository:
        """Provide User repository."""
        return PostgresUserRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_post_repository(self, session: AsyncSession) -> PostRepository:
        """Provide Post repository."""
        return PostgresPostRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_comment_repository(self, session: AsyncSession) -> CommentRepository:
        """Provide Comment repository."""
        return PostgresCommentRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_vote_repository(self, session: AsyncSession) -> VoteRepository:
        """Provide Vote repository."""
        return PostgresVoteRepository(session)
