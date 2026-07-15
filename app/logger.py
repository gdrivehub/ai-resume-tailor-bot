"""
Centralized logging setup using loguru.
Import `logger` from this module anywhere in the app.
"""
import sys

from loguru import logger

from app.config import settings

logger.remove()
logger.add(
    sys.stdout,
    level=settings.log_level,
    colorize=True,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    ),
)
logger.add(
    "logs/bot_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="14 days",
    level="DEBUG",
    encoding="utf-8",
)

__all__ = ["logger"]
