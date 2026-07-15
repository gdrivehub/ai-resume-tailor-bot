from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.database.models import get_settings, update_settings


def _settings_keyboard(current: dict) -> InlineKeyboardMarkup:
    tone = current.get("tone", "professional")
    fmt = current.get("output_format", "docx")

    def mark(val, target):
        return "✅ " if val == target else ""

    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(f"{mark(tone,'professional')}Professional", callback_data="settone:professional")],
            [InlineKeyboardButton(f"{mark(tone,'confident')}Confident", callback_data="settone:confident")],
            [InlineKeyboardButton(f"{mark(tone,'friendly')}Friendly", callback_data="settone:friendly")],
            [
                InlineKeyboardButton(f"{mark(fmt,'docx')}DOCX", callback_data="setfmt:docx"),
                InlineKeyboardButton(f"{mark(fmt,'pdf')}PDF", callback_data="setfmt:pdf"),
                InlineKeyboardButton(f"{mark(fmt,'both')}Both", callback_data="setfmt:both"),
            ],
        ]
    )


def register(app: Client) -> None:
    @app.on_message(filters.command("settings") & filters.private)
    async def settings_cmd(client: Client, message: Message):
        s = await get_settings(message.from_user.id)
        await message.reply_text(
            "⚙️ **Settings**\n\nChoose your preferred writing tone and output file format:",
            reply_markup=_settings_keyboard(s),
        )

    @app.on_callback_query(filters.regex(r"^settone:"))
    async def set_tone_cb(client: Client, cq: CallbackQuery):
        tone = cq.data.split(":", 1)[1]
        await update_settings(cq.from_user.id, {"tone": tone})
        s = await get_settings(cq.from_user.id)
        await cq.message.edit_reply_markup(_settings_keyboard(s))
        await cq.answer(f"Tone set to {tone}")

    @app.on_callback_query(filters.regex(r"^setfmt:"))
    async def set_fmt_cb(client: Client, cq: CallbackQuery):
        fmt = cq.data.split(":", 1)[1]
        await update_settings(cq.from_user.id, {"output_format": fmt})
        s = await get_settings(cq.from_user.id)
        await cq.message.edit_reply_markup(_settings_keyboard(s))
        await cq.answer(f"Output format set to {fmt}")
