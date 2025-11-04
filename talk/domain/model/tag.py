"""Tag entity for categorizing posts."""

from datetime import datetime
from enum import Enum

from pydantic import Field

from talk.domain.model.common import DomainModel
from talk.domain.value import TagId, TagName


class TagType(str, Enum):
    """Tag type for UI grouping."""

    SCIENCE = "science"  # Core research disciplines
    APPLIED = "applied"  # Building/making things
    CONTENT = "content"  # Post format
    META = "meta"  # Philosophy/social studies of science


class Tag(DomainModel):
    """Tag entity for categorizing posts.

    Tags provide a flexible categorization system for posts.
    Posts can have 1-5 tags for discovery and filtering.
    Tags are grouped by type for better UI organization.
    """

    id: TagId
    name: TagName  # Unique, lowercase, alphanumeric + hyphens
    description: str = Field(min_length=10, max_length=200)
    type: TagType  # Category for UI grouping
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
