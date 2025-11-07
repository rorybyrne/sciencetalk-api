"""PostgreSQL implementation of Post repository."""

from collections import defaultdict
from typing import List, Optional
from uuid import UUID

import logfire
from sqlalchemy import delete, desc, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from talk.config import Settings
from talk.domain.model import Post
from talk.domain.repository.post import PostRepository, PostSortOrder
from talk.domain.value import PostId, Slug, TagName, UserId
from talk.persistence.mappers import post_to_dict, row_to_post
from talk.persistence.tables import post_tags_table, posts_table, tags_table


class PostgresPostRepository(PostRepository):
    """PostgreSQL implementation of PostRepository."""

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
            settings: Application settings
        """
        self.session = session
        self.settings = settings

    async def _fetch_tags_for_posts(
        self, post_ids: list[UUID]
    ) -> dict[UUID, list[str]]:
        """Fetch tags for multiple posts in a single query.

        Args:
            post_ids: List of post IDs

        Returns:
            Dict mapping post_id -> list of tag names
        """
        if not post_ids:
            return {}

        stmt = (
            select(post_tags_table.c.post_id, tags_table.c.name)
            .select_from(post_tags_table)
            .join(tags_table, post_tags_table.c.tag_id == tags_table.c.id)
            .where(post_tags_table.c.post_id.in_(post_ids))
        )
        result = await self.session.execute(stmt)
        rows = result.fetchall()

        # Build lookup: post_id -> [tag_names]
        post_tag_map: dict[UUID, list[str]] = defaultdict(list)
        for row in rows:
            post_tag_map[row.post_id].append(row.name)

        return post_tag_map

    async def find_by_id(self, post_id: PostId) -> Optional[Post]:
        """Find a post by ID."""
        with logfire.span("post_repository.find_by_id", post_id=str(post_id)):
            stmt = select(posts_table).where(posts_table.c.id == post_id)
            result = await self.session.execute(stmt)
            row = result.fetchone()

            if not row:
                logfire.warn("Post not found", post_id=str(post_id))
                return None

            # Fetch tags for this post
            post_tag_map = await self._fetch_tags_for_posts([post_id])
            tag_names = post_tag_map.get(post_id, [])

            return row_to_post(row._asdict(), tag_names=tag_names)

    async def find_by_slug(self, slug: Slug) -> Optional[Post]:
        """Find a post by slug.

        Note: Returns None if post is deleted (even though slug is globally unique).
        """
        with logfire.span("post_repository.find_by_slug", slug=str(slug)):
            stmt = select(posts_table).where(
                posts_table.c.slug == str(slug),
                posts_table.c.deleted_at.is_(None),  # Exclude deleted for API access
            )
            result = await self.session.execute(stmt)
            row = result.fetchone()

            if not row:
                logfire.warn("Post not found by slug or is deleted", slug=str(slug))
                return None

            # Fetch tags for this post
            post_tag_map = await self._fetch_tags_for_posts([row.id])
            tag_names = post_tag_map.get(row.id, [])

            return row_to_post(row._asdict(), tag_names=tag_names)

    async def slug_exists(self, slug: Slug) -> bool:
        """Check if a slug exists (globally - includes deleted posts)."""
        with logfire.span("post_repository.slug_exists", slug=str(slug)):
            stmt = (
                select(func.count())
                .select_from(posts_table)
                .where(
                    posts_table.c.slug == str(slug),
                    # NOTE: Check ALL posts (including deleted) for global uniqueness
                )
            )
            result = await self.session.execute(stmt)
            count = result.scalar()
            exists = (count or 0) > 0

            logfire.debug("Slug existence check", slug=str(slug), exists=exists)
            return exists

    async def find_all(
        self,
        sort: PostSortOrder = PostSortOrder.RECENT,
        tag: Optional[TagName] = None,
        include_deleted: bool = False,
        limit: int = 30,
        offset: int = 0,
    ) -> List[Post]:
        """Find posts with filtering and pagination."""
        with logfire.span(
            "post_repository.find_all",
            sort=sort.value,
            tag=tag.root if tag else None,
            include_deleted=include_deleted,
            limit=limit,
            offset=offset,
        ):
            stmt = select(posts_table)

            # Filter by tag (join with post_tags and tags tables)
            if tag:
                stmt = (
                    stmt.select_from(posts_table)
                    .join(
                        post_tags_table, posts_table.c.id == post_tags_table.c.post_id
                    )
                    .join(tags_table, post_tags_table.c.tag_id == tags_table.c.id)
                    .where(tags_table.c.name == tag.root)
                )

            # Filter deleted
            if not include_deleted:
                stmt = stmt.where(posts_table.c.deleted_at.is_(None))

            # Sort order
            if sort == PostSortOrder.RECENT:
                stmt = stmt.order_by(desc(posts_table.c.created_at))
            elif sort == PostSortOrder.ACTIVE:
                stmt = stmt.order_by(desc(posts_table.c.comments_updated_at))
            elif sort == PostSortOrder.HOT:
                # Time-decay ranking: points / (age_hours + offset)^gravity
                # No -1 penalty: new posts are visible but don't dominate
                gravity = self.settings.ranking.gravity
                time_offset = self.settings.ranking.time_offset

                # Calculate age in hours
                age_hours = (
                    func.extract("epoch", func.now() - posts_table.c.created_at) / 3600
                )

                # Calculate score
                score = posts_table.c.points / func.pow(
                    age_hours + time_offset, gravity
                )

                stmt = stmt.order_by(desc(score))

            # Pagination
            stmt = stmt.limit(limit).offset(offset)

            result = await self.session.execute(stmt)
            post_rows = result.fetchall()

            if not post_rows:
                logfire.info("No posts found")
                return []

            # Fetch tags for all posts in a single query
            post_ids = [row.id for row in post_rows]
            post_tag_map = await self._fetch_tags_for_posts(post_ids)

            # Build Post domain models with tags
            posts = []
            for row in post_rows:
                tag_names = post_tag_map.get(row.id, [])
                posts.append(row_to_post(row._asdict(), tag_names=tag_names))

            logfire.info("Found posts", count=len(posts))
            return posts

    async def count(
        self,
        tag: Optional[TagName] = None,
        include_deleted: bool = False,
    ) -> int:
        """Count posts matching the given filters."""
        with logfire.span(
            "post_repository.count",
            tag=tag.root if tag else None,
            include_deleted=include_deleted,
        ):
            stmt = select(func.count()).select_from(posts_table)

            # Filter by tag (join with post_tags and tags tables)
            if tag:
                stmt = (
                    stmt.join(
                        post_tags_table, posts_table.c.id == post_tags_table.c.post_id
                    )
                    .join(tags_table, post_tags_table.c.tag_id == tags_table.c.id)
                    .where(tags_table.c.name == tag.root)
                )

            # Filter deleted
            if not include_deleted:
                stmt = stmt.where(posts_table.c.deleted_at.is_(None))

            result = await self.session.execute(stmt)
            count = result.scalar() or 0
            logfire.info("Post count", count=count)
            return count

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
        post_rows = result.fetchall()

        if not post_rows:
            return []

        # Fetch tags for all posts
        post_ids = [row.id for row in post_rows]
        post_tag_map = await self._fetch_tags_for_posts(post_ids)

        # Build Post domain models with tags
        posts = []
        for row in post_rows:
            tag_names = post_tag_map.get(row.id, [])
            posts.append(row_to_post(row._asdict(), tag_names=tag_names))

        return posts

    async def save(self, post: Post) -> Post:
        """Save a post (create or update)."""
        with logfire.span(
            "post_repository.save",
            post_id=str(post.id),
            title=post.title,
            tags=[t.root for t in post.tag_names],
        ):
            existing = await self.find_by_id(post.id)

            post_dict = post_to_dict(post)  # Note: tag_names are excluded by mapper

            if existing:
                # Update post
                logfire.info("Updating existing post", post_id=str(post.id))
                stmt = (
                    posts_table.update()
                    .where(posts_table.c.id == post.id)
                    .values(**post_dict)
                )
                await self.session.execute(stmt)

                # Delete existing post_tags
                delete_stmt = delete(post_tags_table).where(
                    post_tags_table.c.post_id == post.id
                )
                await self.session.execute(delete_stmt)
            else:
                # Insert new post
                logfire.info(
                    "Inserting new post",
                    post_id=str(post.id),
                    title=post.title,
                    tags=[t.root for t in post.tag_names],
                    author=post.author_handle.root,
                )
                stmt = posts_table.insert().values(**post_dict)
                await self.session.execute(stmt)

            # Insert post_tags relationships
            # First, we need to look up tag IDs from tag names
            tag_lookup_stmt = select(tags_table.c.id, tags_table.c.name).where(
                tags_table.c.name.in_([tag.root for tag in post.tag_names])
            )
            tag_result = await self.session.execute(tag_lookup_stmt)
            tag_rows = tag_result.fetchall()

            # Build mapping: tag_name -> tag_id
            tag_id_map = {row.name: row.id for row in tag_rows}

            # Insert post_tags
            for tag_name in post.tag_names:
                tag_id = tag_id_map.get(tag_name.root)
                if tag_id:
                    post_tag_stmt = insert(post_tags_table).values(
                        post_id=post.id, tag_id=tag_id
                    )
                    await self.session.execute(post_tag_stmt)

            await self.session.flush()
            logfire.info("Post saved successfully", post_id=str(post.id))
            return post

    async def delete(self, post_id: PostId) -> None:
        """Delete a post (hard delete)."""
        stmt = posts_table.delete().where(posts_table.c.id == post_id)
        await self.session.execute(stmt)
        await self.session.flush()

    async def increment_points(self, post_id: PostId) -> None:
        """Atomically increment points by 1."""
        stmt = (
            posts_table.update()
            .where(posts_table.c.id == post_id)
            .values(points=posts_table.c.points + 1)
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def decrement_points(self, post_id: PostId) -> None:
        """Atomically decrement points by 1 (minimum 1)."""
        stmt = (
            posts_table.update()
            .where(posts_table.c.id == post_id)
            .where(posts_table.c.points > 1)  # Don't go below 1
            .values(points=posts_table.c.points - 1)
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def update_text(self, post_id: PostId, text: str | None) -> Post | None:
        """Update the text content of a post."""
        with logfire.span(
            "post_repository.update_text",
            post_id=str(post_id),
            text_length=len(text) if text else 0,
        ):
            stmt = (
                update(posts_table)
                .where(posts_table.c.id == post_id)
                .where(posts_table.c.deleted_at.is_(None))
                .values(
                    text=text,
                    content_updated_at=func.now(),
                )
                .returning(posts_table)
            )

            result = await self.session.execute(stmt)
            row = result.fetchone()

            if row is None:
                logfire.warn("Post not found or deleted", post_id=str(post_id))
                return None

            # Fetch tags for this post
            post_tag_map = await self._fetch_tags_for_posts([post_id])
            tag_names = post_tag_map.get(post_id, [])

            await self.session.flush()
            return row_to_post(row._asdict(), tag_names=tag_names)
