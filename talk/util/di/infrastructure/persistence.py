"""Persistence infrastructure providers."""

from collections.abc import AsyncIterator

from dishka import Scope, provide
import logfire
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from talk.config import Settings
from talk.domain.repository import (
    CommentRepository,
    InviteRepository,
    PostRepository,
    UserIdentityRepository,
    UserRepository,
    VoteRepository,
)
from talk.domain.repository.tag import TagRepository
from talk.persistence.database import create_engine, create_session_factory
from talk.persistence.repository import (
    PostgresCommentRepository,
    PostgresInviteRepository,
    PostgresPostRepository,
    PostgresUserIdentityRepository,
    PostgresUserRepository,
    PostgresVoteRepository,
)
from talk.persistence.repository.tag import PostgresTagRepository
from talk.util.di.base import ProviderBase
from talk.util.observability import instrument_sqlalchemy


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
        engine = create_engine(settings)
        # Instrument SQLAlchemy for observability
        instrument_sqlalchemy(engine)
        return engine

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
        """Provide database session for request scope.

        The session is automatically committed at the end of the request
        if no exception occurred, or rolled back if an exception was raised.
        """
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
                logfire.info("Session committed")
            except Exception as e:
                logfire.warn("Session rollback", error=str(e))
                await session.rollback()
                raise

    @provide(scope=Scope.REQUEST)
    def get_user_repository(self, session: AsyncSession) -> UserRepository:
        """Provide User repository."""
        return PostgresUserRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_user_identity_repository(
        self, session: AsyncSession
    ) -> UserIdentityRepository:
        """Provide UserIdentity repository."""
        return PostgresUserIdentityRepository(session)

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

    @provide(scope=Scope.REQUEST)
    def get_invite_repository(self, session: AsyncSession) -> InviteRepository:
        """Provide Invite repository."""
        return PostgresInviteRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_tag_repository(self, session: AsyncSession) -> TagRepository:
        """Provide Tag repository."""
        return PostgresTagRepository(session)
