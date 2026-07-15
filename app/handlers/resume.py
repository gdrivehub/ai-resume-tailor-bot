from __future__ import annotations

import os
import time
import uuid

from bson import ObjectId
from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from app.config import settings
from app.database.models import (
    add_resume,
    count_resumes,
    delete_resume,
    get_resume_by_hash,
    list_resumes,
    set_active_resume,
)
from app.logger import logger
from app.parsers.resume_parser import UnsupportedFileTypeError, extract_resume_text
from app.storage import dump_channel
from app.utils.hashing import sha256_text
from app.utils.state import clear_state, set_state, waiting_for
from app.utils.validators import validate_file_extension, validate_file_size


def register(app: Client) -> None:
    @app.on_message(filters.command("setresume") & filters.private)
    async def setresume_cmd(client: Client, message: Message):
        count = await count_resumes(message.from_user.id)
        if count >= settings.max_resumes_per_user:
            await message.reply_text(
                f"⚠️ You've reached the limit of {settings.max_resumes_per_user} saved resumes. "
                f"Use /resumes to view and /delete to remove old ones first."
            )
            return
        set_state(message.from_user.id, waiting_for="resume_upload")
        await message.reply_text(
            "📄 Please upload your resume now as a **PDF, DOCX, or TXT** file.\n\n"
            f"Max size: {settings.max_file_size_mb} MB."
        )

    @app.on_message(filters.private & filters.document, group=1)
    async def catch_resume_upload(client: Client, message: Message):
        user_id = message.from_user.id
        if waiting_for(user_id) != "resume_upload":
            return  # not for us; other handlers may process this message

        doc = message.document
        if not validate_file_extension(doc.file_name or ""):
            await message.reply_text("❌ Unsupported file type. Please upload PDF, DOCX, or TXT.")
            return
        if not validate_file_size(doc.file_size or 0):
            await message.reply_text(f"❌ File too large. Max size is {settings.max_file_size_mb} MB.")
            return

        status = await message.reply_text("⏳ Processing your resume...")

        local_path = os.path.join(settings.temp_dir, f"{uuid.uuid4().hex}_{doc.file_name}")
        try:
            if dump_channel.dump_manager is None:
                await status.edit_text(
                    "❌ File storage isn't configured yet on this bot (dump channel unreachable). "
                    "Please contact the bot admin — see README 'Peer id invalid' troubleshooting."
                )
                return

            await message.download(file_name=local_path)
            text = extract_resume_text(local_path)
            resume_hash = sha256_text(text)

            existing = await get_resume_by_hash(user_id, resume_hash)
            if existing:
                await set_active_resume(user_id, existing["_id"])
                await status.edit_text(
                    "✅ This resume was already saved — I've set it as your **active resume**."
                )
                clear_state(user_id)
                return

            caption = f"Original Resume | user_id={user_id} | {doc.file_name}"
            dump_msg = await dump_channel.dump_manager.upload_document(local_path, caption=caption)

            resume_doc = {
                "user_id": user_id,
                "file_name": doc.file_name,
                "resume_text": text,
                "resume_hash": resume_hash,
                "telegram_file_id": dump_msg.document.file_id,
                "dump_message_id": dump_msg.id,
                "active": True,
                "created_at": time.time(),
            }
            resume_id = await add_resume(resume_doc)
            await set_active_resume(user_id, ObjectId(resume_id))

            await status.edit_text(
                "✅ **Resume saved and set as active!**\n\n"
                "Next step: use `/setjd` to paste a job description, then `/tailor`."
            )
        except UnsupportedFileTypeError as e:
            await status.edit_text(f"❌ {e}")
        except ValueError as e:
            await status.edit_text(f"❌ {e}")
        except Exception as e:
            logger.exception("Resume upload failed for user {}: {}", user_id, e)
            await status.edit_text("❌ Something went wrong processing your resume. Please try again.")
        finally:
            clear_state(user_id)
            if os.path.exists(local_path):
                os.remove(local_path)

    @app.on_message(filters.private & filters.text & ~filters.regex(r"^/"), group=2)
    async def remind_resume_upload(client: Client, message: Message):
        user_id = message.from_user.id
        if waiting_for(user_id) == "resume_upload":
            await message.reply_text("Please upload a **file** (PDF/DOCX/TXT), not text. Or send /cancel.")

    @app.on_message(filters.command("resumes") & filters.private)
    async def resumes_cmd(client: Client, message: Message):
        user_id = message.from_user.id
        resumes = await list_resumes(user_id, limit=settings.max_resumes_per_user)
        if not resumes:
            await message.reply_text("You have no saved resumes yet. Use /setresume to upload one.")
            return

        buttons = []
        lines = ["**📁 Your Saved Resumes**\n"]
        for r in resumes:
            active_mark = "🟢 " if r.get("active") else ""
            lines.append(f"{active_mark}`{r['_id']}` — {r.get('file_name', 'resume')}")
            buttons.append(
                [InlineKeyboardButton(f"Set active: {r.get('file_name', 'resume')[:25]}", callback_data=f"actres:{r['_id']}")]
            )
        await message.reply_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(buttons))

    @app.on_callback_query(filters.regex(r"^actres:"))
    async def activate_resume_cb(client: Client, cq: CallbackQuery):
        resume_id = cq.data.split(":", 1)[1]
        await set_active_resume(cq.from_user.id, ObjectId(resume_id))
        await cq.answer("Resume set as active ✅")
        await cq.message.edit_text("✅ Active resume updated.")

    @app.on_message(filters.command("delete") & filters.private)
    async def delete_cmd(client: Client, message: Message):
        user_id = message.from_user.id
        resumes = await list_resumes(user_id, limit=settings.max_resumes_per_user)
        if not resumes:
            await message.reply_text("You have no saved resumes to delete.")
            return
        buttons = [
            [InlineKeyboardButton(f"🗑 {r.get('file_name', 'resume')[:30]}", callback_data=f"delres:{r['_id']}")]
            for r in resumes
        ]
        await message.reply_text("Select a resume to delete:", reply_markup=InlineKeyboardMarkup(buttons))

    @app.on_callback_query(filters.regex(r"^delres:"))
    async def delete_resume_cb(client: Client, cq: CallbackQuery):
        resume_id = cq.data.split(":", 1)[1]
        ok = await delete_resume(cq.from_user.id, ObjectId(resume_id))
        if ok:
            await cq.answer("Deleted ✅")
            await cq.message.edit_text("🗑 Resume deleted.")
        else:
            await cq.answer("Could not delete (not found).", show_alert=True)

    @app.on_message(filters.command("cancel") & filters.private)
    async def cancel_cmd(client: Client, message: Message):
        clear_state(message.from_user.id)
        await message.reply_text("Cancelled current action.")
