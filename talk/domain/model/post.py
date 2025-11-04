"""Post aggregate root.

Posts are the primary content type in Science Talk, categorized by tags.
"""

from datetime import datetime
from typing import Optional

from pydantic import Field, model_validator

from talk.domain.model.common import DomainModel
from talk.domain.value import PostId, TagName, UserId
from talk.domain.value.types import Handle


class Post(DomainModel):
    """Post aggregate root.

    Represents a scientific post with flexible content types:
    - Link posts: Have URL (can also have text as description)
    - Text posts: Have text content (no URL required)
    - Hybrid posts: Have both URL and text

    Posts are categorized by 1-5 tags for discovery and filtering.
    """

    id: PostId
    title: str = Field(min_length=1, max_length=300)
    author_id: UserId
    author_handle: Handle
    url: Optional[str] = None
    text: Optional[str] = Field(default=None, max_length=10000)
    tag_names: list[TagName] = Field(min_length=1, max_length=5)  # 1-5 tags required
    points: int = Field(default=1, ge=1)
    comment_count: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    deleted_at: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_has_content(self) -> "Post":
        """Validate that URL or text content is provided."""
        if not self.url and not self.text:
            raise ValueError("Post must have either URL or text content")
        return self
