"""Test configuration and fixtures."""

import pytest

from talk.config import Settings
from talk.util.di.container import create_container


@pytest.fixture
def test_settings():
    """Test settings with in-memory database."""
    return Settings(
        environment="test",
        database_url="postgresql+asyncpg://talk:talk@localhost:5432/talk_test",
        debug=True,
    )


@pytest.fixture
def container(test_settings):
    """DI container for testing."""
    return create_container(test_settings)
