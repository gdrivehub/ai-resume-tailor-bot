from __future__ import annotations

import os
import time
import uuid

from pyrogram import Client, filters
from pyrogram.types import Message

from app.ai.engine import ai_engine
from app.ai.prompts import TAILOR_RESUME_PROMPT
from app.config import settings
from app.database.models import (
    add_history,
    get_active_jd,
    get_active_resume,
    get_history_by_combo,
    get_settings,
    log_event,
    next_version_number,
)
from app.generators.docx_generator import build_resume_docx
from app.generators.pdf_generator import build_resume_pdf
from app.logger import logger
from app.storage import dump_channel
from app.utils.hashing import combo_hash
from app.utils.rate_limiter import rate_limiter
from app.utils.validators import sanitize_text


async def _no_resume_or_jd_message(message: Message, has_resume: bool, has_jd: bool) -> None:
    missing = []
    if not has_resume:
        missing.append("a resume (`/setresume`)")
    if not has_jd:
        missing.append("a job description (`/setjd`)")
    await message.reply_text(
        "⚠️ You need to set " + " and ".join(missing) + " before running this command."
    )


def register(app: Client) -> None:
    @app.on_message(filters.command("tailor") & filters.private)
    async def tailor_cmd(client: Client, message: Message):
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

        status = await message.reply_text("🤖 Tailoring your resume with AI... this can take up to a minute.")

        try:
            combo = combo_hash(resume["resume_hash"], jd["jd_hash"])

            if settings.enable_duplicate_cache:
                cached = await get_history_by_combo(user_id, combo)
                if cached:
                    await status.edit_text("♻️ Found a cached tailored resume for this exact resume+JD combo. Sending it now...")
                    await dump_channel.dump_manager.forward_to_user(user_id, cached["dump_message_id"])
                    await log_event("tailor_cache_hit", user_id)
                    return

            resume_text = sanitize_text(resume["resume_text"])
            jd_text = sanitize_text(jd["jd_text"])

            prompt = TAILOR_RESUME_PROMPT.format(
                resume_text=resume_text[:12000],
                jd_text=jd_text[:8000],
                company=jd.get("company", "the company"),
                role=jd.get("role", "the role"),
            )
            tailored_data = await ai_engine.generate_json(prompt, temperature=0.4, max_tokens=4096)

            user_settings = await get_settings(user_id)
            out_format = user_settings.get("output_format", "docx")

            base_name = f"{uuid.uuid4().hex}"
            files_to_send: list[str] = []

            if out_format in ("docx", "both"):
                docx_path = os.path.join(settings.temp_dir, f"{base_name}_tailored.docx")
                build_resume_docx(tailored_data, docx_path)
                files_to_send.append(docx_path)

            if out_format in ("pdf", "both"):
                pdf_path = os.path.join(settings.temp_dir, f"{base_name}_tailored.pdf")
                build_resume_pdf(tailored_data, pdf_path)
                files_to_send.append(pdf_path)

            version = await next_version_number(user_id, resume["resume_hash"])
            caption = (
                f"Tailored Resume v{version} | {jd.get('company', '')} - {jd.get('role', '')} | user_id={user_id}"
            )

            last_dump_msg = None
            for path in files_to_send:
                last_dump_msg = await dump_channel.dump_manager.upload_document(path, caption=caption)
                await dump_channel.dump_manager.forward_to_user(user_id, last_dump_msg.id)
                os.remove(path)

            await add_history(
                {
                    "user_id": user_id,
                    "resume_id": resume["_id"],
                    "jd_id": jd["_id"],
                    "resume_hash": resume["resume_hash"],
                    "jd_hash": jd["jd_hash"],
                    "combo_hash": combo,
                    "company": jd.get("company", ""),
                    "role": jd.get("role", ""),
                    "version": version,
                    "dump_message_id": last_dump_msg.id if last_dump_msg else None,
                    "tailored_data": tailored_data,
                    "created_at": time.time(),
                }
            )
            await log_event("tailor_generated", user_id, {"company": jd.get("company"), "role": jd.get("role")})
            await status.edit_text(
                f"✅ **Tailored resume (v{version}) ready!** Sent above.\n\n"
                f"Run `/ats` for a full compatibility report, or `/coverletter` for a matching cover letter."
            )
        except Exception as e:
            logger.exception("Tailor pipeline failed for user {}: {}", user_id, e)
            await status.edit_text(
                "❌ Something went wrong while tailoring your resume. Please try again in a moment. "
                "If this keeps happening, check that your AI provider API key is valid."
            )
