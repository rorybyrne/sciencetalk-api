"""FastAPI application."""

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Create FastAPI application."""
    app_instance = FastAPI(
        title="Science Talk API",
        description="Backend API for Science Talk - a forum for sharing scientific results, methods, tools, and discussions",
        version="0.1.0",
    )

    # TODO: Add routes
    # TODO: Add error handlers
    # TODO: Add DI container
    # TODO: Add CORS middleware

    return app_instance


# Create app instance for uvicorn
app = create_app()
