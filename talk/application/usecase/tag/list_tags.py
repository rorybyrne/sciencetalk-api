"""List tags use case."""

import logfire
from datetime import datetime

from pydantic import BaseModel, Field

from talk.domain.model.tag import TagType
from talk.domain.service import TagService


class TagItem(BaseModel):
    """Tag item in response."""

    name: str
    description: str
    type: TagType
    created_at: datetime


class ListTagsRequest(BaseModel):
    """List tags request."""

    limit: int = Field(default=100, ge=1, le=100)
    order_by: str = Field(default="name", pattern="^(name|created_at)$")


class ListTagsResponse(BaseModel):
    """List tags response."""

    tags: list[TagItem]


class ListTagsUseCase:
    """Use case for listing available tags."""

    def __init__(self, tag_service: TagService) -> None:
        """Initialize list tags use case.

        Args:
            tag_service: Tag domain service
        """
        self.tag_service = tag_service

    async def execute(self, request: ListTagsRequest) -> ListTagsResponse:
        """Execute list tags flow.

        Args:
            request: List tags request

        Returns:
            List of all available tags
        """
        with logfire.span(
            "list_tags.execute",
            limit=request.limit,
            order_by=request.order_by,
        ):
            # Get all tags via service
            tags = await self.tag_service.get_all_tags(
                limit=request.limit,
                order_by=request.order_by,
            )

            # Convert to response items
            tag_items = [
                TagItem(
                    name=tag.name.root,
                    description=tag.description,
                    type=tag.type,
                    created_at=tag.created_at,
                )
                for tag in tags
            ]

            logfire.info("Tags listed", count=len(tag_items))

            return ListTagsResponse(tags=tag_items)
