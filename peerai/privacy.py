"""Refuse to read windows the user would not want sent to any model."""
from __future__ import annotations

from .config import Settings


def is_blocked(window_title: str, process_name: str, settings: Settings) -> str | None:
    """Return a reason string if this window must not be scanned, else None."""
    title = (window_title or "").lower()
    proc = (process_name or "").lower()
    for word in settings.blocked_title_words:
        if word.lower() in title:
            return f"window title matches blocklist word '{word}'"
    for name in settings.blocked_processes:
        if name.lower() in proc:
            return f"process matches blocklist entry '{name}'"
    return None
