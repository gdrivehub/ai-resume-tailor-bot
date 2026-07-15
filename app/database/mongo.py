"""
MongoDB connection manager using Motor (async driver).
Creates indexes on startup for fast lookups and duplicate detection.
"""
from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings
from app.logger import logger


class Mongo:
    client: AsyncIOMotorClient | None = None
    db: AsyncIOMotorDatabase | None = None

    @classmethod
    async def connect(cls) -> None:
        cls.client = AsyncIOMotorClient(
            settings.mongo_uri,
            maxPoolSize=20,
            minPoolSize=1,
            serverSelectionTimeoutMS=8000,
        )
        cls.db = cls.client[settings.mongo_db_name]
        # Verify connection
        await cls.client.admin.command("ping")
        logger.info("Connected to MongoDB database '{}'.", settings.mongo_db_name)
        await cls._ensure_indexes()

    @classmethod
    async def close(cls) -> None:
        if cls.client:
            cls.client.close()
            logger.info("MongoDB connection closed.")

    @classmethod
    async def _ensure_indexes(cls) -> None:
        db = cls.db
        assert db is not None

        await db.users.create_index("user_id", unique=True)

        await db.resumes.create_index([("user_id", 1), ("created_at", -1)])
        await db.resumes.create_index("resume_hash")

        await db.job_descriptions.create_index([("user_id", 1), ("created_at", -1)])
        await db.job_descriptions.create_index("jd_hash")

        await db.history.create_index([("user_id", 1), ("created_at", -1)])
        await db.history.create_index("combo_hash")  # resume_hash + jd_hash for dedup

        await db.cover_letters.create_index([("user_id", 1), ("created_at", -1)])
        await db.ats_reports.create_index([("user_id", 1), ("created_at", -1)])
        await db.settings.create_index("user_id", unique=True)
        await db.analytics.create_index("event_date")

        logger.info("MongoDB indexes ensured.")


def get_db() -> AsyncIOMotorDatabase:
    assert Mongo.db is not None, "MongoDB not connected yet. Call Mongo.connect() first."
    return Mongo.db
