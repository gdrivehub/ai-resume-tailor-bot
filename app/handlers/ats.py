from __future__ import annotations

import os
import time
import uuid

from pyrogram import Client, filters
from pyrogram.types import Message

from app.ai.engine import ai_engine
from app.ai.prompts import GAP_ANALYSIS_PROMPT, KEYWORD_EXTRACTION_PROMPT
from app.ats.analyzer import run_ats_analysis
from app.config import settings
from app.database.models import (
    add_ats_report,
    get_active_jd,
    get_active_resume,
    log_event,
)
from app.generators.docx_generator import build_ats_report_docx
from app.handlers.tailor import _no_resume_or_jd_message
from app.logger import logger
from app.storage.dump_channel import dump_manager
from app.utils.rate_limiter import rate_limiter
from app.utils.validators import sanitize_text


def register(app: Client) -> None:
    @app.on_message(filters.command("ats") & filters.private)
    async def ats_cmd(client: Client, message: Message):
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

        status = await message.reply_text("🔎 Running ATS compatibility analysis...")
        try:
            resume_text = sanitize_text(resume["resume_text"])
            jd_text = sanitize_text(jd["jd_text"])
            report = await run_ats_analysis(resume_text, jd_text)

            summary = (
                f"📊 **ATS Compatibility Report**\n\n"
                f"**Overall Score: {report.get('overall_score')}/100**\n"
                f"• Keyword Match: {report.get('keyword_match_score')}/100\n"
                f"• Skills Match: {report.get('skills_match_score')}/100\n"
                f"• Experience Match: {report.get('experience_match_score')}/100\n"
                f"• Formatting: {report.get('formatting_score')}/100\n\n"
                f"✅ Matched keywords: {', '.join(report.get('matched_keywords', [])[:10]) or 'none'}\n"
                f"❌ Missing keywords: {', '.join(report.get('missing_keywords', [])[:10]) or 'none'}\n\n"
                f"Full detailed report is attached below."
            )

            path = os.path.join(settings.temp_dir, f"{uuid.uuid4().hex}_ats_report.docx")
            build_ats_report_docx(report, path)
            dump_msg = await dump_manager.upload_document(path, caption=f"ATS Report | user_id={user_id}")
            await dump_manager.forward_to_user(user_id, dump_msg.id)
            os.remove(path)

            await add_ats_report(
                {
                    "user_id": user_id,
                    "resume_id": resume["_id"],
                    "jd_id": jd["_id"],
                    "report": report,
                    "created_at": time.time(),
                }
            )
            await log_event("ats_report", user_id)
            await status.edit_text(summary)
        except Exception as e:
            logger.exception("ATS analysis failed for user {}: {}", user_id, e)
            await status.edit_text("❌ Something went wrong generating the ATS report. Please try again.")

    @app.on_message(filters.command("keywords") & filters.private)
    async def keywords_cmd(client: Client, message: Message):
        user_id = message.from_user.id
        jd = await get_active_jd(user_id)
        if not jd:
            await message.reply_text("⚠️ Set a job description first with `/setjd`.")
            return

        status = await message.reply_text("🔑 Extracting keywords...")
        try:
            prompt = KEYWORD_EXTRACTION_PROMPT.format(jd_text=sanitize_text(jd["jd_text"])[:8000])
            data = await ai_engine.generate_json(prompt, temperature=0.2, max_tokens=1200)
            lines = ["**🔑 Top Keywords for This Role**\n"]
            for label, key in [
                ("Hard Skills", "hard_skills"),
                ("Soft Skills", "soft_skills"),
                ("Tools/Tech", "tools_technologies"),
                ("Certifications", "certifications"),
                ("Job Title Variants", "job_title_variants"),
            ]:
                items = data.get(key) or []
                if items:
                    lines.append(f"**{label}:** {', '.join(items)}")
            top = data.get("top_keywords") or []
            if top:
                lines.append(f"\n**⭐ Top Priority Keywords:**\n{', '.join(top)}")
            await status.edit_text("\n".join(lines))
        except Exception as e:
            logger.exception("Keyword extraction failed for user {}: {}", user_id, e)
            await status.edit_text("❌ Something went wrong extracting keywords.")

    @app.on_message(filters.command("analyze") & filters.private)
    async def analyze_cmd(client: Client, message: Message):
        user_id = message.from_user.id
        resume = await get_active_resume(user_id)
        jd = await get_active_jd(user_id)
        if not resume or not jd:
            await _no_resume_or_jd_message(message, bool(resume), bool(jd))
            return

        status = await message.reply_text("🧩 Running gap analysis...")
        try:
            kw_prompt = KEYWORD_EXTRACTION_PROMPT.format(jd_text=sanitize_text(jd["jd_text"])[:8000])
            keywords = await ai_engine.generate_json(kw_prompt, temperature=0.2, max_tokens=1200)

            import json as _json

            gap_prompt = GAP_ANALYSIS_PROMPT.format(
                resume_text=sanitize_text(resume["resume_text"])[:10000],
                keywords_json=_json.dumps(keywords),
            )
            gap = await ai_engine.generate_json(gap_prompt, temperature=0.2, max_tokens=1500)

            await status.edit_text(
                f"**🧩 Gap Analysis**\n\n"
                f"Match: {gap.get('match_percentage', 0)}%\n\n"
                f"✅ Matched: {', '.join(gap.get('matched_keywords', [])[:12]) or 'none'}\n"
                f"❌ Missing: {', '.join(gap.get('missing_keywords', [])[:12]) or 'none'}\n\n"
                f"**Experience notes:** {gap.get('experience_match_notes', '')}\n\n"
                f"**Skills gap notes:** {gap.get('skills_gap_notes', '')}"
            )
        except Exception as e:
            logger.exception("Gap analysis failed for user {}: {}", user_id, e)
            await status.edit_text("❌ Something went wrong running gap analysis.")
