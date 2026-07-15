"""
Repository-style data access functions for every MongoDB collection.
Keeping all queries here makes the rest of the codebase database-agnostic
and easy to test / swap later.
"""
from __future__ import annotations

import time
from typing import Any, Optional

from app.database.mongo import get_db


# ---------------------------------------------------------------------
# USERS
# ---------------------------------------------------------------------
async def upsert_user(user_id: int, username: Optional[str], full_name: str) -> None:
    db = get_db()
    await db.users.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "username": username,
                "full_name": full_name,
                "last_active": time.time(),
            },
            "$setOnInsert": {"created_at": time.time(), "banned": False},
        },
        upsert=True,
    )


async def get_user(user_id: int) -> Optional[dict]:
    db = get_db()
    return await db.users.find_one({"user_id": user_id})


async def is_banned(user_id: int) -> bool:
    user = await get_user(user_id)
    return bool(user and user.get("banned"))


async def set_banned(user_id: int, banned: bool) -> None:
    db = get_db()
    await db.users.update_one({"user_id": user_id}, {"$set": {"banned": banned}})


async def count_users() -> int:
    db = get_db()
    return await db.users.count_documents({})


async def all_user_ids() -> list[int]:
    db = get_db()
    cursor = db.users.find({}, {"user_id": 1})
    return [doc["user_id"] async for doc in cursor]


# ---------------------------------------------------------------------
# RESUMES
# ---------------------------------------------------------------------
async def add_resume(doc: dict) -> str:
    db = get_db()
    result = await db.resumes.insert_one(doc)
    return str(result.inserted_id)


async def get_resume_by_hash(user_id: int, resume_hash: str) -> Optional[dict]:
    db = get_db()
    return await db.resumes.find_one({"user_id": user_id, "resume_hash": resume_hash})


async def get_active_resume(user_id: int) -> Optional[dict]:
    db = get_db()
    return await db.resumes.find_one({"user_id": user_id, "active": True})


async def list_resumes(user_id: int, limit: int = 10) -> list[dict]:
    db = get_db()
    cursor = db.resumes.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
    return [doc async for doc in cursor]


async def count_resumes(user_id: int) -> int:
    db = get_db()
    return await db.resumes.count_documents({"user_id": user_id})


async def set_active_resume(user_id: int, resume_id) -> None:
    db = get_db()
    await db.resumes.update_many({"user_id": user_id}, {"$set": {"active": False}})
    await db.resumes.update_one({"_id": resume_id}, {"$set": {"active": True}})


async def delete_resume(user_id: int, resume_id) -> bool:
    db = get_db()
    result = await db.resumes.delete_one({"user_id": user_id, "_id": resume_id})
    return result.deleted_count > 0


# ---------------------------------------------------------------------
# JOB DESCRIPTIONS
# ---------------------------------------------------------------------
async def add_jd(doc: dict) -> str:
    db = get_db()
    result = await db.job_descriptions.insert_one(doc)
    return str(result.inserted_id)


async def get_active_jd(user_id: int) -> Optional[dict]:
    db = get_db()
    return await db.job_descriptions.find_one({"user_id": user_id, "active": True})


async def set_active_jd(user_id: int, jd_id) -> None:
    db = get_db()
    await db.job_descriptions.update_many({"user_id": user_id}, {"$set": {"active": False}})
    await db.job_descriptions.update_one({"_id": jd_id}, {"$set": {"active": True}})


async def list_jds(user_id: int, limit: int = 10) -> list[dict]:
    db = get_db()
    cursor = db.job_descriptions.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
    return [doc async for doc in cursor]


async def count_jds(user_id: int) -> int:
    db = get_db()
    return await db.job_descriptions.count_documents({"user_id": user_id})


# ---------------------------------------------------------------------
# HISTORY / VERSIONS (tailored resumes)
# ---------------------------------------------------------------------
async def add_history(doc: dict) -> str:
    db = get_db()
    result = await db.history.insert_one(doc)
    return str(result.inserted_id)


async def get_history_by_combo(user_id: int, combo_hash: str) -> Optional[dict]:
    db = get_db()
    return await db.history.find_one({"user_id": user_id, "combo_hash": combo_hash})


async def list_history(user_id: int, limit: int = 10) -> list[dict]:
    db = get_db()
    cursor = db.history.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
    return [doc async for doc in cursor]


async def next_version_number(user_id: int, resume_hash: str) -> int:
    db = get_db()
    count = await db.history.count_documents({"user_id": user_id, "resume_hash": resume_hash})
    return count + 1


# ---------------------------------------------------------------------
# COVER LETTERS
# ---------------------------------------------------------------------
async def add_cover_letter(doc: dict) -> str:
    db = get_db()
    result = await db.cover_letters.insert_one(doc)
    return str(result.inserted_id)


async def list_cover_letters(user_id: int, limit: int = 10) -> list[dict]:
    db = get_db()
    cursor = db.cover_letters.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
    return [doc async for doc in cursor]


# ---------------------------------------------------------------------
# ATS REPORTS
# ---------------------------------------------------------------------
async def add_ats_report(doc: dict) -> str:
    db = get_db()
    result = await db.ats_reports.insert_one(doc)
    return str(result.inserted_id)


async def list_ats_reports(user_id: int, limit: int = 10) -> list[dict]:
    db = get_db()
    cursor = db.ats_reports.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
    return [doc async for doc in cursor]


# ---------------------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------------------
DEFAULT_SETTINGS = {
    "tone": "professional",
    "output_format": "docx",  # docx | pdf | both
    "notify_on_complete": True,
}


async def get_settings(user_id: int) -> dict:
    db = get_db()
    doc = await db.settings.find_one({"user_id": user_id})
    if not doc:
        doc = {"user_id": user_id, **DEFAULT_SETTINGS}
        await db.settings.insert_one(doc)
    return doc


async def update_settings(user_id: int, updates: dict) -> None:
    db = get_db()
    await db.settings.update_one({"user_id": user_id}, {"$set": updates}, upsert=True)


# ---------------------------------------------------------------------
# ANALYTICS
# ---------------------------------------------------------------------
async def log_event(event_type: str, user_id: int, meta: Optional[dict] = None) -> None:
    db = get_db()
    await db.analytics.insert_one(
        {
            "event_type": event_type,
            "user_id": user_id,
            "meta": meta or {},
            "event_date": time.strftime("%Y-%m-%d"),
            "timestamp": time.time(),
        }
    )


async def get_stats_summary() -> dict[str, Any]:
    db = get_db()
    total_users = await db.users.count_documents({})
    total_tailors = await db.history.count_documents({})
    total_cover_letters = await db.cover_letters.count_documents({})
    total_ats = await db.ats_reports.count_documents({})
    return {
        "total_users": total_users,
        "total_tailors": total_tailors,
        "total_cover_letters": total_cover_letters,
        "total_ats_reports": total_ats,
    }
