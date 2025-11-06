"""PostgreSQL implementation of Comment repository."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from talk.domain.model import Comment
from talk.domain.repository import CommentRepository
from talk.domain.value import CommentId, PostId, UserId
from talk.persistence.mappers import comment_to_dict, row_to_comment
from talk.persistence.tables import comments_table


class PostgresCommentRepository(CommentRepository):
    """PostgreSQL implementation of CommentRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    def _comment_to_db_dict(
        self, comment: Comment, exclude: Optional[Set[str]] = None
    ) -> Dict[str, Any]:
        """Convert comment to database dict with optional field exclusion.

        Args:
            comment: Comment domain model
            exclude: Set of field names to exclude

        Returns:
            Dict suitable for database insertion/update
        """
        comment_dict = comment_to_dict(comment)
        if exclude:
            return {k: v for k, v in comment_dict.items() if k not in exclude}
        return comment_dict

    async def find_by_id(self, comment_id: CommentId) -> Optional[Comment]:
        """Find a comment by ID."""
        stmt = select(comments_table).where(comments_table.c.id == comment_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        return row_to_comment(row._asdict()) if row else None

    async def find_by_post(
        self,
        post_id: PostId,
        include_deleted: bool = False,
    ) -> List[Comment]:
        """Find all comments for a post in tree order."""
        stmt = select(comments_table).where(comments_table.c.post_id == post_id)

        if not include_deleted:
            stmt = stmt.where(comments_table.c.deleted_at.is_(None))

        # Order by path for proper tree structure
        stmt = stmt.order_by(comments_table.c.path)

        result = await self.session.execute(stmt)
        return [row_to_comment(row._asdict()) for row in result.fetchall()]

    async def find_by_author(
        self,
        author_id: UserId,
        include_deleted: bool = False,
        limit: int = 30,
        offset: int = 0,
    ) -> List[Comment]:
        """Find comments by a specific author."""
        stmt = select(comments_table).where(comments_table.c.author_id == author_id)

        if not include_deleted:
            stmt = stmt.where(comments_table.c.deleted_at.is_(None))

        stmt = (
            stmt.order_by(desc(comments_table.c.created_at)).limit(limit).offset(offset)
        )

        result = await self.session.execute(stmt)
        return [row_to_comment(row._asdict()) for row in result.fetchall()]

    async def find_children(
        self,
        parent_id: CommentId,
        include_deleted: bool = False,
    ) -> List[Comment]:
        """Find direct child comments of a parent comment."""
        stmt = select(comments_table).where(comments_table.c.parent_id == parent_id)

        if not include_deleted:
            stmt = stmt.where(comments_table.c.deleted_at.is_(None))

        stmt = stmt.order_by(comments_table.c.created_at)

        result = await self.session.execute(stmt)
        return [row_to_comment(row._asdict()) for row in result.fetchall()]

    async def save(self, comment: Comment) -> Comment:
        """Save a comment (create or update)."""
        existing = await self.find_by_id(comment.id)

        if existing:
            # Update - include all fields
            comment_dict = self._comment_to_db_dict(comment)
            stmt = (
                comments_table.update()
                .where(comments_table.c.id == comment.id)
                .values(**comment_dict)
            )
            await self.session.execute(stmt)
        else:
            # Insert - exclude path and depth (set by database trigger)
            comment_dict = self._comment_to_db_dict(comment, exclude={"path", "depth"})
            stmt = comments_table.insert().values(**comment_dict)
            await self.session.execute(stmt)

        await self.session.flush()

        # Fetch the comment back to get the path/depth set by trigger
        return await self.find_by_id(comment.id) or comment

    async def delete(self, comment_id: CommentId) -> None:
        """Delete a comment (hard delete)."""
        stmt = comments_table.delete().where(comments_table.c.id == comment_id)
        await self.session.execute(stmt)
        await self.session.flush()

    async def count_by_post(self, post_id: PostId) -> int:
        """Count comments for a post (excluding deleted)."""
        stmt = (
            select(func.count())
            .select_from(comments_table)
            .where(comments_table.c.post_id == post_id)
            .where(comments_table.c.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def increment_points(self, comment_id: CommentId) -> None:
        """Atomically increment points by 1."""
        stmt = (
            comments_table.update()
            .where(comments_table.c.id == comment_id)
            .values(
                points=comments_table.c.points + 1,
                updated_at=datetime.now(),
            )
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def decrement_points(self, comment_id: CommentId) -> None:
        """Atomically decrement points by 1 (minimum 1)."""
        stmt = (
            comments_table.update()
            .where(comments_table.c.id == comment_id)
            .where(comments_table.c.points > 1)  # Don't go below 1
            .values(
                points=comments_table.c.points - 1,
                updated_at=datetime.now(),
            )
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def update_text(self, comment_id: CommentId, text: str) -> Comment | None:
        """Update the text content of a comment."""
        stmt = (
            update(comments_table)
            .where(comments_table.c.id == comment_id)
            .where(comments_table.c.deleted_at.is_(None))
            .values(
                text=text,
                updated_at=datetime.now(),
            )
            .returning(comments_table)
        )

        result = await self.session.execute(stmt)
        row = result.fetchone()

        if row is None:
            # Comment not found or deleted
            return None

        await self.session.flush()
        return row_to_comment(row._asdict())
