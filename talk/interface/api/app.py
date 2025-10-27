"""FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from talk.config import Settings
from talk.interface.api.routes import (
    auth,
    comments,
    health,
    invites,
    oauth_metadata,
    posts,
    users,
    votes,
)
from talk.util.di.container import create_container, setup_di
from talk.util.logging import setup_logging


def create_app() -> FastAPI:
    """Create FastAPI application."""
    settings = Settings()

    # Configure logging first
    setup_logging(settings)

    app_instance = FastAPI(
        title="Science Talk API",
        description="Backend API for Science Talk - a forum for sharing scientific results, methods, tools, and discussions",
        version="0.1.0",
    )

    # Setup CORS middleware
    app_instance.add_middleware(
        CORSMiddleware,
        allow_origins=[
            settings.api.frontend_url,  # Frontend (talk.amacrin.com)
            "http://localhost:3000",  # Local development
            "http://localhost:5173",  # Vite default
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Setup dependency injection
    # Settings are loaded from environment automatically
    container = create_container()
    setup_di(app_instance, container)

    # Register routes
    app_instance.include_router(health.router)
    app_instance.include_router(
        oauth_metadata.router
    )  # OAuth client metadata (no prefix)
    app_instance.include_router(auth.router)
    app_instance.include_router(posts.router)
    app_instance.include_router(comments.router)
    app_instance.include_router(votes.router)
    app_instance.include_router(invites.router)
    app_instance.include_router(users.router)

    # TODO: Add error handlers

    return app_instance


# Create app instance for uvicorn
app = create_app()
