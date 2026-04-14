"""Logging helpers for servicorn."""

from __future__ import annotations

import logging

__all__ = ["configure_logging", "get_logger"]


def get_logger(name: str) -> logging.Logger:
    """Return a project logger under the ``servicorn`` namespace."""
    if name.startswith("servicorn"):
        logger_name = name
    else:
        logger_name = f"servicorn.{name}"
    logger = logging.getLogger(logger_name)
    if logger_name == "servicorn":
        logger.addHandler(logging.NullHandler())
    return logger


def configure_logging(level: int = logging.INFO) -> None:
    """Configure a minimal stderr logger for manual runs."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
