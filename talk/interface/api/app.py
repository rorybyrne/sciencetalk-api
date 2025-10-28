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
from talk.util.observability import (
    configure_logfire,
    instrument_fastapi,
    instrument_httpx,
)


def create_app() -> FastAPI:
    """Create FastAPI application."""
    settings = Settings()

    # Configure observability (Logfire) first
    configure_logfire(settings)

    # Instrument httpx for outbound HTTP requests
    instrument_httpx()

    app_instance = FastAPI(
        title="Science Talk API",
        description="Backend API for Science Talk - a forum for sharing scientific results, methods, tools, and discussions",
        version="0.1.0",
    )

    # Instrument FastAPI for automatic tracing of HTTP requests
    instrument_fastapi(app_instance)

    # Setup CORS middleware
    # Safari is stricter with CORS - need explicit configuration
    app_instance.add_middleware(
        CORSMiddleware,
        allow_origins=[
            settings.api.frontend_url,  # Frontend (talk.amacrin.com)
            "http://localhost:3000",  # Local development
            "http://localhost:5173",  # Vite default
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Accept",
            "Origin",
            "User-Agent",
            "DNT",
            "Cache-Control",
            "X-Requested-With",
        ],
        expose_headers=["Content-Length", "Content-Type"],
        max_age=600,  # Cache preflight requests for 10 minutes
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
