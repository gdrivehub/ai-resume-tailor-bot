from __future__ import annotations

import time

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.database.models import list_history
from app.storage import dump_channel


def register(app: Client) -> None:
    @app.on_message(filters.command("history") & filters.private)
    async def history_cmd(client: Client, message: Message):
        user_id = message.from_user.id
        items = await list_history(user_id, limit=10)
        if not items:
            await message.reply_text("No tailored resumes yet. Run `/tailor` to generate your first one.")
            return

        buttons = []
        lines = ["**🕘 Your Tailored Resume History**\n"]
        for h in items:
            when = time.strftime("%Y-%m-%d", time.localtime(h.get("created_at", 0)))
            lines.append(f"v{h.get('version')} — {h.get('company','')} / {h.get('role','')} ({when})")
            if h.get("dump_message_id"):
                buttons.append(
                    [
                        InlineKeyboardButton(
                            f"⬇️ v{h.get('version')} - {h.get('company','')[:20]}",
                            callback_data=f"gethist:{h['dump_message_id']}",
                        )
                    ]
                )
        await message.reply_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(buttons) if buttons else None)

    @app.on_callback_query(filters.regex(r"^gethist:"))
    async def get_history_cb(client: Client, cq: CallbackQuery):
        if dump_channel.dump_manager is None:
            await cq.answer("File storage isn't available right now. Contact the bot admin.", show_alert=True)
            return
        dump_message_id = int(cq.data.split(":", 1)[1])
        await dump_channel.dump_manager.forward_to_user(cq.from_user.id, dump_message_id)
        await cq.answer("Sent ✅")
