"""Test configuration and fixtures."""

import re
from uuid import UUID

from talk.domain.value import Slug


def make_slug(title: str, post_id: UUID | str | None = None) -> Slug:
    """Helper function to generate slugs for test posts.

    Mimics the slug generation logic for testing purposes.

    Args:
        title: Post title to generate slug from
        post_id: Optional post ID (UUID or str) for fallback slug generation

    Returns:
        Valid Slug value object
    """
    # Convert to lowercase and replace non-alphanumeric with hyphens
    slug_str = re.sub(r"[^a-z0-9]+", "-", title.lower())
    # Remove consecutive hyphens
    slug_str = re.sub(r"-+", "-", slug_str)
    # Strip leading/trailing hyphens and truncate
    slug_str = slug_str.strip("-")[:100]

    # Handle empty slug
    if not slug_str and post_id:
        # Convert UUID to string if needed
        id_str = str(post_id)
        slug_str = f"post-{id_str[:8]}"
    elif not slug_str:
        slug_str = "test-post"

    return Slug(slug_str)


# @pytest.fixture
# def test_settings():
#     """Test settings with test database."""
#     return Settings(
#         environment="test",
#         debug=True,
#         database=DatabaseSettings(
#             url="postgresql+asyncpg://localhost:5432/talk_test"
#         ),
#     )
