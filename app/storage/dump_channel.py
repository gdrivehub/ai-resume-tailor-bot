"""
Manages uploading generated/original files to the private Telegram dump
channel and retrieving them back by file_id. This keeps MongoDB storing
only lightweight metadata (as per the architecture report) while
Telegram's own CDN acts as free, reliable file storage.
"""
from __future__ import annotations

from pyrogram import Client
from pyrogram.types import Message

from app.config import settings
from app.logger import logger


class DumpChannelManager:
    def __init__(self, client: Client) -> None:
        self.client = client
        self.channel_id = settings.dump_channel_id

    async def upload_document(self, file_path: str, caption: str = "") -> Message:
        """
        Uploads a local file to the dump channel and returns the sent
        Message (which contains the telegram file_id for later retrieval).
        """
        try:
            msg = await self.client.send_document(
                chat_id=self.channel_id,
                document=file_path,
                caption=caption[:1024],
            )
            return msg
        except Exception as e:
            logger.error("Failed to upload {} to dump channel: {}", file_path, e)
            raise

    async def forward_to_user(self, user_id: int, dump_message_id: int) -> Message:
        """
        Copies a stored file from the dump channel to the requesting user
        without exposing the dump channel itself.
        """
        return await self.client.copy_message(
            chat_id=user_id,
            from_chat_id=self.channel_id,
            message_id=dump_message_id,
        )

    async def verify_access(self) -> bool:
        """
        Confirms the bot can post in the configured dump channel. Called
        at startup so misconfiguration is caught immediately with a clear
        error rather than failing on first use.
        """
        try:
            chat = await self.client.get_chat(self.channel_id)
            logger.info("Dump channel verified: '{}' (id={})", chat.title, self.channel_id)
            return True
        except Exception as e:
            logger.error(
                "Cannot access dump channel {}. Make sure the bot is an ADMIN "
                "of that channel with 'Post Messages' permission. Error: {}",
                self.channel_id, e,
            )
            return False


# Populated at bot startup once the Client instance exists
dump_manager: DumpChannelManager | None = None


def init_dump_manager(client: Client) -> DumpChannelManager:
    global dump_manager
    dump_manager = DumpChannelManager(client)
    return dump_manager
