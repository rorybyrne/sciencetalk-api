"""Dependency injection container."""

from dishka import Container, make_container
from dishka.integrations.fastapi import setup_dishka

from talk.config import Settings

from .application import ApplicationProvider
from .domain import DomainProvider
from .persistence import PersistenceProvider


def create_container(settings: Settings) -> Container:
    """Create DI container with all providers.

    Args:
        settings: Application settings

    Returns:
        Configured DI container
    """
    container = make_container(
        DomainProvider(),
        PersistenceProvider(settings),
        ApplicationProvider(),
    )
    return container


def setup_di(app, container: Container) -> None:
    """Setup dependency injection for FastAPI.

    Args:
        app: FastAPI application
        container: DI container
    """
    setup_dishka(container, app)
