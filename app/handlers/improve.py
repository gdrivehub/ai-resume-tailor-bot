from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.ai.engine import ai_engine
from app.ai.prompts import IMPROVE_SECTION_PROMPT
from app.database.models import get_active_jd, get_active_resume
from app.logger import logger
from app.utils.rate_limiter import rate_limiter
from app.utils.validators import sanitize_text

SECTION_SCHEMAS = {
    "summary": '{"summary": "improved summary text"}',
    "experience": '{"experience": [{"title": "...", "company": "...", "bullets": ["...", "..."]}]}',
    "skills": '{"skills": ["...", "..."]}',
    "projects": '{"projects": [{"name": "...", "description": "...", "bullets": ["..."]}]}',
    "education": '{"education": [{"degree": "...", "institution": "...", "dates": "...", "details": "..."}]}',
}

SECTION_LABELS = {
    "summary": "📝 Summary",
    "experience": "💼 Experience",
    "skills": "🛠 Skills",
    "projects": "🚀 Projects",
    "education": "🎓 Education",
}


def _keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(label, callback_data=f"improve:{key}")] for key, label in SECTION_LABELS.items()]
    )


def register(app: Client) -> None:
    @app.on_message(filters.command("improve") & filters.private)
    async def improve_cmd(client: Client, message: Message):
        resume = await get_active_resume(message.from_user.id)
        if not resume:
            await message.reply_text("⚠️ Set an active resume first with `/setresume`.")
            return
        await message.reply_text(
            "Which section would you like me to improve?",
            reply_markup=_keyboard(),
        )

    @app.on_callback_query(filters.regex(r"^improve:"))
    async def improve_cb(client: Client, cq: CallbackQuery):
        user_id = cq.from_user.id
        section = cq.data.split(":", 1)[1]

        allowed, retry_after = rate_limiter.allow(user_id)
        if not allowed:
            await cq.answer(f"Please wait {retry_after:.0f}s before trying again.", show_alert=True)
            return

        resume = await get_active_resume(user_id)
        if not resume:
            await cq.answer("No active resume found.", show_alert=True)
            return
        jd = await get_active_jd(user_id)

        await cq.answer("Improving...")
        await cq.message.edit_text(f"✨ Improving your **{section}** section...")

        try:
            prompt = IMPROVE_SECTION_PROMPT.format(
                section=section,
                schema_hint=SECTION_SCHEMAS[section],
                resume_text=sanitize_text(resume["resume_text"])[:10000],
                jd_text=sanitize_text(jd["jd_text"])[:6000] if jd else "(no job description set)",
            )
            data = await ai_engine.generate_json(prompt, temperature=0.4, max_tokens=1500)

            content = data.get(section)
            if isinstance(content, list):
                if section in ("experience", "projects", "education"):
                    text_parts = []
                    for item in content:
                        if section == "experience":
                            text_parts.append(f"**{item.get('title','')} — {item.get('company','')}**")
                            text_parts.extend(f"• {b}" for b in item.get("bullets", []))
                        elif section == "projects":
                            text_parts.append(f"**{item.get('name','')}**: {item.get('description','')}")
                            text_parts.extend(f"• {b}" for b in item.get("bullets", []))
                        elif section == "education":
                            text_parts.append(
                                f"**{item.get('degree','')} — {item.get('institution','')}** "
                                f"({item.get('dates','')}) {item.get('details','')}"
                            )
                    rendered = "\n".join(text_parts)
                else:
                    rendered = "\n".join(f"• {x}" for x in content)
            else:
                rendered = str(content)

            await cq.message.edit_text(
                f"✅ **Improved {SECTION_LABELS[section]}**\n\n{rendered}\n\n"
                f"_Tip: run `/tailor` to regenerate your full resume with these improvements incorporated._"
            )
        except Exception as e:
            logger.exception("Improve section '{}' failed for user {}: {}", section, user_id, e)
            await cq.message.edit_text("❌ Something went wrong improving this section. Please try again.")
