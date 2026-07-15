"""
Validation and sanitization helpers.
"""
from __future__ import annotations

import re

from app.config import settings

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}

# Basic prompt-injection sanitization: strip obvious instruction-override
# attempts from user-supplied resume/JD text before sending to the AI.
_INJECTION_PATTERNS = [
    re.compile(r"ignore (all|any|the|previous|prior|above)?\s*(all|any|previous|prior|above)?\s*instructions", re.IGNORECASE),
    re.compile(r"disregard (all|any|the|previous|prior|above)?\s*instructions", re.IGNORECASE),
    re.compile(r"you are now .* (do anything|dan|jailbreak)", re.IGNORECASE),
    re.compile(r"system prompt", re.IGNORECASE),
    re.compile(r"</?(system|assistant|user)>", re.IGNORECASE),
]


def validate_file_extension(filename: str) -> bool:
    lower = filename.lower()
    return any(lower.endswith(ext) for ext in ALLOWED_EXTENSIONS)


def validate_file_size(size_bytes: int) -> bool:
    return size_bytes <= settings.max_file_size_mb * 1024 * 1024


def sanitize_text(text: str) -> str:
    """
    Removes likely prompt-injection payloads and control characters from
    user-supplied text before it is embedded into an AI prompt.
    """
    cleaned = text
    for pattern in _INJECTION_PATTERNS:
        cleaned = pattern.sub("[removed]", cleaned)
    # Strip non-printable control characters except newlines/tabs
    cleaned = "".join(ch for ch in cleaned if ch in "\n\t" or ch.isprintable())
    return cleaned.strip()


def validate_jd_length(text: str) -> bool:
    return 50 <= len(text.strip()) <= 20000
