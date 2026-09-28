"""Content sources: given a screen point, say what content block is there."""
from __future__ import annotations

from typing import Protocol

from ..events import Target


class ContentSource(Protocol):
    def at(self, x: int, y: int) -> Target | None: ...
