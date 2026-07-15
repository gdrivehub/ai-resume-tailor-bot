from __future__ import annotations

import os
import time
import uuid

from pyrogram import Client, filters
from pyrogram.types import Message

from app.ai.engine import ai_engine
from app.ai.prompts import COVER_LETTER_PROMPT
from app.config import settings
from app.database.models import (
    add_cover_letter,
    get_active_jd,
    get_active_resume,
    get_settings,
    log_event,
)
from app.generators.docx_generator import build_cover_letter_docx
from app.handlers.tailor import _no_resume_or_jd_message
from app.logger import logger
from app.storage import dump_channel
from app.utils.rate_limiter import rate_limiter
from app.utils.validators import sanitize_text


def register(app: Client) -> None:
    @app.on_message(filters.command("coverletter") & filters.private)
    async def coverletter_cmd(client: Client, message: Message):
        user_id = message.from_user.id
        allowed, retry_after = rate_limiter.allow(user_id)
        if not allowed:
            await message.reply_text(f"⏳ Please wait {retry_after:.0f}s before trying again.")
            return

        resume = await get_active_resume(user_id)
        jd = await get_active_jd(user_id)
        if not resume or not jd:
            await _no_resume_or_jd_message(message, bool(resume), bool(jd))
            return

        if dump_channel.dump_manager is None:
            await message.reply_text(
                "❌ File storage isn't configured yet on this bot (dump channel unreachable). "
                "Please contact the bot admin."
            )
            return

        status = await message.reply_text("✍️ Writing your cover letter...")
        try:
            user_settings = await get_settings(user_id)
            prompt = COVER_LETTER_PROMPT.format(
                resume_text=sanitize_text(resume["resume_text"])[:10000],
                jd_text=sanitize_text(jd["jd_text"])[:8000],
                company=jd.get("company", "the company"),
                role=jd.get("role", "the role"),
                tone=user_settings.get("tone", "professional"),
            )
            data = await ai_engine.generate_json(prompt, temperature=0.5, max_tokens=1800)

            candidate_name = ""
            try:
                first_line = resume["resume_text"].strip().splitlines()[0]
                candidate_name = first_line[:60]
            except Exception:
                pass

            path = os.path.join(settings.temp_dir, f"{uuid.uuid4().hex}_cover_letter.docx")
            build_cover_letter_docx(data, candidate_name, path)

            caption = f"Cover Letter | {jd.get('company', '')} - {jd.get('role', '')} | user_id={user_id}"
            dump_msg = await dump_channel.dump_manager.upload_document(path, caption=caption)
            await dump_channel.dump_manager.forward_to_user(user_id, dump_msg.id)
            os.remove(path)

            await add_cover_letter(
                {
                    "user_id": user_id,
                    "resume_id": resume["_id"],
                    "jd_id": jd["_id"],
                    "company": jd.get("company", ""),
                    "role": jd.get("role", ""),
                    "dump_message_id": dump_msg.id,
                    "created_at": time.time(),
                }
            )
            await log_event("cover_letter_generated", user_id)
            await status.edit_text("✅ **Cover letter ready!** Sent above.")
        except Exception as e:
            logger.exception("Cover letter generation failed for user {}: {}", user_id, e)
            await status.edit_text("❌ Something went wrong generating your cover letter. Please try again.")
