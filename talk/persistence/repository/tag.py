"""PostgreSQL implementation of Tag repository."""

from typing import Optional

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from talk.domain.model.tag import Tag
from talk.domain.repository.tag import TagRepository
from talk.domain.value import TagId, TagName
from talk.persistence.mappers import row_to_tag, tag_to_dict
from talk.persistence.tables import tags_table


class PostgresTagRepository(TagRepository):
    """PostgreSQL implementation of TagRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: Async database session
        """
        self.session = session

    async def save(self, tag: Tag) -> Tag:
        """Save or update a tag."""
        tag_dict = tag_to_dict(tag)

        # Try to find existing tag
        existing = await self.find_by_id(tag.id)

        if existing:
            # Update existing
            stmt = (
                update(tags_table).where(tags_table.c.id == tag.id).values(**tag_dict)
            )
            await self.session.execute(stmt)
        else:
            # Insert new
            stmt = insert(tags_table).values(**tag_dict)
            await self.session.execute(stmt)

        await self.session.flush()
        return tag

    async def find_by_id(self, tag_id: TagId) -> Optional[Tag]:
        """Find tag by ID."""
        stmt = select(tags_table).where(tags_table.c.id == tag_id)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        return row_to_tag(row._asdict()) if row else None

    async def find_by_name(self, name: TagName) -> Optional[Tag]:
        """Find tag by name."""
        stmt = select(tags_table).where(tags_table.c.name == name.root)
        result = await self.session.execute(stmt)
        row = result.fetchone()
        return row_to_tag(row._asdict()) if row else None

    async def find_by_names(self, names: list[TagName]) -> list[Tag]:
        """Find multiple tags by names in a single query."""
        if not names:
            return []

        stmt = select(tags_table).where(
            tags_table.c.name.in_([name.root for name in names])
        )
        result = await self.session.execute(stmt)
        rows = result.fetchall()
        return [row_to_tag(row._asdict()) for row in rows]

    async def find_all(self, limit: int = 100, order_by: str = "name") -> list[Tag]:
        """Find all tags."""
        stmt = select(tags_table).limit(limit)

        # Order by requested field
        if order_by == "created_at":
            stmt = stmt.order_by(tags_table.c.created_at.desc())
        else:
            stmt = stmt.order_by(tags_table.c.name)

        result = await self.session.execute(stmt)
        rows = result.fetchall()
        return [row_to_tag(row._asdict()) for row in rows]

    async def delete(self, tag_id: TagId) -> None:
        """Delete a tag."""
        stmt = delete(tags_table).where(tags_table.c.id == tag_id)
        await self.session.execute(stmt)
        await self.session.flush()
