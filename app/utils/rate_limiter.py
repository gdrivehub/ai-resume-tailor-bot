"""
Simple in-memory sliding-window rate limiter, per user.
Lightweight (no Redis needed) — fine for single-instance VPS/Koyeb/Render
deployments. Uses a bounded cache so memory never grows unbounded.
"""
from __future__ import annotations

import time
from collections import deque

from cachetools import TTLCache

from app.config import settings


class RateLimiter:
    def __init__(self, max_calls: int, window_seconds: int) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._buckets: TTLCache[int, deque] = TTLCache(maxsize=10_000, ttl=window_seconds * 2)

    def allow(self, user_id: int) -> tuple[bool, float]:
        """
        Returns (allowed, seconds_until_retry).
        """
        now = time.time()
        bucket = self._buckets.get(user_id)
        if bucket is None:
            bucket = deque()
            self._buckets[user_id] = bucket

        # Drop timestamps outside the window
        while bucket and now - bucket[0] > self.window_seconds:
            bucket.popleft()

        if len(bucket) >= self.max_calls:
            retry_after = self.window_seconds - (now - bucket[0])
            return False, max(retry_after, 0.0)

        bucket.append(now)
        return True, 0.0


rate_limiter = RateLimiter(settings.rate_limit_count, settings.rate_limit_window)
