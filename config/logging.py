"""Structured logging via loguru — single sink, JSON-friendly fields."""
from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from config.settings import settings


def configure_logging() -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.log_level,
        colorize=True,
        format=(
            "<dim>{time:HH:mm:ss}</dim> "
            "<level>{level: <8}</level> "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan> "
            "<level>{message}</level>"
        ),
    )
    try:
        Path(settings.log_path).parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            settings.log_path,
            level=settings.log_level,
            rotation="10 MB",
            retention="7 days",
            compression="zip",
            enqueue=True,
            backtrace=False,
            diagnose=False,
        )
    except OSError:
        logger.warning("file logging disabled — using stderr only (read-only FS)")


__all__ = ["logger", "configure_logging"]
