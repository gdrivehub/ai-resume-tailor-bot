"""
Entry point for AI Resume Tailor Bot.
Run with:  python main.py
"""
from __future__ import annotations

import asyncio
import sys

try:
    import uvloop
    uvloop.install()
except ImportError:
    pass  # uvloop is unavailable on Windows; asyncio default loop is used instead

from app.bot import run_bot
from app.logger import logger


def main() -> None:
    try:
        asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit) as e:
        if isinstance(e, SystemExit) and e.code:
            logger.error(str(e.code) if not isinstance(e.code, str) else e.code)
            sys.exit(1)
        logger.info("Bot stopped by user.")
    except Exception as e:
        logger.exception("Fatal error: {}", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
