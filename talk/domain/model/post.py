"""Post aggregate root.

Posts are the primary content type in Science Talk, with 6 distinct types
for different kinds of scientific communication.
"""

from datetime import datetime
from typing import Optional

from pydantic import Field, model_validator

from talk.domain.model.common import DomainModel
from talk.domain.value import PostId, PostType, UserId
from talk.domain.value.types import Handle


class Post(DomainModel):
    """Post aggregate root.

    Represents a scientific post with specific type-based validation rules:
    - URL-based types (result, method, review, tool): require URL
    - Text-based types (discussion, ask): require text content
    """

    id: PostId
    title: str = Field(min_length=1, max_length=300)
    type: PostType
    author_id: UserId
    author_handle: Handle
    url: Optional[str] = None
    text: Optional[str] = Field(default=None, max_length=10000)
    points: int = Field(default=1, ge=1)
    comment_count: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    deleted_at: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_post_type_content(self) -> "Post":
        """Validate that URL or text is provided based on post type."""
        if self.type.requires_url and not self.url:
            raise ValueError(f"URL is required for {self.type.value} posts")
        if self.type.requires_text and not self.text:
            raise ValueError(f"Text is required for {self.type.value} posts")
        return self
