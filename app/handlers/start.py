from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.types import Message

from app.database.models import (
    count_jds,
    count_resumes,
    get_settings,
    log_event,
    upsert_user,
)
from app.logger import logger

WELCOME_TEXT = """👋 **Welcome to AI Resume Tailor Bot!**

I help you tailor your resume to any job description using AI — completely free.

**Quick Start:**
1️⃣ `/setresume` — upload your resume (PDF/DOCX)
2️⃣ `/setjd` — paste the job description
3️⃣ `/tailor` — get your AI-optimized resume + ATS report

**Other things I can do:**
• `/ats` — run an ATS compatibility check
• `/coverletter` — generate a tailored cover letter
• `/improve` — improve a specific resume section
• `/history` — view your past tailored resumes
• `/resumes` / `/delete` — manage saved resumes
• `/settings` — change tone & output format
• `/help` — show full command list

Let's get your resume job-ready! 🚀"""

HELP_TEXT = """**📖 Full Command Reference**

**Core**
/start — welcome message
/help — this menu
/profile — your usage stats
/settings — tone & output format preferences

**Resume**
/setresume — upload a new resume
/resumes — list your saved resumes
/delete — delete a saved resume
/setjd — paste a job description
/tailor — generate a tailored resume for the active JD

**Analysis**
/ats — ATS compatibility report
/keywords — extract keywords from active JD
/analyze — gap analysis (resume vs JD)
/improve — improve a specific section (summary/experience/skills/projects/education)

**Documents**
/coverletter — generate a tailored cover letter
/history — view past tailored resume versions

**Admin (admins only)**
/stats /broadcast /users /logs /getchannelid"""


def register(app: Client) -> None:
    @app.on_message(filters.command("start") & filters.private)
    async def start_cmd(client: Client, message: Message):
        user = message.from_user
        await upsert_user(user.id, user.username, user.first_name or "")
        await log_event("start", user.id)
        await message.reply_text(WELCOME_TEXT)
        logger.info("User {} ({}) started the bot.", user.id, user.username)

    @app.on_message(filters.command("help") & filters.private)
    async def help_cmd(client: Client, message: Message):
        await message.reply_text(HELP_TEXT)

    @app.on_message(filters.command("profile") & filters.private)
    async def profile_cmd(client: Client, message: Message):
        user_id = message.from_user.id
        n_resumes = await count_resumes(user_id)
        n_jds = await count_jds(user_id)
        s = await get_settings(user_id)
        await message.reply_text(
            f"**👤 Your Profile**\n\n"
            f"Saved resumes: {n_resumes}\n"
            f"Saved job descriptions: {n_jds}\n"
            f"Tone preference: {s.get('tone')}\n"
            f"Output format: {s.get('output_format')}\n"
        )
