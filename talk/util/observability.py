"""Observability configuration using Logfire.

Logfire provides:
- Structured logging with OpenTelemetry
- Distributed tracing
- Performance monitoring
- Integration with popular libraries (FastAPI, SQLAlchemy, httpx)

Usage:
    # Direct usage (recommended)
    import logfire

    # Structured logging
    logfire.info("User created", user_id=user.id, handle=user.handle)

    # Manual spans for critical operations
    with logfire.span("create_invites", inviter_handle=handle):
        # Your code here
        pass
"""

import logfire
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from talk.config import Settings


def configure_logfire(settings: Settings) -> None:
    """Configure Logfire for observability.

    Sets up Logfire with environment-specific configuration:
    - Development: Local-only (unless token provided), rich console output, 100% sampling
    - Production: Cloud sending (if token provided), minimal console, 10% sampling

    Token Configuration:
    - Set OBSERVABILITY__LOGFIRE_TOKEN environment variable to enable cloud sending
    - If token is present, logs will be sent to Logfire cloud by default
    - Can be explicitly controlled with OBSERVABILITY__SEND_TO_LOGFIRE

    Args:
        settings: Application settings
    """
    # Determine if we should send to Logfire cloud
    # Priority: explicit setting > token presence > default (False)
    if settings.observability.send_to_logfire is not None:
        send_to_logfire = settings.observability.send_to_logfire
    elif settings.observability.logfire_token:
        send_to_logfire = True
    else:
        send_to_logfire = False

    # Build configuration kwargs
    config_kwargs = {
        "service_name": "talk-backend",
        "service_version": "1.0.0",
        "environment": settings.environment,
        "send_to_logfire": send_to_logfire,
        "console": logfire.ConsoleOptions(
            colors="auto",
            span_style="show-parents",
            include_timestamps=True,
            verbose=settings.debug,
        ),
        # No sampling - log everything always
        # We follow the observability quick-start guide and only instrument what matters
    }

    # Add token if provided
    if settings.observability.logfire_token:
        config_kwargs["token"] = settings.observability.logfire_token

    # Configure Logfire
    logfire.configure(**config_kwargs)

    logfire.info(
        "Observability configured",
        environment=settings.environment,
        debug=settings.debug,
        send_to_logfire=send_to_logfire,
        has_token=bool(settings.observability.logfire_token),
    )


def instrument_fastapi(app: FastAPI) -> None:
    """Instrument FastAPI application with Logfire.

    Automatically traces:
    - All HTTP requests/responses
    - Request duration
    - Errors and exceptions
    - Request metadata (method, path, client)

    Args:
        app: FastAPI application instance
    """

    def _map_request_attributes(request, attributes):
        """Map request attributes, handling both HTTP and WebSocket requests."""
        result = {**attributes}

        # Add method for HTTP requests (WebSocket doesn't have method attribute)
        if hasattr(request, "method"):
            result["method"] = request.method

        # Add path if available
        if hasattr(request, "url"):
            result["path"] = request.url.path

        # Add client host if available
        if hasattr(request, "client") and request.client:
            result["client_host"] = request.client.host

        return result

    logfire.instrument_fastapi(
        app,
        capture_headers=True,
        request_attributes_mapper=_map_request_attributes,
    )
    logfire.info("FastAPI instrumented")


def instrument_sqlalchemy(engine: AsyncEngine) -> None:
    """Instrument SQLAlchemy engine with Logfire.

    Automatically traces:
    - All SQL queries
    - Query duration
    - Connection pool usage
    - Transaction boundaries

    Args:
        engine: SQLAlchemy async engine
    """
    logfire.instrument_sqlalchemy(
        engine=engine.sync_engine,
        enable_commenter=True,  # Add SQL comments with span context
    )
    logfire.info("SQLAlchemy instrumented")


def instrument_httpx() -> None:
    """Instrument httpx client with Logfire.

    Automatically traces:
    - All outbound HTTP requests
    - Request/response details
    - Errors and retries
    - External service latency
    """
    logfire.instrument_httpx()
    logfire.info("httpx instrumented")
