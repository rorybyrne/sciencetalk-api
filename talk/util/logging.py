"""Logging configuration for the application."""

import logging
import sys

from talk.config import Settings


def setup_logging(settings: Settings) -> None:
    """Configure application logging.

    Sets up structured logging with appropriate levels based on environment.

    Args:
        settings: Application settings
    """
    # Determine log level based on environment
    if settings.debug:
        level = logging.DEBUG
    elif settings.environment == "production":
        level = logging.DEBUG  # Temporarily DEBUG for OAuth debugging
    else:
        level = logging.INFO

    # Configure root logger
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,  # Override any existing configuration
    )

    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    # Our application loggers stay at the configured level
    logging.getLogger("talk").setLevel(level)

    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured: environment={settings.environment}, level={logging.getLevelName(level)}"
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
