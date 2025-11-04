"""In-memory implementation of Tag repository for testing."""

from copy import deepcopy
from typing import Optional

from talk.domain.model.tag import Tag
from talk.domain.repository.tag import TagRepository
from talk.domain.value import TagId, TagName


class InMemoryTagRepository(TagRepository):
    """In-memory implementation of TagRepository for testing."""

    def __init__(self) -> None:
        """Initialize empty repository."""
        self._tags: dict[TagId, Tag] = {}
        self._name_index: dict[str, TagId] = {}

    async def save(self, tag: Tag) -> Tag:
        """Save or update a tag."""
        self._tags[tag.id] = deepcopy(tag)
        self._name_index[tag.name.root] = tag.id
        return deepcopy(tag)

    async def find_by_id(self, tag_id: TagId) -> Optional[Tag]:
        """Find tag by ID."""
        tag = self._tags.get(tag_id)
        return deepcopy(tag) if tag else None

    async def find_by_name(self, name: TagName) -> Optional[Tag]:
        """Find tag by name."""
        tag_id = self._name_index.get(name.root)
        if tag_id:
            tag = self._tags.get(tag_id)
            return deepcopy(tag) if tag else None
        return None

    async def find_by_names(self, names: list[TagName]) -> list[Tag]:
        """Find multiple tags by names."""
        tags = []
        for name in names:
            tag = await self.find_by_name(name)
            if tag:
                tags.append(tag)
        return tags

    async def find_all(self, limit: int = 100, order_by: str = "name") -> list[Tag]:
        """Find all tags."""
        tags = list(self._tags.values())

        # Sort by requested field
        if order_by == "created_at":
            tags.sort(key=lambda t: t.created_at, reverse=True)
        else:
            tags.sort(key=lambda t: t.name.root)

        return [deepcopy(tag) for tag in tags[:limit]]

    async def delete(self, tag_id: TagId) -> None:
        """Delete a tag."""
        tag = self._tags.get(tag_id)
        if tag:
            self._name_index.pop(tag.name.root, None)
            self._tags.pop(tag_id, None)
