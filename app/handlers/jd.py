from __future__ import annotations

import time

from bson import ObjectId
from pyrogram import Client, filters
from pyrogram.types import Message

from app.config import settings
from app.database.models import add_jd, count_jds, set_active_jd
from app.logger import logger
from app.parsers.jd_parser import clean_jd_text, parse_jd_structured
from app.utils.hashing import sha256_text
from app.utils.state import clear_state, set_state, waiting_for
from app.utils.validators import sanitize_text, validate_jd_length


def register(app: Client) -> None:
    @app.on_message(filters.command("setjd") & filters.private)
    async def setjd_cmd(client: Client, message: Message):
        count = await count_jds(message.from_user.id)
        if count >= settings.max_jds_per_user:
            await message.reply_text(
                f"⚠️ You've reached the limit of {settings.max_jds_per_user} saved job descriptions."
            )
            return
        set_state(message.from_user.id, waiting_for="jd_paste")
        await message.reply_text(
            "📋 Please **paste the full job description** as text now (or send /cancel)."
        )

    @app.on_message(filters.private & filters.text & ~filters.regex(r"^/"), group=1)
    async def catch_jd_paste(client: Client, message: Message):
        user_id = message.from_user.id
        if waiting_for(user_id) != "jd_paste":
            return

        raw_text = sanitize_text(message.text or "")
        if not validate_jd_length(raw_text):
            await message.reply_text(
                "❌ That doesn't look like a valid job description (too short or too long). "
                "Please paste the full JD text, or /cancel."
            )
            return

        status = await message.reply_text("⏳ Analyzing job description...")
        try:
            jd_text = clean_jd_text(raw_text)
            jd_hash = sha256_text(jd_text)
            structured = await parse_jd_structured(jd_text)

            jd_doc = {
                "user_id": user_id,
                "jd_text": jd_text,
                "jd_hash": jd_hash,
                "company": structured["company"],
                "role": structured["role"],
                "location": structured.get("location", ""),
                "active": True,
                "created_at": time.time(),
            }
            jd_id = await add_jd(jd_doc)
            await set_active_jd(user_id, ObjectId(jd_id))

            await status.edit_text(
                f"✅ **Job description saved and set as active!**\n\n"
                f"🏢 Company: {structured['company']}\n"
                f"💼 Role: {structured['role']}\n\n"
                f"Next: run `/tailor` to generate your optimized resume, or `/ats` for a compatibility check."
            )
        except Exception as e:
            logger.exception("JD processing failed for user {}: {}", user_id, e)
            await status.edit_text("❌ Something went wrong analyzing the job description. Please try again.")
        finally:
            clear_state(user_id)
