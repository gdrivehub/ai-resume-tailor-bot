"""
Central configuration module.
Loads everything from environment variables (.env file) and exposes
a single `settings` object used across the whole application.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root regardless of current working directory
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None or val.strip() == "":
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def _int(name: str, default: int) -> int:
    val = os.getenv(name)
    if val is None or val.strip() == "":
        return default
    try:
        return int(val)
    except ValueError:
        return default


def _list(name: str) -> list[str]:
    val = os.getenv(name, "")
    return [x.strip() for x in val.split(",") if x.strip()]


@dataclass
class Settings:
    # Telegram
    api_id: int = _int("API_ID", 0)
    api_hash: str = os.getenv("API_HASH", "")
    bot_token: str = os.getenv("BOT_TOKEN", "")

    # Admins
    admins: list[int] = field(default_factory=lambda: [int(x) for x in _list("ADMINS") if x.isdigit() or (x.startswith("-") and x[1:].isdigit())])

    # Dump channel
    dump_channel_id: int = _int("DUMP_CHANNEL_ID", 0)

    # Mongo
    mongo_uri: str = os.getenv("MONGO_URI", "")
    mongo_db_name: str = os.getenv("MONGO_DB_NAME", "resume_tailor_bot")

    # AI - Gemini
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    # AI - OpenRouter
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "").strip()
    openrouter_model: str = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3-0324:free")
    openrouter_fallback_models: list[str] = field(default_factory=lambda: _list("OPENROUTER_FALLBACK_MODELS"))

    # Behaviour
    max_resumes_per_user: int = _int("MAX_RESUMES_PER_USER", 10)
    max_jds_per_user: int = _int("MAX_JDS_PER_USER", 10)
    rate_limit_count: int = _int("RATE_LIMIT_COUNT", 5)
    rate_limit_window: int = _int("RATE_LIMIT_WINDOW", 60)
    max_file_size_mb: int = _int("MAX_FILE_SIZE_MB", 10)
    enable_duplicate_cache: bool = _bool("ENABLE_DUPLICATE_CACHE", True)
    temp_dir: str = os.getenv("TEMP_DIR", "./temp")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    workers: int = _int("WORKERS", 4)

    # Health server (Koyeb/Render need an open HTTP port)
    enable_health_server: bool = _bool("ENABLE_HEALTH_SERVER", True)
    health_server_port: int = _int("HEALTH_SERVER_PORT", 8080)

    @property
    def ai_provider_priority(self) -> str:
        """Returns which provider is primary, based on key availability."""
        if self.gemini_api_key:
            return "gemini"
        if self.openrouter_api_key:
            return "openrouter"
        return "none"

    def validate(self) -> list[str]:
        """Returns a list of human-readable errors, empty if config is valid."""
        errors = []
        if not self.api_id:
            errors.append("API_ID is missing or invalid in .env")
        if not self.api_hash:
            errors.append("API_HASH is missing in .env")
        if not self.bot_token:
            errors.append("BOT_TOKEN is missing in .env")
        if not self.mongo_uri:
            errors.append("MONGO_URI is missing in .env")
        if not self.dump_channel_id:
            errors.append("DUMP_CHANNEL_ID is missing in .env")
        if not self.gemini_api_key and not self.openrouter_api_key:
            errors.append(
                "Both GEMINI_API_KEY and OPENROUTER_API_KEY are empty. "
                "At least one AI provider key is required."
            )
        return errors


settings = Settings()
Path(settings.temp_dir).mkdir(parents=True, exist_ok=True)
