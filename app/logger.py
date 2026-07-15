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

try:
    logger.add(
        "logs/bot_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="14 days",
        level="DEBUG",
        encoding="utf-8",
    )
except OSError as e:
    # Never let file-logging setup (e.g. a permission issue on a mounted
    # volume) take down the whole bot — stdout logging above still works,
    # and container logs remain visible via `docker compose logs`.
    logger.warning("File logging disabled (could not open logs/ directory): {}", e)

__all__ = ["logger"]
