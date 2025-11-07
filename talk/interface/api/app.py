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
    tags,
    users,
    votes,
)
from talk.util.di.container import create_container, setup_di
from talk.util.observability import (
    instrument_fastapi,
    instrument_httpx,
)


def create_app() -> FastAPI:
    """Create FastAPI application.

    Note: Logfire should be configured before calling this function.
    In production, start_app.py handles this.
    In tests, configure in conftest.py if needed.
    """
    settings = Settings()

    # Instrument httpx for outbound HTTP requests
    # (Logfire must be configured before instrumentation)
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
    app_instance.include_router(tags.router)

    # TODO: Add error handlers

    return app_instance


# Create app instance for uvicorn
# Note: Logfire must be configured before this module is imported
# In production: start_app.py handles this
# In tests: configure in conftest.py
app = create_app()
