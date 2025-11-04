"""Tag entity for categorizing posts."""

from datetime import datetime

from pydantic import Field

from talk.domain.model.common import DomainModel
from talk.domain.value import TagId, TagName


class Tag(DomainModel):
    """Tag entity for categorizing posts.

    Tags provide a flexible categorization system for posts.
    Posts can have 1-5 tags for discovery and filtering.
    """

    id: TagId
    name: TagName  # Unique, lowercase, alphanumeric + hyphens
    description: str = Field(min_length=10, max_length=200)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
