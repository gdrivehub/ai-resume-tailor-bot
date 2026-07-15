from __future__ import annotations

import asyncio

from pyrogram import Client, filters
from pyrogram.types import Message

from app.config import settings
from app.database.models import (
    all_user_ids,
    get_stats_summary,
    set_banned,
)
from app.logger import logger

admin_filter = filters.user(settings.admins) if settings.admins else filters.create(lambda _, __, ___: False)


def register(app: Client) -> None:
    @app.on_message(filters.command("stats") & filters.private & admin_filter)
    async def stats_cmd(client: Client, message: Message):
        stats = await get_stats_summary()
        await message.reply_text(
            "**📊 Bot Statistics**\n\n"
            f"Total users: {stats['total_users']}\n"
            f"Total tailored resumes: {stats['total_tailors']}\n"
            f"Total cover letters: {stats['total_cover_letters']}\n"
            f"Total ATS reports: {stats['total_ats_reports']}\n"
        )

    @app.on_message(filters.command("users") & filters.private & admin_filter)
    async def users_cmd(client: Client, message: Message):
        ids = await all_user_ids()
        await message.reply_text(f"👥 Total registered users: **{len(ids)}**")

    @app.on_message(filters.command("broadcast") & filters.private & admin_filter)
    async def broadcast_cmd(client: Client, message: Message):
        if not message.reply_to_message:
            await message.reply_text("Reply to the message you want to broadcast with `/broadcast`.")
            return

        ids = await all_user_ids()
        status = await message.reply_text(f"📢 Broadcasting to {len(ids)} users...")
        sent, failed = 0, 0
        for uid in ids:
            try:
                await message.reply_to_message.copy(uid)
                sent += 1
            except Exception as e:
                failed += 1
                logger.debug("Broadcast failed for user {}: {}", uid, e)
            await asyncio.sleep(0.05)  # gentle throttle to avoid flood limits
        await status.edit_text(f"✅ Broadcast complete. Sent: {sent}, Failed: {failed}")

    @app.on_message(filters.command("ban") & filters.private & admin_filter)
    async def ban_cmd(client: Client, message: Message):
        parts = message.text.split()
        if len(parts) < 2 or not parts[1].isdigit():
            await message.reply_text("Usage: `/ban <user_id>`")
            return
        await set_banned(int(parts[1]), True)
        await message.reply_text(f"🚫 User {parts[1]} banned.")

    @app.on_message(filters.command("unban") & filters.private & admin_filter)
    async def unban_cmd(client: Client, message: Message):
        parts = message.text.split()
        if len(parts) < 2 or not parts[1].isdigit():
            await message.reply_text("Usage: `/unban <user_id>`")
            return
        await set_banned(int(parts[1]), False)
        await message.reply_text(f"✅ User {parts[1]} unbanned.")

    @app.on_message(filters.command("logs") & filters.private & admin_filter)
    async def logs_cmd(client: Client, message: Message):
        import glob
        import os

        log_files = sorted(glob.glob("logs/*.log"))
        if not log_files:
            await message.reply_text("No log files found yet.")
            return
        latest = log_files[-1]
        try:
            await message.reply_document(latest, caption=f"📄 {os.path.basename(latest)}")
        except Exception as e:
            await message.reply_text(f"Could not send log file: {e}")

    @app.on_message(filters.command("getchannelid") & filters.private & admin_filter)
    async def getchannelid_cmd(client: Client, message: Message):
        """
        Helper: forward any message from your dump channel to this chat,
        and the bot will reply with the numeric channel ID to put in .env
        """
        if message.forward_from_chat:
            await message.reply_text(
                f"📌 Channel ID: `{message.forward_from_chat.id}`\n\n"
                f"Put this in your `.env` as `DUMP_CHANNEL_ID={message.forward_from_chat.id}`"
            )
        else:
            await message.reply_text(
                "Forward any message from your private dump channel to me, and I'll reply with its ID.\n\n"
                "(Make sure the bot is already an admin of that channel first.)"
            )
