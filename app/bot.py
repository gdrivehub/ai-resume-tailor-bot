"""
Assembles and runs the Pyrogram Client, wiring up MongoDB, the AI engine,
the dump channel manager, the health-check server, and all handlers.
"""
from __future__ import annotations

import asyncio

from pyrogram import Client
from pyrogram.errors import FloodWait, RPCError

from app.config import settings
from app.database.mongo import Mongo
from app.handlers import register_all
from app.health_server import start_health_server
from app.logger import logger
from app.storage.dump_channel import init_dump_manager

MAX_START_RETRIES = 5


def build_client() -> Client:
    app = Client(
        name="ai_resume_tailor_bot",
        api_id=settings.api_id,
        api_hash=settings.api_hash,
        bot_token=settings.bot_token,
        workers=settings.workers,
        workdir=settings.session_dir,
        in_memory=False,  # persist the session to disk so restarts don't
                          # re-run the full Telegram login handshake every
                          # time -- repeated logins in a short window are
                          # what trigger Telegram's FloodWait protection.
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
        # Deliberately NON-FATAL. A bot account often cannot resolve a raw
        # channel ID until it has received at least one update from that
        # chat, even if it's already an admin there. Crashing here used to
        # cause a fast restart loop, which is exactly what triggers
        # Telegram's FloodWait lockout. Instead we keep the bot running so
        # you can use /getchannelid (forward a message from the channel to
        # the bot) to get the correct ID, or simply post one message in the
        # channel while the bot is running so it can cache the peer.
        logger.warning(
            "Dump channel is not yet reachable. File storage features (resume "
            "upload, /tailor, /ats, /coverletter, /history) will fail until this "
            "is fixed. See README.md 'Troubleshooting' -> 'Peer id invalid'. "
            "The bot will keep running so you can use /getchannelid."
        )

    logger.info(
        "AI provider priority: {} (Gemini key set: {}, OpenRouter key set: {})",
        settings.ai_provider_priority,
        bool(settings.gemini_api_key),
        bool(settings.openrouter_api_key),
    )


async def run_bot() -> None:
    app = build_client()
    attempt = 0

    while True:
        try:
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
            break  # clean shutdown (e.g. Ctrl+C) -- don't loop again

        except FloodWait as e:
            # Telegram is asking us to back off before trying to log in
            # again. Sleeping here (instead of crashing and letting Docker
            # restart us) is what actually respects the flood wait --
            # crash-looping through this makes it WORSE, not better.
            wait_s = e.value + 5
            attempt += 1
            logger.error(
                "Telegram FloodWait: must wait {}s before retrying login "
                "(attempt {}/{}). Do NOT manually restart the container -- "
                "this is being handled automatically. Sleeping now...",
                wait_s, attempt, MAX_START_RETRIES,
            )
            if attempt >= MAX_START_RETRIES:
                raise SystemExit(
                    f"Hit FloodWait {attempt} times in a row. Stopping to avoid "
                    f"making it worse. Wait at least {wait_s}s with the container "
                    f"fully stopped, then start it manually."
                )
            await asyncio.sleep(wait_s)
            continue

        except RPCError as e:
            logger.exception("Telegram RPC error during startup: {}", e)
            raise
