"""Tag domain service."""

import logfire

from talk.domain.model.tag import Tag
from talk.domain.repository.tag import TagRepository
from talk.domain.value import TagName

from .base import Service


class TagService(Service):
    """Domain service for tag operations."""

    def __init__(self, tag_repository: TagRepository) -> None:
        """Initialize tag service.

        Args:
            tag_repository: Tag repository
        """
        self.tag_repository = tag_repository

    async def validate_tags_exist(self, tag_names: list[TagName]) -> list[Tag]:
        """Validate that all requested tags exist.

        Args:
            tag_names: List of tag names to validate

        Returns:
            List of found tags

        Raises:
            ValueError: If any tags are not found
        """
        with logfire.span(
            "tag_service.validate_tags_exist", tags=[t.root for t in tag_names]
        ):
            # Batch fetch tags
            tags = await self.tag_repository.find_by_names(tag_names)

            # Check that all requested tags were found
            found_names = {tag.name.root for tag in tags}
            requested_names = {name.root for name in tag_names}
            missing = requested_names - found_names

            if missing:
                raise ValueError(f"Tags not found: {', '.join(sorted(missing))}")

            logfire.info("All tags validated", count=len(tags))
            return tags

    async def get_all_tags(self, limit: int = 100, order_by: str = "name") -> list[Tag]:
        """Get all available tags.

        Args:
            limit: Maximum number of tags to return
            order_by: Field to order by ('name' or 'created_at')

        Returns:
            List of tags
        """
        with logfire.span("tag_service.get_all_tags", limit=limit, order_by=order_by):
            tags = await self.tag_repository.find_all(limit=limit, order_by=order_by)
            logfire.info("Tags retrieved", count=len(tags))
            return tags

    async def get_tag_by_name(self, name: TagName) -> Tag | None:
        """Get a tag by name.

        Args:
            name: Tag name

        Returns:
            Tag if found, None otherwise
        """
        with logfire.span("tag_service.get_tag_by_name", tag_name=name.root):
            tag = await self.tag_repository.find_by_name(name)
            if tag:
                logfire.info("Tag found", tag_name=name.root)
            else:
                logfire.warn("Tag not found", tag_name=name.root)
            return tag
