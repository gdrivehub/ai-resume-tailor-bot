"""
Lightweight in-memory conversation state, used for simple multi-step
flows (e.g. "waiting for JD paste", "waiting for improve-section choice").
Not persisted — acceptable since these are short-lived interactions.
"""
from __future__ import annotations

from cachetools import TTLCache

# 30 minute TTL is plenty for a user to complete a multi-step flow
_state: TTLCache[int, dict] = TTLCache(maxsize=5000, ttl=1800)


def set_state(user_id: int, **kwargs) -> None:
    current = _state.get(user_id, {})
    current.update(kwargs)
    _state[user_id] = current


def get_state(user_id: int) -> dict:
    return _state.get(user_id, {})


def clear_state(user_id: int) -> None:
    _state.pop(user_id, None)


def waiting_for(user_id: int) -> str | None:
    return _state.get(user_id, {}).get("waiting_for")
