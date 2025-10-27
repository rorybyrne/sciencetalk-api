"""PostgreSQL implementation of Post repository."""

import logging
from typing import List, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from talk.domain.model import Post
from talk.domain.repository.post import PostRepository, PostSortOrder
from talk.domain.value import PostId, PostType, UserId
from talk.persistence.mappers import post_to_dict, row_to_post
from talk.persistence.tables import posts_table

logger = logging.getLogger(__name__)


class PostgresPostRepository(PostRepository):
    """PostgreSQL implementation of PostRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def find_by_id(self, post_id: PostId) -> Optional[Post]:
        """Find a post by ID."""
        logger.debug(f"DB query: SELECT post WHERE id={post_id}")
        stmt = select(posts_table).where(posts_table.c.id == post_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()

        if row:
            logger.debug(f"DB result: Found post {post_id}")
        else:
            logger.warning(f"DB result: Post {post_id} not found in database")

        return row_to_post(row._asdict()) if row else None

    async def find_all(
        self,
        sort: PostSortOrder = PostSortOrder.RECENT,
        post_type: Optional[PostType] = None,
        include_deleted: bool = False,
        limit: int = 30,
        offset: int = 0,
    ) -> List[Post]:
        """Find posts with filtering and pagination."""
        logger.debug(
            f"DB query: SELECT posts WHERE type={post_type}, "
            f"deleted={include_deleted}, sort={sort}, limit={limit}, offset={offset}"
        )

        stmt = select(posts_table)

        # Filter by type
        if post_type:
            stmt = stmt.where(posts_table.c.type == post_type.value)

        # Filter deleted
        if not include_deleted:
            stmt = stmt.where(posts_table.c.deleted_at.is_(None))

        # Sort order
        if sort == PostSortOrder.RECENT:
            stmt = stmt.order_by(desc(posts_table.c.created_at))
        else:  # ACTIVE - sort by most recent comment
            # For active sorting, we'd need a subquery to find last comment time
            # For now, fall back to created_at (can optimize later)
            stmt = stmt.order_by(desc(posts_table.c.updated_at))

        # Pagination
        stmt = stmt.limit(limit).offset(offset)

        result = await self.session.execute(stmt)
        posts = [row_to_post(row._asdict()) for row in result.fetchall()]

        logger.info(f"DB result: Found {len(posts)} posts")
        return posts

    async def find_by_author(
        self,
        author_id: UserId,
        include_deleted: bool = False,
        limit: int = 30,
        offset: int = 0,
    ) -> List[Post]:
        """Find posts by a specific author."""
        stmt = select(posts_table).where(posts_table.c.author_id == author_id)

        if not include_deleted:
            stmt = stmt.where(posts_table.c.deleted_at.is_(None))

        stmt = stmt.order_by(desc(posts_table.c.created_at)).limit(limit).offset(offset)

        result = await self.session.execute(stmt)
        return [row_to_post(row._asdict()) for row in result.fetchall()]

    async def save(self, post: Post) -> Post:
        """Save a post (create or update)."""
        existing = await self.find_by_id(post.id)

        post_dict = post_to_dict(post)

        if existing:
            # Update
            logger.info(f"DB: Updating existing post {post.id}")
            stmt = (
                posts_table.update()
                .where(posts_table.c.id == post.id)
                .values(**post_dict)
            )
            await self.session.execute(stmt)
        else:
            # Insert
            logger.info(
                f"DB: Inserting new post {post.id} "
                f"(title='{post.title}', type={post.type}, author={post.author_handle})"
            )
            stmt = posts_table.insert().values(**post_dict)
            await self.session.execute(stmt)

        await self.session.flush()
        logger.info(
            f"DB: Post {post.id} flushed to DB successfully "
            "(will be committed at end of request)"
        )
        return post

    async def delete(self, post_id: PostId) -> None:
        """Delete a post (hard delete)."""
        stmt = posts_table.delete().where(posts_table.c.id == post_id)
        await self.session.execute(stmt)
        await self.session.flush()

    async def increment_points(self, post_id: PostId) -> None:
        """Atomically increment points by 1."""
        from datetime import datetime

        stmt = (
            posts_table.update()
            .where(posts_table.c.id == post_id)
            .values(
                points=posts_table.c.points + 1,
                updated_at=datetime.now(),
            )
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def decrement_points(self, post_id: PostId) -> None:
        """Atomically decrement points by 1 (minimum 1)."""
        from datetime import datetime

        stmt = (
            posts_table.update()
            .where(posts_table.c.id == post_id)
            .where(posts_table.c.points > 1)  # Don't go below 1
            .values(
                points=posts_table.c.points - 1,
                updated_at=datetime.now(),
            )
        )
        await self.session.execute(stmt)
        await self.session.flush()
