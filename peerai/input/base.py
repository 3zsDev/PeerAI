"""Pointer sources: anything that can say where on screen the user is looking."""
from __future__ import annotations

from typing import Protocol

from ..events import PointerSample


class PointerSource(Protocol):
    """Mouse today, webcam gaze or a Tobii tomorrow. Same three calls."""

    def start(self) -> None: ...

    def poll(self) -> PointerSample | None:
        """Return the latest sample, or None if nothing is available yet."""
        ...

    def stop(self) -> None: ...
