"""Test harness for integration and E2E tests.

Assumes docker-compose services are already running via `just local-up`.
Settings are loaded from environment variables (configure via .env or export).
"""

import pytest_asyncio

from talk.util.di import Component
from tests.di import build_test_container


def create_env_fixture(unmock: set[Component] | None = None):
    """Factory for creating test environment fixtures.

    Creates a pytest fixture that:
    - Builds a test container with specified unmocking
    - Yields request-scoped container for service access
    - Assumes docker services already running (no docker management)
    - Settings loaded from environment automatically

    Args:
        unmock: Components to use real implementations for

    Returns:
        Pytest fixture function that yields AsyncContainer

    Usage:
        # Unit tests - everything mocked, no docker needed
        unit_env = test_env()

        # Integration tests - real persistence, assumes postgres running
        integration_env = test_env(unmock={"persistence"})

        # E2E tests - real everything, assumes all services running
        e2e_env = test_env(unmock={"persistence", "bluesky"})

        @pytest.mark.asyncio
        async def test_create_post(integration_env):
            repo = await integration_env.get(PostRepository)
            post = await repo.save(Post(...))
            assert post.id is not None
    """

    @pytest_asyncio.fixture
    async def _test_environment():
        # Build container with specified unmocking
        container = build_test_container(unmock=unmock or set())

        # Open request-scoped context
        async with container() as request_container:
            yield request_container

        # Container automatically closes

    return _test_environment
