"""Database connection and session management.

Provides async database engine and session factory for PostgreSQL.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from talk.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    """Create async database engine.

    Args:
        settings: Application settings with database URL

    Returns:
        Configured async engine
    """
    return create_async_engine(
        settings.database_url,
        echo=settings.debug,  # Log SQL queries in debug mode
        pool_pre_ping=True,  # Verify connections before using
        pool_size=5,  # Connection pool size
        max_overflow=10,  # Max connections beyond pool_size
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create async session factory.

    Args:
        engine: Database engine

    Returns:
        Session factory for creating database sessions
    """
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,  # Don't expire objects after commit
        autoflush=False,  # Manual flushing for better control
        autocommit=False,  # Explicit transaction management
    )


@asynccontextmanager
async def get_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """Get database session with automatic cleanup.

    Args:
        session_factory: Factory for creating sessions

    Yields:
        Database session
    """
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
