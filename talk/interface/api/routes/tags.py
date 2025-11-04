"""Tag routes."""

import logfire
from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter

from talk.application.usecase.tag import (
    ListTagsRequest,
    ListTagsResponse,
    ListTagsUseCase,
)

router = APIRouter(
    prefix="/tags",
    tags=["tags"],
    route_class=DishkaRoute,
)


@router.get(
    "",
    response_model=ListTagsResponse,
    summary="List all available tags",
    description="Get a list of all available tags for categorizing posts.",
)
async def list_tags(
    use_case: FromDishka[ListTagsUseCase],
    limit: int = 100,
    order_by: str = "name",
) -> ListTagsResponse:
    """List all available tags.

    Args:
        use_case: List tags use case (injected)
        limit: Maximum number of tags to return (1-100)
        order_by: Sort order ('name' or 'created_at')

    Returns:
        List of tags

    Example:
        GET /tags?limit=10&order_by=name
    """
    with logfire.span("api.list_tags", limit=limit, order_by=order_by):
        request = ListTagsRequest(limit=limit, order_by=order_by)
        return await use_case.execute(request)
