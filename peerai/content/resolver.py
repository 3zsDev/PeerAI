"""Turn a fixation point into a Target, applying self-exclusion, privacy, and image fallback."""
from __future__ import annotations

import os
from collections.abc import Callable

from ..config import Settings
from ..events import Rect, Target
from ..privacy import is_blocked
from .base import ContentSource


class Blocked(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class Resolver:
    def __init__(
        self,
        source: ContentSource,
        settings: Settings,
        excluded_rects: Callable[[], list[Rect]] = lambda: [],
        crop: Callable[[Rect], bytes] | None = None,
        screen: Callable[[], Rect] | None = None,
    ) -> None:
        self._source = source
        self._settings = settings
        self._excluded_rects = excluded_rects
        self._crop = crop
        self._screen = screen
        self._own_pid = os.getpid()

    def resolve(self, x: int, y: int) -> Target | None:
        for rect in self._excluded_rects():
            if rect.contains(x, y):
                return None  # our own panel or overlay: never scan what we generate

        target = self._source.at(x, y)
        if target is None:
            return None
        if target.process_id and target.process_id == self._own_pid:
            return None

        reason = is_blocked(target.window_title, target.app_name, self._settings)
        if reason:
            raise Blocked(reason)

        needs_image = target.kind_hint == "image" or len(target.text.strip()) < 20
        if needs_image and target.image_png is None and self._crop is not None:
            box = target.bbox
            if box.width < 40 or box.height < 40:
                screen = self._screen() if self._screen else Rect(0, 0, 1920, 1080)
                from .screenshot import box_around

                box = box_around(x, y, self._settings.screenshot_box, screen)
            try:
                target.image_png = self._crop(box)
                target.bbox = box
                if target.kind_hint == "unknown":
                    target.kind_hint = "image"
                target.hash = target.compute_hash()
            except Exception:
                pass
        return target
