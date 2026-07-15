"""
Minimal HTTP health-check server.
Koyeb and Render's free "Web Service" tiers require an open HTTP port
that responds to requests, or they consider the deployment unhealthy /
put it to sleep. This runs alongside the Pyrogram bot in the same
process using aiohttp, with negligible resource overhead.
"""
from __future__ import annotations

from aiohttp import web

from app.config import settings
from app.logger import logger

_start_time = None


async def _health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok", "service": "ai-resume-tailor-bot"})


async def _root(request: web.Request) -> web.Response:
    return web.Response(text="AI Resume Tailor Bot is running.")


async def start_health_server() -> web.AppRunner:
    app = web.Application()
    app.router.add_get("/", _root)
    app.router.add_get("/health", _health)
    app.router.add_get("/healthz", _health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=settings.health_server_port)
    await site.start()
    logger.info("Health check server listening on port {}", settings.health_server_port)
    return runner
