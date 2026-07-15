"""
Hashing helpers used for duplicate detection (resume+JD combos) as
described in the architecture report: SHA256(resume) + SHA256(JD).
"""
from __future__ import annotations

import hashlib


def sha256_text(text: str) -> str:
    normalized = " ".join(text.split()).lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def combo_hash(resume_hash: str, jd_hash: str) -> str:
    return hashlib.sha256(f"{resume_hash}:{jd_hash}".encode("utf-8")).hexdigest()
