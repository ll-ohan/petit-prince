"""Logging configuration with function/line display."""

import logging
import sys

from src.config.settings import LoggingConfig


def setup_logging(config: LoggingConfig) -> None:
    """Configure application logging.

    Args:
        config: Logging configuration.
    """
    logging.basicConfig(
        level=getattr(logging, config.level),
        format=config.format,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
