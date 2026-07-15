"""
Assembles and runs the Pyrogram Client, wiring up MongoDB, the AI engine,
the dump channel manager, the health-check server, and all handlers.
"""
from __future__ import annotations

import asyncio

from pyrogram import Client

from app.config import settings
from app.database.mongo import Mongo
from app.handlers import register_all
from app.health_server import start_health_server
from app.logger import logger
from app.storage.dump_channel import init_dump_manager


def build_client() -> Client:
    app = Client(
        name="ai_resume_tailor_bot",
        api_id=settings.api_id,
        api_hash=settings.api_hash,
        bot_token=settings.bot_token,
        workers=settings.workers,
        in_memory=True,  # no local session file needed on ephemeral hosts (Koyeb/Render)
    )
    register_all(app)
    return app


async def _startup_checks(app: Client) -> None:
    errors = settings.validate()
    if errors:
        for err in errors:
            logger.error("CONFIG ERROR: {}", err)
        raise SystemExit(
            "Bot startup aborted due to configuration errors. Please fix your .env file. "
            "See README.md for setup instructions."
        )

    await Mongo.connect()

    dump_manager = init_dump_manager(app)
    ok = await dump_manager.verify_access()
    if not ok:
        raise SystemExit(
            "Bot startup aborted: cannot access the configured DUMP_CHANNEL_ID. "
            "Make sure the bot account is an ADMIN of that private channel."
        )

    logger.info(
        "AI provider priority: {} (Gemini key set: {}, OpenRouter key set: {})",
        settings.ai_provider_priority,
        bool(settings.gemini_api_key),
        bool(settings.openrouter_api_key),
    )


async def run_bot() -> None:
    app = build_client()

    async with app:
        await _startup_checks(app)

        health_runner = None
        if settings.enable_health_server:
            health_runner = await start_health_server()

        me = await app.get_me()
        logger.info("Bot started as @{} (id={}).", me.username, me.id)
        logger.info("AI Resume Tailor Bot is now running. Press Ctrl+C to stop.")

        try:
            await asyncio.Event().wait()  # run forever
        finally:
            if health_runner:
                await health_runner.cleanup()
            await Mongo.close()
            logger.info("Bot shut down cleanly.")
