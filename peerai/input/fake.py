"""Scripted pointer source for tests and --demo runs on machines without a display."""
from __future__ import annotations

import time
from collections.abc import Iterable, Iterator

from ..events import PointerSample


class FakePointerSource:
    """Replays (x, y, hold_seconds) segments in real time, then repeats."""

    def __init__(self, script: Iterable[tuple[int, int, float]] | None = None, loop: bool = True) -> None:
        self._script = list(script or [(200, 300, 1.5), (900, 300, 1.5), (600, 700, 1.5)])
        self._loop = loop
        self._iter: Iterator[tuple[int, int, float]] | None = None
        self._segment: tuple[int, int, float] | None = None
        self._segment_start = 0.0
        self._exhausted = False

    def start(self) -> None:
        self._iter = iter(self._script)
        self._advance()

    def stop(self) -> None:
        self._exhausted = True

    def _advance(self) -> None:
        assert self._iter is not None
        try:
            self._segment = next(self._iter)
        except StopIteration:
            if self._loop:
                self._iter = iter(self._script)
                self._segment = next(self._iter)
            else:
                self._segment = None
                self._exhausted = True
                return
        self._segment_start = time.monotonic()

    @property
    def exhausted(self) -> bool:
        return self._exhausted

    def poll(self) -> PointerSample | None:
        if self._segment is None:
            return None
        now = time.monotonic()
        if now - self._segment_start > self._segment[2]:
            self._advance()
            if self._segment is None:
                return None
        x, y, _ = self._segment
        return PointerSample(x, y, now)
