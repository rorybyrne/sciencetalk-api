#!/usr/bin/env python3
"""Start the FastAPI application with Logfire error tracking for startup errors."""

import sys
import logfire
import uvicorn

from talk.config import Settings
from talk.util.observability import configure_logfire


def main() -> int:
    """Start the application and log any startup errors to Logfire."""
    settings = Settings()

    # Configure Logfire early to catch startup errors
    configure_logfire(settings)

    try:
        logfire.info("Starting FastAPI application")

        # Start uvicorn server
        # This will import the app, which will try to configure Logfire again (no-op)
        uvicorn.run(
            "talk.interface.api.app:app",
            host="0.0.0.0",
            port=8000,
            log_level="info",
        )

        return 0

    except Exception as e:
        logfire.error(
            "Application startup failed",
            error=str(e),
            error_type=type(e).__name__,
            _exc_info=sys.exc_info(),
        )
        # Re-raise so the container fails properly
        raise


if __name__ == "__main__":
    sys.exit(main())
