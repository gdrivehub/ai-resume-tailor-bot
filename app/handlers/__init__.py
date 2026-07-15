"""
Registers every command/callback handler module onto the Pyrogram Client.
Import order matters slightly for message-group priority (see comments
in resume.py / jd.py regarding group=1/group=2 catch-all handlers), but
each module guards itself via conversation state so order is otherwise
safe.
"""
from __future__ import annotations

from pyrogram import Client

from app.handlers import (
    admin,
    ats,
    coverletter,
    history,
    improve,
    jd,
    resume,
    settings as settings_handler,
    start,
    tailor,
)

ALL_MODULES = [
    start,
    settings_handler,
    resume,
    jd,
    tailor,
    ats,
    coverletter,
    improve,
    history,
    admin,
]


def register_all(app: Client) -> None:
    for module in ALL_MODULES:
        module.register(app)
