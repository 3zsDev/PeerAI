"""Dwell detection: the gate that stops the assistant firing on every glance.

A fixation starts when pointer samples stay within `radius_px` of an anchor
for `dwell_s`. While the fixation holds, an "extended" Fixation is emitted
every `extend_every_s` so the UI can show progress. When the pointer leaves
the radius, FixationEnd is emitted and the detector re-arms.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .events import Fixation, FixationEnd, PointerSample, Rect


@dataclass
class FixationDetector:
    dwell_s: float = 0.7
    radius_px: float = 30.0
    extend_every_s: float = 0.5

    _anchor: PointerSample | None = None
    _fired: bool = False
    _last_emit_t: float = 0.0

    def reset(self) -> None:
        self._anchor = None
        self._fired = False
        self._last_emit_t = 0.0

    @property
    def active(self) -> bool:
        return self._fired

    def feed(self, sample: PointerSample) -> Fixation | FixationEnd | None:
        if self._anchor is None:
            self._anchor = sample
            return None

        dist = math.hypot(sample.x - self._anchor.x, sample.y - self._anchor.y)
        if dist > self.radius_px:
            ended = None
            if self._fired:
                ended = FixationEnd(started_at=self._anchor.t, ended_at=sample.t)
            self._anchor = sample
            self._fired = False
            self._last_emit_t = 0.0
            return ended

        held = sample.t - self._anchor.t
        if held < self.dwell_s:
            return None

        if not self._fired:
            self._fired = True
            self._last_emit_t = sample.t
            return Fixation(self._anchor.x, self._anchor.y, self._anchor.t, held)

        if sample.t - self._last_emit_t >= self.extend_every_s:
            self._last_emit_t = sample.t
            return Fixation(self._anchor.x, self._anchor.y, self._anchor.t, held)
        return None


@dataclass
class TargetHysteresis:
    """Only switch targets when the pointer has clearly left the current one.

    Without this, gaze noise near a block edge makes the highlight flicker
    between two neighbours and floods the model with requests.
    """

    margin_px: int = 40
    rearm_s: float = 0.3

    _current: Rect | None = None
    _outside_since: float | None = None

    @property
    def current(self) -> Rect | None:
        return self._current

    def clear(self) -> None:
        self._current = None
        self._outside_since = None

    def observe(self, x: int, y: int, t: float) -> None:
        """Track whether the pointer is inside the current target."""
        if self._current is None:
            return
        if self._current.contains(x, y, self.margin_px):
            self._outside_since = None
        elif self._outside_since is None:
            self._outside_since = t

    def accept(self, candidate: Rect, x: int, y: int, t: float) -> bool:
        """Return True if `candidate` should become the active target.

        Returns False both when the candidate is the current target (nothing
        new to do) and when the pointer has not yet been outside the current
        target long enough to switch.
        """
        if self._current is None:
            self._current = candidate
            self._outside_since = None
            return True
        if candidate == self._current:
            self._outside_since = None
            return False

        self.observe(x, y, t)
        if self._outside_since is not None and t - self._outside_since >= self.rearm_s:
            self._current = candidate
            self._outside_since = None
            return True
        return False
