"""Tag repository interface."""

from abc import ABC, abstractmethod
from typing import Optional

from talk.domain.model.tag import Tag
from talk.domain.value import TagId, TagName


class TagRepository(ABC):
    """Repository interface for Tag aggregate."""

    @abstractmethod
    async def save(self, tag: Tag) -> Tag:
        """Save or update a tag.

        Args:
            tag: Tag to save

        Returns:
            Saved tag
        """
        pass

    @abstractmethod
    async def find_by_id(self, tag_id: TagId) -> Optional[Tag]:
        """Find tag by ID.

        Args:
            tag_id: Tag identifier

        Returns:
            Tag if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_by_name(self, name: TagName) -> Optional[Tag]:
        """Find tag by name.

        Args:
            name: Tag name

        Returns:
            Tag if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_by_names(self, names: list[TagName]) -> list[Tag]:
        """Find multiple tags by names in a single query.

        Args:
            names: List of tag names

        Returns:
            List of found tags (may be fewer than requested if some don't exist)
        """
        pass

    @abstractmethod
    async def find_all(self, limit: int = 100, order_by: str = "name") -> list[Tag]:
        """Find all tags.

        Args:
            limit: Maximum number of tags to return
            order_by: Field to order by ('name', 'usage_count', 'created_at')

        Returns:
            List of tags
        """
        pass

    @abstractmethod
    async def delete(self, tag_id: TagId) -> None:
        """Delete a tag.

        Args:
            tag_id: Tag identifier
        """
        pass
