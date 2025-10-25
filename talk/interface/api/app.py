"""FastAPI application."""

from fastapi import FastAPI

from talk.interface.api.routes import auth, comments, health, posts, votes
from talk.util.di.container import create_container, setup_di


def create_app() -> FastAPI:
    """Create FastAPI application."""
    app_instance = FastAPI(
        title="Science Talk API",
        description="Backend API for Science Talk - a forum for sharing scientific results, methods, tools, and discussions",
        version="0.1.0",
    )

    # Setup dependency injection
    # Settings are loaded from environment automatically
    container = create_container()
    setup_di(app_instance, container)

    # Register routes
    app_instance.include_router(health.router)
    app_instance.include_router(auth.router)
    app_instance.include_router(posts.router)
    app_instance.include_router(comments.router)
    app_instance.include_router(votes.router)

    # TODO: Add error handlers
    # TODO: Add CORS middleware

    return app_instance


# Create app instance for uvicorn
app = create_app()
