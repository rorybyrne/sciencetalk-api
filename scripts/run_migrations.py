#!/usr/bin/env python3
"""Run database migrations with Logfire error tracking."""

import sys
import logfire
from alembic import command
from alembic.config import Config

from talk.config import Settings
from talk.util.observability import configure_logfire


def main() -> int:
    """Run migrations and log any errors to Logfire."""
    settings = Settings()

    # Configure Logfire
    configure_logfire(settings)

    try:
        logfire.info("Starting database migrations")

        # Create Alembic config
        alembic_cfg = Config("alembic.ini")

        # Run migrations
        command.upgrade(alembic_cfg, "head")

        logfire.info("Database migrations completed successfully")
        return 0

    except Exception as e:
        logfire.error(
            "Database migration failed",
            error=str(e),
            error_type=type(e).__name__,
            _exc_info=sys.exc_info(),
        )
        # Re-raise so the container fails and doesn't start with broken schema
        raise


if __name__ == "__main__":
    sys.exit(main())
